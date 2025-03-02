import os
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import PyPDF2
import io

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
    
    async def analyze_report(self, db: Session, report_id: int) -> Dict[str, Any]:
        """
        Analyze a report that has already been uploaded.
        This method is designed to be run in the background.
        
        Args:
            db: Database session
            report_id: ID of the report to analyze
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Get the report
            report = DBService.get_report_by_id(db, report_id)
            if not report:
                logger.error(f"Report with ID {report_id} not found")
                return {"status": "error", "message": f"Report with ID {report_id} not found"}
            
            # Update report status
            DBService.update_report_status(db, report_id, "processing")
            
            # Read the PDF file
            file_path = report.file_path
            if not os.path.exists(file_path):
                logger.error(f"PDF file not found at path: {file_path}")
                DBService.update_report_status(db, report_id, "failed")
                return {"status": "error", "message": "PDF file not found"}
            
            try:
                # Extract text from PDF
                with open(file_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    page_count = len(pdf_reader.pages)
                    
                    # Update page count
                    report.page_count = page_count
                    db.commit()
                    
                    # Extract text from each page
                    text = ""
                    for page_num in range(min(page_count, 100)):  # Limit to first 100 pages
                        page = pdf_reader.pages[page_num]
                        text += page.extract_text() + "\n\n"
                
                # Analyze the text
                analysis_result = await self.analyze_report_text(text, report_id)
                
                # Store analysis results
                self._store_analysis_results(db, report_id, analysis_result)
                
                # Update report status
                DBService.update_report_status(db, report_id, "completed")
                
                return {
                    "status": "success",
                    "report_id": report_id,
                    "message": "Report analyzed successfully"
                }
                
            except Exception as e:
                logger.error(f"Error processing PDF: {str(e)}")
                DBService.update_report_status(db, report_id, "failed")
                return {"status": "error", "message": f"Error processing PDF: {str(e)}"}
            
        except Exception as e:
            logger.error(f"Error analyzing report {report_id}: {str(e)}")
            try:
                DBService.update_report_status(db, report_id, "failed")
            except:
                pass
            return {"status": "error", "message": f"Error analyzing report: {str(e)}"}
    
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
            logger.info(f"Starting AI analysis for report ID: {report_id}")
            logger.info(f"Text length: {len(text)} characters")
            
            # Log a sample of the text for debugging
            text_sample = text[:500] + "..." if len(text) > 500 else text
            logger.debug(f"Text sample: {text_sample}")
            
            # Use the new comprehensive analyze_report method from AIService
            try:
                logger.info("Starting comprehensive report analysis with FinBERT model...")
                analysis_result = self.ai_service.analyze_report(text)
                
                # Add report_id to the result
                analysis_result["report_id"] = report_id
                
                # Log analysis results
                logger.info(f"Analysis completed with status: {analysis_result.get('status', 'unknown')}")
                logger.info(f"Extracted {len(analysis_result.get('metrics', []))} metrics")
                logger.info(f"Extracted {len(analysis_result.get('risks', []))} risk factors")
                logger.info(f"Sentiment: {analysis_result.get('sentiment', {}).get('sentiment', 'unknown')}")
                
                return analysis_result
                
            except Exception as analysis_error:
                logger.error(f"Error in comprehensive analysis: {str(analysis_error)}")
                # If the comprehensive analysis fails, try individual components
                return self._fallback_component_analysis(text, report_id)
            
        except Exception as e:
            logger.error(f"Critical error analyzing report text: {str(e)}")
            # Return a minimal result with error information
            return {
                "report_id": report_id,
                "status": "failed",
                "message": f"Critical error: {str(e)}",
                "metrics": [],
                "risks": [],
                "executive_summary": "Error generating executive summary.",
                "business_outlook": "Error generating business outlook.",
                "sentiment": {
                    "sentiment": "neutral",
                    "explanation": "Error analyzing sentiment."
                }
            }
    
    def _fallback_component_analysis(self, text: str, report_id: int) -> Dict[str, Any]:
        """Fallback to component-by-component analysis if comprehensive analysis fails."""
        logger.info(f"Using fallback component analysis for report ID: {report_id}")
        analysis_result = {
            "report_id": report_id,
            "metrics": [],
            "risks": [],
            "executive_summary": "",
            "business_outlook": "",
            "sentiment": {
                "sentiment": "neutral",
                "explanation": ""
            },
            "component_errors": []
        }
        
        # Try to get metrics with error handling
        try:
            logger.info("Extracting financial metrics...")
            metrics = self.ai_service.extract_financial_metrics(text)
            analysis_result["metrics"] = metrics
            logger.info(f"Successfully extracted {len(metrics)} financial metrics")
        except Exception as metrics_error:
            logger.error(f"Error extracting financial metrics: {str(metrics_error)}")
            analysis_result["component_errors"].append(
                {"component": "metrics", "error": str(metrics_error)}
            )
        
        # Try to get executive summary with error handling
        try:
            logger.info("Generating executive summary...")
            executive_summary = self.ai_service.generate_summary(text, "executive")
            analysis_result["executive_summary"] = executive_summary
            logger.info("Successfully generated executive summary")
        except Exception as summary_error:
            logger.error(f"Error generating executive summary: {str(summary_error)}")
            analysis_result["executive_summary"] = "Error generating executive summary."
            analysis_result["component_errors"].append(
                {"component": "executive_summary", "error": str(summary_error)}
            )
        
        # Try to get business outlook with error handling
        try:
            logger.info("Generating business outlook...")
            business_outlook = self.ai_service.generate_summary(text, "business")
            analysis_result["business_outlook"] = business_outlook
            logger.info("Successfully generated business outlook")
        except Exception as outlook_error:
            logger.error(f"Error generating business outlook: {str(outlook_error)}")
            analysis_result["business_outlook"] = "Error generating business outlook."
            analysis_result["component_errors"].append(
                {"component": "business_outlook", "error": str(outlook_error)}
            )
        
        # Try to get risk factors with error handling
        try:
            logger.info("Extracting risk factors...")
            risks = self.ai_service.extract_risk_factors(text)
            analysis_result["risks"] = risks
            logger.info(f"Successfully extracted {len(risks)} risk factors")
        except Exception as risks_error:
            logger.error(f"Error extracting risk factors: {str(risks_error)}")
            analysis_result["component_errors"].append(
                {"component": "risk_factors", "error": str(risks_error)}
            )
        
        # Try to get sentiment analysis with error handling
        try:
            logger.info("Analyzing sentiment...")
            sentiment = self.ai_service.analyze_sentiment(text)
            analysis_result["sentiment"] = sentiment
            logger.info(f"Successfully analyzed sentiment: {sentiment.get('sentiment', 'unknown')}")
        except Exception as sentiment_error:
            logger.error(f"Error analyzing sentiment: {str(sentiment_error)}")
            analysis_result["sentiment"] = {
                "sentiment": "neutral",
                "explanation": "Error analyzing sentiment."
            }
            analysis_result["component_errors"].append(
                {"component": "sentiment", "error": str(sentiment_error)}
            )
        
        # Add overall status
        if analysis_result["component_errors"]:
            if len(analysis_result["component_errors"]) >= 4:  # Most components failed
                analysis_result["status"] = "failed"
                analysis_result["message"] = "Most analysis components failed"
            else:
                analysis_result["status"] = "partial"
                analysis_result["message"] = f"Partial analysis completed with {len(analysis_result['component_errors'])} component errors"
            logger.warning(f"Analysis completed with {len(analysis_result['component_errors'])} component errors")
        else:
            analysis_result["status"] = "success"
            analysis_result["message"] = "Analysis completed successfully"
            logger.info("Analysis completed successfully with no errors")
        
        return analysis_result
    
    def _store_analysis_results(self, db: Session, report_id: int, analysis: Dict[str, Any]) -> None:
        """Store analysis results in the database."""
        try:
            logger.info(f"Storing analysis results for report ID: {report_id}")
            
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
                logger.info(f"Stored {len(metrics)} metrics for report ID: {report_id}")
            else:
                logger.warning(f"No metrics to store for report ID: {report_id}")
            
            # Store summaries
            summaries = []
            
            # Executive summary
            if analysis.get("executive_summary"):
                summaries.append(SummaryCreate(
                    report_id=report_id,
                    category="executive",
                    content=analysis["executive_summary"]
                ))
            
            # Business outlook
            if analysis.get("business_outlook"):
                summaries.append(SummaryCreate(
                    report_id=report_id,
                    category="outlook",
                    content=analysis["business_outlook"]
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
                if analysis['sentiment'].get('score'):
                    sentiment_content += f"\n\nConfidence Score: {analysis['sentiment'].get('score', 0.0):.2f}"
                
                summaries.append(SummaryCreate(
                    report_id=report_id,
                    category="sentiment",
                    content=sentiment_content
                ))
            
            # Processing information
            if analysis.get("processing_time") or analysis.get("model_used"):
                processing_info = []
                if analysis.get("processing_time"):
                    processing_info.append(f"Processing Time: {analysis['processing_time']}")
                if analysis.get("processing_date"):
                    processing_info.append(f"Processing Date: {analysis['processing_date']}")
                if analysis.get("model_used"):
                    processing_info.append(f"Model Used: {analysis['model_used']}")
                if analysis.get("message"):
                    processing_info.append(f"Status Message: {analysis['message']}")
                
                summaries.append(SummaryCreate(
                    report_id=report_id,
                    category="processing_info",
                    content="\n".join(processing_info)
                ))
            
            # Error summary (if any)
            errors = analysis.get("component_errors", [])
            if not errors and "errors" in analysis:
                errors = analysis.get("errors", [])
                
            if errors:
                error_content = "\n".join([
                    f"- {error.get('component', 'unknown')}: {error.get('error', 'unknown error')}"
                    for error in errors
                ])
                summaries.append(SummaryCreate(
                    report_id=report_id,
                    category="errors",
                    content=error_content
                ))
            
            if summaries:
                self.db_service.create_summaries_batch(db, summaries)
                logger.info(f"Stored {len(summaries)} summaries for report ID: {report_id}")
            else:
                logger.warning(f"No summaries to store for report ID: {report_id}")
            
            # Update report status based on analysis status
            status = analysis.get("status", "completed")
            if status == "error" or status == "failed":
                self.db_service.update_report_status(db, report_id, "failed")
                logger.warning(f"Updated report status to 'failed' for report ID: {report_id}")
            elif status == "partial":
                self.db_service.update_report_status(db, report_id, "partial")
                logger.warning(f"Updated report status to 'partial' for report ID: {report_id}")
            else:
                self.db_service.update_report_status(db, report_id, "completed")
                logger.info(f"Updated report status to 'completed' for report ID: {report_id}")
                
        except Exception as e:
            logger.error(f"Error storing analysis results: {str(e)}")
            # Update report status to indicate error
            try:
                self.db_service.update_report_status(db, report_id, "failed")
                logger.warning(f"Updated report status to 'failed' due to storage error for report ID: {report_id}")
            except Exception as status_error:
                logger.error(f"Failed to update report status: {str(status_error)}")
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
        """Get historical metrics for a company."""
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
    
    async def compare_texts(
        self,
        text1: str,
        text2: str,
        instruction: str = "Compare these two texts and highlight key differences:"
    ) -> str:
        """Compare two texts using AI analysis.
        
        Args:
            text1: First text to compare
            text2: Second text to compare
            instruction: Specific instruction for the comparison
            
        Returns:
            String containing the comparison analysis
        """
        try:
            logger.info("Comparing texts with AI analysis")
            
            # Prepare the prompt for comparison
            prompt = f"""
{instruction}

