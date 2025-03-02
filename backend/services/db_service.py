import logging
import json
from typing import List, Dict, Any, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, func
from datetime import datetime

from models.database import Company, Report, Metric, Summary, Entity, SentimentAnalysis, RiskAssessment
from models.schemas import (
    CompanyCreate, CompanyUpdate, ReportCreate, 
    MetricCreate, SummaryCreate, SearchParams,
    EntityCreate, SentimentAnalysisCreate, RiskAssessmentCreate
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
    def get_company_metrics(db: Session, company_id: int, metric_names: Optional[List[str]] = None) -> Dict[str, List]:
        """Get metrics for a specific company across all reports.
        
        Args:
            db: Database session
            company_id: ID of the company
            metric_names: Optional list of metric names to filter by
            
        Returns:
            Dictionary with metrics organized by year
        """
        try:
            # Get all reports for the company
            reports = db.query(Report).filter(Report.company_id == company_id).all()
            
            if not reports:
                return {"metrics": []}
            
            # Get all metrics for these reports
            metrics_data = []
            for report in reports:
                query = db.query(Metric).filter(Metric.report_id == report.id)
                
                # Apply metric name filter if provided
                if metric_names:
                    query = query.filter(Metric.name.in_(metric_names))
                
                report_metrics = query.all()
                
                # Add year to each metric
                for metric in report_metrics:
                    metrics_data.append({
                        "id": metric.id,
                        "name": metric.name,
                        "value": metric.value,
                        "unit": metric.unit,
                        "category": metric.category,
                        "year": report.year,
                        "report_id": report.id
                    })
            
            return {"metrics": metrics_data}
        except Exception as e:
            logger.error(f"Error getting company metrics: {str(e)}")
            raise
    
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
    def store_enhanced_analysis(db: Session, report_id: int, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store enhanced analysis results including entities, sentiment, and risk assessment.
        
        Args:
            db: Database session
            report_id: ID of the report
            analysis_results: Dictionary with analysis results
            
        Returns:
            Dictionary with stored analysis IDs
        """
        result_ids = {}
        
        try:
            # Store entities
            if "entities" in analysis_results and "entities" in analysis_results["entities"]:
                entities = analysis_results["entities"]["entities"]
                entity_ids = []
                
                for entity_type, entity_list in entities.items():
                    for entity in entity_list:
                        entity_create = EntityCreate(
                            report_id=report_id,
                            entity_type=entity_type,
                            text=entity["text"],
                            score=entity.get("score", 0.0),
                            section=None  # Could be added if section info is available
                        )
                        db_entity = DBService.create_entity(db, entity_create)
                        entity_ids.append(db_entity.id)
                
                result_ids["entity_ids"] = entity_ids
            
            # Store sentiment analysis
            if "sentiment" in analysis_results:
                sentiment = analysis_results["sentiment"]
                sentiment_create = SentimentAnalysisCreate(
                    report_id=report_id,
                    sentiment=sentiment.get("sentiment", "neutral"),
                    score=sentiment.get("score", 0.5),
                    distribution=sentiment.get("sentiment_distribution", {}),
                    insight=analysis_results.get("insights", {}).get("sentiment")
                )
                db_sentiment = DBService.create_sentiment_analysis(db, sentiment_create)
                result_ids["sentiment_id"] = db_sentiment.id
            
            # Store risk assessment
            if "risk" in analysis_results:
                risk = analysis_results["risk"]
                risk_create = RiskAssessmentCreate(
                    report_id=report_id,
                    overall_score=risk.get("overall_risk_score", 0.0),
                    categories=risk.get("risk_categories", {}),
                    primary_factors=risk.get("primary_risk_factors", []),
                    insight=analysis_results.get("insights", {}).get("risk")
                )
                db_risk = DBService.create_risk_assessment(db, risk_create)
                result_ids["risk_id"] = db_risk.id
            
            # Store overall insight as a summary
            if "insights" in analysis_results and "overall" in analysis_results["insights"]:
                summary_create = SummaryCreate(
                    report_id=report_id,
                    category="ai_insight",
                    content=analysis_results["insights"]["overall"]
                )
                db_summary = DBService.create_summary(db, summary_create)
                result_ids["summary_id"] = db_summary.id
            
            return result_ids
        
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing enhanced analysis: {str(e)}")
            raise
    
    @staticmethod
    def get_enhanced_analysis_by_report_id(db: Session, report_id: int) -> Dict[str, Any]:
        """
        Get enhanced analysis results for a report.
        
        Args:
            db: Database session
            report_id: ID of the report
            
        Returns:
            Dictionary with enhanced analysis results
        """
        try:
            # Get entities
            entities = DBService.get_entities_by_report_id(db, report_id)
            
            # Organize entities by type
            entity_dict = {}
            for entity in entities:
                if entity.entity_type not in entity_dict:
                    entity_dict[entity.entity_type] = []
                
                entity_dict[entity.entity_type].append({
                    "id": entity.id,
                    "text": entity.text,
                    "score": entity.score,
                    "section": entity.section
                })
            
            # Get sentiment analysis
            sentiment = DBService.get_sentiment_analysis_by_report_id(db, report_id)
            sentiment_dict = None
            if sentiment:
                sentiment_dict = {
                    "id": sentiment.id,
                    "sentiment": sentiment.sentiment,
                    "score": sentiment.score,
                    "distribution": sentiment.distribution,
                    "insight": sentiment.insight
                }
            
            # Get risk assessment
            risk = DBService.get_risk_assessment_by_report_id(db, report_id)
            risk_dict = None
            if risk:
                risk_dict = {
                    "id": risk.id,
                    "overall_score": risk.overall_score,
                    "categories": risk.categories,
                    "primary_factors": risk.primary_factors,
                    "insight": risk.insight
                }
            
            # Get AI insight summary
            ai_insight = db.query(Summary).filter(
                Summary.report_id == report_id,
                Summary.category == "ai_insight"
            ).first()
            
            insights = {}
            if sentiment and sentiment.insight:
                insights["sentiment"] = sentiment.insight
            if risk and risk.insight:
                insights["risk"] = risk.insight
            if ai_insight:
                insights["overall"] = ai_insight.content
            
            return {
                "entities": entity_dict,
                "sentiment": sentiment_dict,
                "risk": risk_dict,
                "insights": insights
            }
        
        except Exception as e:
            logger.error(f"Error getting enhanced analysis: {str(e)}")
            return {
                "entities": {},
                "sentiment": None,
                "risk": None,
                "insights": {},
                "error": str(e)
            }
    
    @staticmethod
    def get_report_by_id(db: Session, report_id: int) -> Optional[Report]:
        """Get a report by ID."""
        return db.query(Report).filter(Report.id == report_id).first() 