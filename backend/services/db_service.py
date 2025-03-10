import logging
import json
from typing import List, Dict, Any, Optional, Union, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, func
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from models.database import Company, Report, Metric, Summary, Entity, SentimentAnalysis, RiskAssessment
from models.schemas import (
    CompanyCreate, CompanyUpdate, ReportCreate, 
    MetricCreate, SummaryCreate, SearchParams,
    EntityCreate, SentimentAnalysisCreate, RiskAssessmentCreate
)

logger = logging.getLogger(__name__)

class DBServiceError(Exception):
    """Base exception for database service errors."""
    pass

class DBService:
    """Service for database operations."""
    
    @staticmethod
    def create_company(db: Session, company: CompanyCreate) -> Tuple[Optional[Company], Optional[str]]:
        """
        Create a new company in the database.
        
        Args:
            db: Database session
            company: Company data to create
            
        Returns:
            Tuple containing:
            - Company object or None if error
            - Error message or None if successful
        """
        try:
            db_company = Company(
                name=company.name,
                ticker=company.ticker,
                sector=company.sector,
                description=company.description
            )
            db.add(db_company)
            db.commit()
            db.refresh(db_company)
            logger.info(f"Created company: {db_company.name} (ID: {db_company.id})")
            return db_company, None
        except SQLAlchemyError as e:
            db.rollback()
            error_msg = f"Database error creating company: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            db.rollback()
            error_msg = f"Unexpected error creating company: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    @staticmethod
    def update_company(db: Session, company_id: int, company: CompanyUpdate) -> Optional[Company]:
        """Update an existing company."""
        try:
            db_company = db.query(Company).filter(Company.id == company_id).first()
            if not db_company:
                return None
            
            # Update fields if provided
            if company.name is not None:
                db_company.name = company.name
            if company.ticker is not None:
                db_company.ticker = company.ticker
            if company.sector is not None:
                db_company.sector = company.sector
            if company.description is not None:
                db_company.description = company.description
            
            db_company.updated_at = datetime.now()
            db.commit()
            db.refresh(db_company)
            return db_company
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating company: {str(e)}")
            raise
    
    @staticmethod
    def get_company(db: Session, company_id: int) -> Optional[Company]:
        """Get a company by ID."""
        try:
            return db.query(Company).filter(Company.id == company_id).first()
        except Exception as e:
            logger.error(f"Error getting company: {str(e)}")
            raise
    
    @staticmethod
    def get_company_by_name(db: Session, name: str) -> Optional[Company]:
        """Get a company by name."""
        try:
            return db.query(Company).filter(Company.name == name).first()
        except Exception as e:
            logger.error(f"Error getting company by name: {str(e)}")
            raise
    
    @staticmethod
    def get_company_by_ticker(db: Session, ticker: str) -> Optional[Company]:
        """Get a company by ticker symbol."""
        try:
            return db.query(Company).filter(Company.ticker == ticker).first()
        except Exception as e:
            logger.error(f"Error getting company by ticker: {str(e)}")
            raise
    
    @staticmethod
    def get_companies(db: Session, skip: int = 0, limit: int = 100) -> List[Company]:
        """Get all companies with pagination."""
        try:
            return db.query(Company).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting companies: {str(e)}")
            raise
    
    @staticmethod
    def create_report(db: Session, report: ReportCreate) -> Report:
        """Create a new report."""
        try:
            db_report = Report(
                company_id=report.company_id,
                year=report.year,
                file_path=report.file_path,
                file_name=report.file_name,
                upload_date=datetime.now(),
                processing_status=report.processing_status,
                page_count=report.page_count
            )
            db.add(db_report)
            db.commit()
            db.refresh(db_report)
            return db_report
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating report: {str(e)}")
            raise
    
    @staticmethod
    def update_report_status(db: Session, report_id: int, status: str, error_message: Optional[str] = None) -> Optional[Report]:
        """
        Update the processing status of a report.
        
        Args:
            db: Database session
            report_id: ID of the report to update
            status: New processing status
            error_message: Optional error message if status is 'failed'
            
        Returns:
            Updated Report object or None if report not found
        """
        try:
            db_report = db.query(Report).filter(Report.id == report_id).first()
            if not db_report:
                return None
            
            db_report.processing_status = status
            
            # If there's an error message and status is failed, store it
            if error_message and status == "failed":
                db_report.error_message = error_message
            
            db.commit()
            db.refresh(db_report)
            return db_report
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating report status: {str(e)}")
            raise
    
    @staticmethod
    def get_report(db: Session, report_id: int) -> Optional[Report]:
        """Get a report by ID."""
        try:
            return db.query(Report).filter(Report.id == report_id).first()
        except Exception as e:
            logger.error(f"Error getting report: {str(e)}")
            raise
    
    @staticmethod
    def get_reports_by_company(db: Session, company_id: int, skip: int = 0, limit: int = 100) -> List[Report]:
        """Get all reports for a company with pagination."""
        try:
            return db.query(Report).filter(Report.company_id == company_id).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting reports by company: {str(e)}")
            raise
    
    @staticmethod
    def get_reports(db: Session, skip: int = 0, limit: int = 100) -> List[Report]:
        """Get all reports with pagination."""
        try:
            return db.query(Report).order_by(desc(Report.upload_date)).offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting reports: {str(e)}")
            raise
    
    @staticmethod
    def create_metric(db: Session, metric: MetricCreate) -> Metric:
        """Create a new metric."""
        try:
            db_metric = Metric(
                report_id=metric.report_id,
                name=metric.name,
                value=metric.value,
                unit=metric.unit,
                category=metric.category
            )
            db.add(db_metric)
            db.commit()
            db.refresh(db_metric)
            return db_metric
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating metric: {str(e)}")
            raise
    
    @staticmethod
    def create_metrics_batch(db: Session, metrics: List[MetricCreate]) -> List[Metric]:
        """Create multiple metrics in a batch."""
        try:
            db_metrics = []
            for metric in metrics:
                db_metric = Metric(
                    report_id=metric.report_id,
                    name=metric.name,
                    value=metric.value,
                    unit=metric.unit,
                    category=metric.category
                )
                db.add(db_metric)
                db_metrics.append(db_metric)
            
            db.commit()
            for metric in db_metrics:
                db.refresh(metric)
            
            return db_metrics
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating metrics batch: {str(e)}")
            raise
    
    @staticmethod
    def get_metrics_by_report(db: Session, report_id: int) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Get all metrics for a specific report.
        
        Args:
            db: Database session
            report_id: ID of the report to get metrics for
            
        Returns:
            Tuple containing:
            - List of metrics as dictionaries or None if error
            - Error message or None if successful
        """
        try:
            metrics = db.query(Metric).filter(Metric.report_id == report_id).all()
            
            # Format metrics consistently as dictionaries
            result = []
            for metric in metrics:
                result.append({
                    "id": metric.id,
                    "report_id": metric.report_id,
                    "name": metric.name,
                    "value": metric.value,
                    "unit": metric.unit,
                    "year": metric.year
                })
            
            logger.info(f"Retrieved {len(result)} metrics for report ID {report_id}")
            return result, None
        except SQLAlchemyError as e:
            error_msg = f"Database error retrieving metrics for report {report_id}: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error retrieving metrics for report {report_id}: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    @staticmethod
    def create_summary(db: Session, summary: SummaryCreate) -> Summary:
        """Create a new summary."""
        try:
            db_summary = Summary(
                report_id=summary.report_id,
                category=summary.category,
                content=summary.content
            )
            db.add(db_summary)
            db.commit()
            db.refresh(db_summary)
            return db_summary
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating summary: {str(e)}")
            raise
    
    @staticmethod
    def create_summaries_batch(db: Session, summaries: List[SummaryCreate]) -> List[Summary]:
        """Create multiple summaries in a batch."""
        try:
            db_summaries = []
            for summary in summaries:
                db_summary = Summary(
                    report_id=summary.report_id,
                    category=summary.category,
                    content=summary.content
                )
                db.add(db_summary)
                db_summaries.append(db_summary)
            
            db.commit()
            for summary in db_summaries:
                db.refresh(summary)
            
            return db_summaries
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating summaries batch: {str(e)}")
            raise
    
    @staticmethod
    def get_summaries_by_report(db: Session, report_id: int) -> List[Summary]:
        """Get all summaries for a report."""
        try:
            return db.query(Summary).filter(Summary.report_id == report_id).all()
        except Exception as e:
            logger.error(f"Error getting summaries by report: {str(e)}")
            raise
    
    @staticmethod
    def get_summaries_by_report_id(db: Session, report_id: int) -> List[Summary]:
        """Get all summaries for a report."""
        try:
            return db.query(Summary).filter(Summary.report_id == report_id).all()
        except Exception as e:
            logger.error(f"Error getting summaries for report {report_id}: {str(e)}")
            return []
    
    @staticmethod
    def search_reports(db: Session, params: SearchParams, skip: int = 0, limit: int = 100) -> List[Report]:
        """Search for reports based on various criteria."""
        try:
            query = db.query(Report)
            
            # Join with Company if needed for filtering
            if params.company_name or params.ticker or params.sector:
                query = query.join(Report.company)
            
            # Apply filters
            if params.company_name:
                query = query.filter(Company.name.ilike(f"%{params.company_name}%"))
            
            if params.ticker:
                query = query.filter(Company.ticker == params.ticker)
            
            if params.sector:
                query = query.filter(Company.sector == params.sector)
            
            if params.year:
                query = query.filter(Report.year == params.year)
            
            if params.start_date:
                query = query.filter(Report.upload_date >= params.start_date)
            
            if params.end_date:
                query = query.filter(Report.upload_date <= params.end_date)
            
            # Apply pagination and return results
            return query.offset(skip).limit(limit).all()
        except Exception as e:
            logger.error(f"Error searching reports: {str(e)}")
            raise
    
    @staticmethod
    def get_report_with_company(db: Session, report_id: int) -> Optional[Report]:
        """Get a report with its associated company."""
        try:
            return db.query(Report).filter(Report.id == report_id).first()
        except Exception as e:
            logger.error(f"Error getting report with company: {str(e)}")
            return None
    
    @staticmethod
    def get_report_full_data(db: Session, report_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Get full report data including metrics and summaries.
        
        Args:
            db: Database session
            report_id: ID of the report to retrieve
            
        Returns:
            Tuple containing:
            - Dictionary with report data or None if error
            - Error message or None if successful
        """
        try:
            # Get the report with company data
            report = db.query(Report).filter(Report.id == report_id).first()
            
            if not report:
                return None, f"Report with ID {report_id} not found"
                
            # Get metrics for the report
            metrics = db.query(Metric).filter(Metric.report_id == report_id).all()
            
            # Get summaries for the report
            summaries = db.query(Summary).filter(Summary.report_id == report_id).all()
            
            # Get entities for the report
            entities = db.query(Entity).filter(Entity.report_id == report_id).all()
            
            # Get sentiment analysis for the report
            sentiment = db.query(SentimentAnalysis).filter(SentimentAnalysis.report_id == report_id).first()
            
            # Get risk assessment for the report
            risk = db.query(RiskAssessment).filter(RiskAssessment.report_id == report_id).first()
            
            # Format the response
            result = {
                "id": report.id,
                "company_id": report.company_id,
                "company_name": report.company.name if report.company else None,
                "ticker": report.company.ticker if report.company else None,
                "sector": report.company.sector if report.company else None,
                "year": report.year,
                "file_path": report.file_path,
                "upload_date": report.upload_date.isoformat(),
                "processing_status": report.processing_status,
                "metrics": [{"name": m.name, "value": m.value, "unit": m.unit} for m in metrics],
                "summaries": {s.category: s.content for s in summaries},
                "entities": [{"name": e.name, "type": e.entity_type, "mentions": e.mention_count, "sentiment": e.sentiment_score} for e in entities],
                "sentiment": {
                    "overall_score": sentiment.overall_score if sentiment else None,
                    "positive_sections": sentiment.positive_sections if sentiment else None,
                    "negative_sections": sentiment.negative_sections if sentiment else None
                } if sentiment else None,
                "risk_assessment": {
                    "overall_risk_score": risk.overall_risk_score if risk else None,
                    "risk_factors": json.loads(risk.risk_factors) if risk and risk.risk_factors else None
                } if risk else None
            }
            
            logger.info(f"Retrieved full data for report ID {report_id}")
            return result, None
            
        except SQLAlchemyError as e:
            error_msg = f"Database error retrieving report {report_id}: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error retrieving report {report_id}: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    @staticmethod
    def get_company_reports_by_year(db: Session, company_id: int) -> Dict[int, Report]:
        """Get all reports for a company organized by year."""
        try:
            reports = db.query(Report).filter(Report.company_id == company_id).all()
            return {report.year: report for report in reports}
        except Exception as e:
            logger.error(f"Error getting company reports by year: {str(e)}")
            raise
    
    @staticmethod
    def get_metrics_by_name_and_company(
        db: Session, 
        company_id: int, 
        metric_name: str
    ) -> List[Dict[str, Any]]:
        """Get metrics by name for a company across all reports."""
        try:
            results = (
                db.query(Metric, Report.year)
                .join(Report, Metric.report_id == Report.id)
                .filter(Report.company_id == company_id, Metric.name == metric_name)
                .order_by(Report.year)
                .all()
            )
            
            return [
                {
                    "year": year,
                    "name": metric.name,
                    "value": metric.value,
                    "unit": metric.unit
                }
                for metric, year in results
            ]
        except Exception as e:
            logger.error(f"Error getting metrics by name and company: {str(e)}")
            raise
    
    @staticmethod
    def get_company_count(db: Session) -> int:
        """Get the total number of companies in the database."""
        try:
            return db.query(Company).count()
        except Exception as e:
            logger.error(f"Error getting company count: {str(e)}")
            return 0
    
    @staticmethod
    def get_report_count(db: Session) -> int:
        """Get the total number of reports in the database."""
        try:
            return db.query(Report).count()
        except Exception as e:
            logger.error(f"Error getting report count: {str(e)}")
            return 0
    
    @staticmethod
    def get_recent_reports(db: Session, limit: int = 5) -> List[Report]:
        """Get the most recently uploaded reports."""
        try:
            return db.query(Report).order_by(desc(Report.upload_date)).limit(limit).all()
        except Exception as e:
            logger.error(f"Error getting recent reports: {str(e)}")
            return []
    
    @staticmethod
    def get_company_metrics(db: Session, company_id: int, metric_names: Optional[List[str]] = None) -> Tuple[Optional[Dict[str, List[Dict[str, Any]]]], Optional[str]]:
        """
        Get metrics for a company, optionally filtered by metric names.
        
        Args:
            db: Database session
            company_id: ID of the company
            metric_names: Optional list of metric names to filter by
            
        Returns:
            Tuple containing:
            - Dictionary of metrics by name or None if error
            - Error message or None if successful
        """
        try:
            # Get all reports for this company
            reports = db.query(Report).filter(Report.company_id == company_id).all()
            
            if not reports:
                logger.warning(f"No reports found for company ID {company_id}")
                return {"metrics": {}}, None
            
            # Get report IDs
            report_ids = [report.id for report in reports]
            
            # Base query for metrics
            metrics_query = db.query(Metric).filter(Metric.report_id.in_(report_ids))
            
            # Apply metric name filter if provided
            if metric_names and len(metric_names) > 0:
                metrics_query = metrics_query.filter(Metric.name.in_(metric_names))
            
            # Execute query
            metrics = metrics_query.all()
            
            # Group metrics by name
            metrics_by_name = {}
            for metric in metrics:
                if metric.name not in metrics_by_name:
                    metrics_by_name[metric.name] = []
                
                # Get the report year for this metric
                report = db.query(Report).filter(Report.id == metric.report_id).first()
                year = report.year if report else None
                
                metrics_by_name[metric.name].append({
                    "id": metric.id,
                    "year": year,
                    "value": metric.value,
                    "unit": metric.unit
                })
            
            # Sort each metric list by year
            for name in metrics_by_name:
                metrics_by_name[name] = sorted(metrics_by_name[name], key=lambda x: x["year"] if x["year"] else 0)
            
            logger.info(f"Retrieved metrics for company ID {company_id}")
            return {"metrics": metrics_by_name}, None
        except SQLAlchemyError as e:
            error_msg = f"Database error retrieving metrics for company {company_id}: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error retrieving metrics for company {company_id}: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    @staticmethod
    def create_entity(db: Session, entity: EntityCreate) -> Entity:
        """Create a new entity."""
        try:
            db_entity = Entity(
                report_id=entity.report_id,
                entity_type=entity.entity_type,
                text=entity.text,
                score=entity.score,
                section=entity.section
            )
            db.add(db_entity)
            db.commit()
            db.refresh(db_entity)
            return db_entity
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating entity: {str(e)}")
            raise
    
    @staticmethod
    def create_sentiment_analysis(db: Session, sentiment: SentimentAnalysisCreate) -> SentimentAnalysis:
        """Create a new sentiment analysis."""
        try:
            db_sentiment = SentimentAnalysis(
                report_id=sentiment.report_id,
                section=sentiment.section,
                sentiment=sentiment.sentiment,
                score=sentiment.score,
                distribution=sentiment.distribution,
                insight=sentiment.insight
            )
            db.add(db_sentiment)
            db.commit()
            db.refresh(db_sentiment)
            return db_sentiment
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating sentiment analysis: {str(e)}")
            raise
    
    @staticmethod
    def create_risk_assessment(db: Session, risk: RiskAssessmentCreate) -> RiskAssessment:
        """Create a new risk assessment."""
        try:
            db_risk = RiskAssessment(
                report_id=risk.report_id,
                overall_score=risk.overall_score,
                categories=risk.categories,
                primary_factors=risk.primary_factors,
                insight=risk.insight
            )
            db.add(db_risk)
            db.commit()
            db.refresh(db_risk)
            return db_risk
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating risk assessment: {str(e)}")
            raise
    
    @staticmethod
    def get_entities_by_report_id(db: Session, report_id: int) -> List[Entity]:
        """Get all entities for a report."""
        return db.query(Entity).filter(Entity.report_id == report_id).all()
    
    @staticmethod
    def get_sentiment_analysis_by_report_id(db: Session, report_id: int) -> Optional[SentimentAnalysis]:
        """Get sentiment analysis for a report."""
        return db.query(SentimentAnalysis).filter(SentimentAnalysis.report_id == report_id).first()
    
    @staticmethod
    def get_risk_assessment_by_report_id(db: Session, report_id: int) -> Optional[RiskAssessment]:
        """Get risk assessment for a report."""
        return db.query(RiskAssessment).filter(RiskAssessment.report_id == report_id).first()
    
    @staticmethod
    def get_report_by_id(db: Session, report_id: int) -> Optional[Report]:
        """Get a report by ID."""
        return db.query(Report).filter(Report.id == report_id).first() 