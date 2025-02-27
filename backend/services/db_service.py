import logging
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from datetime import datetime

from backend.models.database import Company, Report, Metric, Summary
from backend.models.schemas import (
    CompanyCreate, CompanyUpdate, ReportCreate, 
    MetricCreate, SummaryCreate, SearchParams
)

logger = logging.getLogger(__name__)

class DBService:
    """Service for database operations."""
    
    @staticmethod
    def create_company(db: Session, company: CompanyCreate) -> Company:
        """Create a new company."""
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
            return db_company
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating company: {str(e)}")
            raise
    
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
    def update_report_status(db: Session, report_id: int, status: str) -> Optional[Report]:
        """Update the processing status of a report."""
        try:
            db_report = db.query(Report).filter(Report.id == report_id).first()
            if not db_report:
                return None
            
            db_report.processing_status = status
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
    def get_metrics_by_report(db: Session, report_id: int) -> List[Metric]:
        """Get all metrics for a report."""
        try:
            return db.query(Metric).filter(Metric.report_id == report_id).all()
        except Exception as e:
            logger.error(f"Error getting metrics by report: {str(e)}")
            raise
    
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
        """Get a report by ID with its associated company."""
        try:
            return db.query(Report).filter(Report.id == report_id).join(Report.company).first()
        except Exception as e:
            logger.error(f"Error getting report with company: {str(e)}")
            raise
    
    @staticmethod
    def get_report_full_data(db: Session, report_id: int) -> Dict[str, Any]:
        """Get a report with all its associated data (metrics and summaries)."""
        try:
            report = db.query(Report).filter(Report.id == report_id).first()
            if not report:
                return {}
            
            company = db.query(Company).filter(Company.id == report.company_id).first()
            metrics = db.query(Metric).filter(Metric.report_id == report_id).all()
            summaries = db.query(Summary).filter(Summary.report_id == report_id).all()
            
            return {
                "report": report,
                "company": company,
                "metrics": metrics,
                "summaries": summaries
            }
        except Exception as e:
            logger.error(f"Error getting report full data: {str(e)}")
            raise
    
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