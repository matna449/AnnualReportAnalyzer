"""
API routes for PDF processing
"""

import os
import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional

from models.database_session import get_db
from services.pdf_processor import PDFProcessor
from services.db_service import DBService
from models.schemas import CompanyCreate, ReportCreate
from models.database import Report

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/pdf",
    tags=["pdf-processing"],
    responses={404: {"description": "Not found"}},
)

@router.post("/process")
async def process_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    company_name: str = Form(...),
    year: str = Form(...),
    ticker: Optional[str] = Form(None),
    sector: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Process a PDF file in the background.
    
    Args:
        background_tasks: FastAPI background tasks
        file: Uploaded PDF file
        company_name: Name of the company
        year: Year of the report
        ticker: Company ticker symbol (optional)
        sector: Company sector (optional)
        db: Database session
        
    Returns:
        Dict with report ID and status
    """
    try:
        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # Initialize services
        db_service = DBService()
        
        # Check if company exists, create if not
        company = db_service.get_company_by_name(db, company_name)
        if not company:
            logger.info(f"Creating new company: {company_name}")
            company_create = CompanyCreate(
                name=company_name,
                ticker=ticker or "",
                sector=sector or ""
            )
            company = db_service.create_company(db, company_create)
        
        # Save the uploaded file
        uploads_dir = os.path.join(os.getcwd(), "uploads")
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
        
        file_content = await file.read()
        file_path = os.path.join(uploads_dir, file.filename)
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Create report entry
        report_create = ReportCreate(
            company_id=company.id,
            year=year,
            file_path=file_path,
            file_name=file.filename,
            processing_status="pending"
        )
        report = db_service.create_report(db, report_create)
        
        # Add background task to process the report
        background_tasks.add_task(process_report_background, report.id, file_path)
        
        return {
            "report_id": report.id,
            "status": "processing",
            "message": "Report processing started in the background"
        }
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

async def process_report_background(report_id: int, file_path: str):
    """
    Process a report in the background.
    
    Args:
        report_id: ID of the report in the database
        file_path: Path to the PDF file
    """
    logger.info(f"Starting background processing of report {report_id}")
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"File path: {file_path}")
    logger.info(f"File exists: {os.path.exists(file_path)}")
    
    db = None
    try:
        # Get database session
        db_generator = get_db()
        db = next(db_generator)
        logger.info(f"Successfully connected to database for report {report_id}")
        
        # Update report status to processing
        db_service = DBService()
        db_service.update_report_status(db, report_id, "processing")
        
        # Process the report
        pdf_processor = PDFProcessor()
        result = pdf_processor.process_annual_report(file_path, report_id, db)
        
        if "error" in result:
            logger.error(f"Error processing report {report_id}: {result['error']}")
            db_service.update_report_status(db, report_id, "failed")
        else:
            logger.info(f"Successfully processed report {report_id}")
            # Status is already updated to completed in the processor
            
    except Exception as e:
        logger.error(f"Error in background processing of report {report_id}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Try to update report status to failed
        if db:
            try:
                db_service = DBService()
                db_service.update_report_status(db, report_id, "failed")
            except Exception as update_error:
                logger.error(f"Failed to update report status: {update_error}")
    finally:
        # Close database connection
        if db:
            try:
                db.close()
                logger.info(f"Database connection closed for report {report_id}")
            except Exception as close_error:
                logger.error(f"Error closing database connection: {close_error}")

@router.get("/status/{report_id}")
async def get_processing_status(
    report_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the processing status of a report.
    
    Args:
        report_id: ID of the report
        db: Database session
        
    Returns:
        Dict with report status and details
    """
    try:
        db_service = DBService()
        report = db_service.get_report(db, report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
        
        return {
            "report_id": report.id,
            "status": report.processing_status,
            "company_id": report.company_id,
            "year": report.year,
            "file_name": report.file_name,
            "upload_date": report.upload_date
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting report status: {str(e)}")

@router.get("/metrics/{report_id}")
async def get_report_metrics(
    report_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the metrics for a processed report.
    
    Args:
        report_id: ID of the report
        db: Database session
        
    Returns:
        Dict with report metrics
    """
    try:
        db_service = DBService()
        report = db_service.get_report(db, report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
        
        if report.processing_status != "completed":
            return {
                "report_id": report.id,
                "status": report.processing_status,
                "metrics": [],
                "message": f"Report processing status: {report.processing_status}"
            }
        
        metrics = db_service.get_metrics_by_report(db, report_id)
        
        # Group metrics by category
        grouped_metrics = {}
        for metric in metrics:
            category = metric.category or "other"
            if category not in grouped_metrics:
                grouped_metrics[category] = []
            
            grouped_metrics[category].append({
                "id": metric.id,
                "name": metric.name,
                "value": metric.value,
                "unit": metric.unit
            })
        
        return {
            "report_id": report.id,
            "status": report.processing_status,
            "metrics": grouped_metrics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting report metrics: {str(e)}")

@router.get("/insights/{report_id}")
async def get_report_insights(
    report_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the AI-generated insights for a processed report.
    
    Args:
        report_id: ID of the report
        db: Database session
        
    Returns:
        Dict with report insights
    """
    try:
        db_service = DBService()
        report = db_service.get_report(db, report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
        
        if report.processing_status != "completed":
            return {
                "report_id": report.id,
                "status": report.processing_status,
                "insights": [],
                "message": f"Report processing status: {report.processing_status}"
            }
        
        summaries = db_service.get_summaries_by_report(db, report_id)
        
        insights = {}
        for summary in summaries:
            insights[summary.category] = summary.content
        
        return {
            "report_id": report.id,
            "status": report.processing_status,
            "insights": insights
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting report insights: {str(e)}")

@router.get("/reports/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if report is None:
            raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving report {report_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") 