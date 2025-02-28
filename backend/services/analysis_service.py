import os
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from services.pdf_service import PDFService
from services.ai_service import AIService
from services.db_service import DBService
from models.schemas import (
    CompanyCreate, ReportCreate, MetricCreate, SummaryCreate
)

logger = logging.getLogger(__name__)

class AnalysisService:
    """Service for coordinating PDF processing and AI analysis."""
    
    def __init__(self):
        self.pdf_service = PDFService()
        self.ai_service = AIService()
        self.db_service = DBService()
        self.upload_dir = os.path.join(os.getcwd(), "uploads")
        
        # Create uploads directory if it doesn't exist
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)
    
    async def process_report(
        self, 
        db: Session, 
        file_content: bytes, 
        filename: str, 
        company_name: str, 
        year: int,
        ticker: Optional[str] = None,
        sector: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process an uploaded annual report."""
        file_path = None
        report = None
        
        try:
            logger.info(f"Starting processing of report: {filename} for {company_name}")
            
            # Validate inputs
            if not file_content or len(file_content) < 100:
                logger.error(f"File content too small: {len(file_content) if file_content else 0} bytes")
                raise Exception("File content is too small or empty")
                
            if not filename or not filename.lower().endswith('.pdf'):
                logger.error(f"Invalid filename: {filename}")
                raise Exception("Invalid filename or not a PDF file")
            
            # Save the uploaded file
            try:
                file_path, file_name = self.pdf_service.save_upload(
                    file_content, 
                    filename, 
                    self.upload_dir
                )
                logger.info(f"File saved successfully at: {file_path}")
            except Exception as e:
                logger.error(f"Failed to save uploaded file: {str(e)}")
                raise Exception(f"Failed to save uploaded file: {str(e)}")
            
            # Extract text from PDF
            try:
                text = self.pdf_service.extract_text_from_pdf(file_path)
                if not text or len(text.strip()) < 100:
                    logger.warning(f"Extracted text is too short or empty: {len(text) if text else 0} chars")
                    raise Exception("The PDF appears to be empty or could not be properly read")
                logger.info(f"Successfully extracted {len(text)} characters of text from PDF")
            except Exception as e:
                logger.error(f"Failed to extract text from PDF: {str(e)}")
                raise Exception(f"Failed to extract text from PDF: {str(e)}")
            
            # Get PDF metadata
            try:
                metadata = self.pdf_service.get_pdf_metadata(file_path)
                page_count = metadata.get('page_count', 0)
                logger.info(f"PDF metadata extracted: {page_count} pages")
            except Exception as e:
                logger.error(f"Failed to extract PDF metadata: {str(e)}")
                # Not critical, continue with default values
                page_count = 0
            
            # Database operations - use transaction
            try:
                # Begin transaction explicitly
                db.begin_nested()
                
                # Check if company exists, create if not
                company = self.db_service.get_company_by_name(db, company_name)
                if not company:
                    logger.info(f"Creating new company: {company_name}")
                    company_create = CompanyCreate(
                        name=company_name,
                        ticker=ticker or "",
                        sector=sector or "",
                        description=""
                    )
                    company = self.db_service.create_company(db, company_create)
                
                # Create report record
                logger.info(f"Creating report record for company ID: {company.id}")
                report_create = ReportCreate(
                    company_id=company.id,
                    year=str(year),
                    file_path=file_path,
                    file_name=file_name,
                    processing_status="processing",
                    page_count=page_count
                )
                report = self.db_service.create_report(db, report_create)
                
                # Commit the transaction for creating the report
                db.commit()
                logger.info(f"Report record created with ID: {report.id}")
                
                # Start AI analysis
                logger.info(f"Starting AI analysis for report ID: {report.id}")
                analysis_result = await self.analyze_report_text(text, report.id)
                
                # Begin a new transaction for storing analysis results
                db.begin_nested()
                
                # Store analysis results
                self._store_analysis_results(db, report.id, analysis_result)
                
                # Update report status
                self.db_service.update_report_status(db, report.id, "completed")
                
                # Commit the transaction for analysis results
                db.commit()
                logger.info(f"Report processing completed successfully for report ID: {report.id}")
                
                return {
                    "report_id": report.id,
                    "company_id": company.id,
                    "status": "completed"
                }
            except Exception as e:
                logger.error(f"Database error during report processing: {str(e)}")
                # Rollback transaction
                db.rollback()
                
                # Update report status to failed if it was created
                if report:
                    try:
                        # Begin a new transaction for updating status
                        db.begin_nested()
                        self.db_service.update_report_status(db, report.id, "failed")
                        db.commit()
                        logger.info(f"Updated report status to 'failed' for report ID: {report.id}")
                    except Exception as status_error:
                        logger.error(f"Failed to update report status: {str(status_error)}")
                        db.rollback()
                
                raise Exception(f"Database error during report processing: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error processing report {filename}: {str(e)}")
            # If file was saved but processing failed, we keep the file for debugging
            if file_path and os.path.exists(file_path):
                logger.info(f"Keeping file for debugging: {file_path}")
            raise
    
    async def analyze_report_text(self, text: str, report_id: int) -> Dict[str, Any]:
        """Analyze the text content of a report using AI services."""
        try:
            # Perform comprehensive analysis
            analysis_result = self.ai_service.analyze_report(text)
            
            # Add report_id to the result
            analysis_result["report_id"] = report_id
            
            return analysis_result
        except Exception as e:
            logger.error(f"Error analyzing report text: {str(e)}")
            raise
    
    def _store_analysis_results(self, db: Session, report_id: int, analysis: Dict[str, Any]) -> None:
        """Store analysis results in the database."""
        try:
            # Store metrics
            metrics = []
            for metric_data in analysis.get("metrics", []):
                metric = MetricCreate(
                    report_id=report_id,
                    name=metric_data.get("name", ""),
                    value=metric_data.get("value", ""),
                    unit=metric_data.get("unit", ""),
                    category=metric_data.get("category", "financial")
                )
                metrics.append(metric)
            
            if metrics:
                self.db_service.create_metrics_batch(db, metrics)
            
            # Store summaries
            summaries = []
            
            # Executive summary
            if analysis.get("summaries", {}).get("executive"):
                summaries.append(SummaryCreate(
                    report_id=report_id,
                    category="executive",
                    content=analysis["summaries"]["executive"]
                ))
            
            # Business outlook
            if analysis.get("summaries", {}).get("outlook"):
                summaries.append(SummaryCreate(
                    report_id=report_id,
                    category="outlook",
                    content=analysis["summaries"]["outlook"]
                ))
            
            # Risk factors (combine into a single summary)
            if analysis.get("risks"):
                risk_content = "\n".join([f"- {risk}" for risk in analysis["risks"]])
                summaries.append(SummaryCreate(
                    report_id=report_id,
                    category="risks",
                    content=risk_content
                ))
            
            # Sentiment analysis
            if analysis.get("sentiment"):
                sentiment_content = (
                    f"Sentiment: {analysis['sentiment'].get('sentiment', 'neutral')}\n\n"
                    f"Explanation: {analysis['sentiment'].get('explanation', '')}"
                )
                summaries.append(SummaryCreate(
                    report_id=report_id,
                    category="sentiment",
                    content=sentiment_content
                ))
            
            if summaries:
                self.db_service.create_summaries_batch(db, summaries)
                
        except Exception as e:
            logger.error(f"Error storing analysis results: {str(e)}")
            raise
    
    async def compare_reports(
        self, 
        db: Session, 
        report_ids: List[int]
    ) -> Dict[str, Any]:
        """Compare multiple reports."""
        try:
            reports_data = []
            metrics_by_report = {}
            
            # Collect data for each report
            for report_id in report_ids:
                report_data = self.db_service.get_report_full_data(db, report_id)
                if not report_data:
                    continue
                
                reports_data.append({
                    "report_id": report_id,
                    "company_name": report_data["company"].name if report_data.get("company") else "",
                    "year": report_data["report"].year if report_data.get("report") else 0,
                    "metrics": report_data.get("metrics", []),
                    "summaries": report_data.get("summaries", [])
                })
                
                # Organize metrics by name for easier comparison
                metrics_by_report[report_id] = {
                    metric.name: {
                        "value": metric.value,
                        "unit": metric.unit
                    }
                    for metric in report_data.get("metrics", [])
                }
            
            # Find common metrics across reports
            common_metrics = set()
            for report_id, metrics in metrics_by_report.items():
                if not common_metrics:
                    common_metrics = set(metrics.keys())
                else:
                    common_metrics &= set(metrics.keys())
            
            # Create comparison data for common metrics
            comparison_data = []
            for metric_name in common_metrics:
                metric_comparison = {
                    "name": metric_name,
                    "values": []
                }
                
                for report in reports_data:
                    report_id = report["report_id"]
                    if report_id in metrics_by_report and metric_name in metrics_by_report[report_id]:
                        metric_comparison["values"].append({
                            "report_id": report_id,
                            "company_name": report["company_name"],
                            "year": report["year"],
                            "value": metrics_by_report[report_id][metric_name]["value"],
                            "unit": metrics_by_report[report_id][metric_name]["unit"]
                        })
                
                comparison_data.append(metric_comparison)
            
            return {
                "reports": reports_data,
                "comparison": comparison_data
            }
        except Exception as e:
            logger.error(f"Error comparing reports: {str(e)}")
            raise
    
    async def get_report_analysis(self, db: Session, report_id: int) -> Dict[str, Any]:
        """Get the complete analysis for a report."""
        try:
            report_data = self.db_service.get_report_full_data(db, report_id)
            if not report_data:
                return {}
            
            # Organize metrics by category
            metrics_by_category = {}
            for metric in report_data.get("metrics", []):
                category = metric.category or "financial"
                if category not in metrics_by_category:
                    metrics_by_category[category] = []
                
                metrics_by_category[category].append({
                    "name": metric.name,
                    "value": metric.value,
                    "unit": metric.unit
                })
            
            # Organize summaries by category
            summaries_by_category = {}
            for summary in report_data.get("summaries", []):
                summaries_by_category[summary.category] = summary.content
            
            return {
                "report": {
                    "id": report_data["report"].id,
                    "year": report_data["report"].year,
                    "file_name": report_data["report"].file_name,
                    "upload_date": report_data["report"].upload_date,
                    "page_count": report_data["report"].page_count
                },
                "company": {
                    "id": report_data["company"].id,
                    "name": report_data["company"].name,
                    "ticker": report_data["company"].ticker,
                    "sector": report_data["company"].sector
                },
                "metrics": metrics_by_category,
                "summaries": summaries_by_category
            }
        except Exception as e:
            logger.error(f"Error getting report analysis: {str(e)}")
            raise
    
    async def get_company_metrics_history(
        self, 
        db: Session, 
        company_id: int, 
        metric_names: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get historical data for specific metrics for a company."""
        try:
            result = {}
            
            for metric_name in metric_names:
                metric_history = self.db_service.get_metrics_by_name_and_company(
                    db, company_id, metric_name
                )
                result[metric_name] = metric_history
            
            return result
        except Exception as e:
            logger.error(f"Error getting company metrics history: {str(e)}")
            raise 