TEXT 1:
{text1}

TEXT 2:
{text2}

Please provide a detailed comparison highlighting:
1. Key similarities between the texts
2. Important differences and contrasts
3. Overall assessment of which text presents a more positive/negative view (if applicable)
4. Any notable trends or patterns across both texts
"""
            
            # Use the AI service to generate the comparison
            comparison_result = await self.ai_service.answer_question(prompt, "")
            
            if not comparison_result or len(comparison_result.strip()) < 10:
                # Fallback to a simpler comparison if the AI service fails
                comparison_result = self._generate_basic_comparison(text1, text2)
                
            return comparison_result
            
        except Exception as e:
            logger.error(f"Error comparing texts: {str(e)}")
            return f"Error generating comparison: {str(e)}"
    
    def _generate_basic_comparison(self, text1: str, text2: str) -> str:
        """Generate a basic comparison when AI service fails.
        
        Args:
            text1: First text to compare
            text2: Second text to compare
            
        Returns:
            Basic comparison text
        """
        # Calculate text lengths
        len1 = len(text1.split())
        len2 = len(text2.split())
        
        # Calculate sentiment scores using simple keyword counting
        positive_words = ["growth", "increase", "profit", "success", "positive", "opportunity", "strong", "improve"]
        negative_words = ["decline", "decrease", "loss", "risk", "negative", "challenge", "weak", "concern"]
        
        pos_score1 = sum(1 for word in positive_words if word.lower() in text1.lower())
        neg_score1 = sum(1 for word in negative_words if word.lower() in text1.lower())
        pos_score2 = sum(1 for word in positive_words if word.lower() in text2.lower())
        neg_score2 = sum(1 for word in negative_words if word.lower() in text2.lower())
        
        # Generate basic comparison
        comparison = "Basic Comparison Analysis:\n\n"
        
        # Length comparison
        comparison += f"Text 1 contains {len1} words, while Text 2 contains {len2} words.\n"
        comparison += f"Text 1 is {'longer' if len1 > len2 else 'shorter'} than Text 2.\n\n"
        
        # Sentiment comparison
        sentiment1 = "positive" if pos_score1 > neg_score1 else "negative" if neg_score1 > pos_score1 else "neutral"
        sentiment2 = "positive" if pos_score2 > neg_score2 else "negative" if neg_score2 > pos_score2 else "neutral"
        
        comparison += f"Text 1 appears to have a {sentiment1} tone overall.\n"
        comparison += f"Text 2 appears to have a {sentiment2} tone overall.\n\n"
        
        comparison += "Note: This is a basic comparison generated as a fallback. For a more detailed analysis, please try again later."
        
        return comparison 