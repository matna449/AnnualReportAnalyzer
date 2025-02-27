from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from backend.models.database_session import get_db
from backend.models.schemas import (
    Company, CompanyCreate, CompanyUpdate,
    Report, SearchParams, ComparisonRequest
)
from backend.services.analysis_service import AnalysisService

logger = logging.getLogger(__name__)
router = APIRouter()
analysis_service = AnalysisService()

# Company routes
@router.post("/companies/", response_model=Company)
async def create_company(
    company: CompanyCreate,
    db: Session = Depends(get_db)
):
    """Create a new company."""
    try:
        from backend.services.db_service import DBService
        return DBService.create_company(db, company)
    except Exception as e:
        logger.error(f"Error creating company: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating company: {str(e)}")

@router.get("/companies/", response_model=List[Company])
async def get_companies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all companies with pagination."""
    try:
        from backend.services.db_service import DBService
        return DBService.get_companies(db, skip, limit)
    except Exception as e:
        logger.error(f"Error getting companies: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting companies: {str(e)}")

@router.get("/companies/{company_id}", response_model=Company)
async def get_company(
    company_id: int,
    db: Session = Depends(get_db)
):
    """Get a company by ID."""
    try:
        from backend.services.db_service import DBService
        company = DBService.get_company(db, company_id)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company with ID {company_id} not found")
        return company
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting company: {str(e)}")

@router.put("/companies/{company_id}", response_model=Company)
async def update_company(
    company_id: int,
    company: CompanyUpdate,
    db: Session = Depends(get_db)
):
    """Update a company."""
    try:
        from backend.services.db_service import DBService
        updated_company = DBService.update_company(db, company_id, company)
        if not updated_company:
            raise HTTPException(status_code=404, detail=f"Company with ID {company_id} not found")
        return updated_company
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating company: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating company: {str(e)}")

# Report routes
@router.post("/reports/upload/")
async def upload_report(
    file: UploadFile = File(...),
    company_name: str = Form(...),
    year: int = Form(...),
    ticker: Optional[str] = Form(None),
    sector: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload and process an annual report."""
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            logger.warning(f"Invalid file type attempted: {file.filename}")
            return JSONResponse(
                status_code=400,
                content={"detail": "Only PDF files are supported"}
            )
        
        # Validate year
        current_year = datetime.now().year
        if year < 1900 or year > current_year + 1:
            logger.warning(f"Invalid year provided: {year}")
            return JSONResponse(
                status_code=400,
                content={"detail": f"Year must be between 1900 and {current_year + 1}"}
            )
        
        # Validate company name
        if not company_name or len(company_name.strip()) < 2:
            logger.warning(f"Invalid company name: {company_name}")
            return JSONResponse(
                status_code=400,
                content={"detail": "Company name is required and must be at least 2 characters"}
            )
        
        logger.info(f"Processing upload: {file.filename} for company {company_name}, year {year}")
        
        # Read file content
        try:
            file_content = await file.read()
            if not file_content or len(file_content) < 100:  # Basic check for empty or corrupt files
                return JSONResponse(
                    status_code=400,
                    content={"detail": "File appears to be empty or corrupt"}
                )
        except Exception as e:
            logger.error(f"Error reading uploaded file: {str(e)}")
            return JSONResponse(
                status_code=400,
                content={"detail": f"Error reading uploaded file: {str(e)}"}
            )
        
        # Process the report
        try:
            result = await analysis_service.process_report(
                db, file_content, file.filename, company_name, year, ticker, sector
            )
            
            logger.info(f"Successfully processed report: {file.filename}, report_id: {result['report_id']}")
            
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Report uploaded and processed successfully",
                    "report_id": result["report_id"],
                    "company_id": result["company_id"],
                    "status": result["status"]
                }
            )
        except Exception as e:
            logger.error(f"Error processing report: {str(e)}")
            # Check if the transaction needs to be rolled back
            db.rollback()
            return JSONResponse(
                status_code=500,
                content={"detail": f"Error processing report: {str(e)}"}
            )
            
    except Exception as e:
        logger.error(f"Unexpected error uploading report: {str(e)}")
        # Ensure transaction is rolled back
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error uploading report: {str(e)}"}
        )

@router.get("/reports/")
async def get_reports(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all reports with pagination."""
    try:
        from backend.services.db_service import DBService
        reports = DBService.get_reports(db, skip, limit)
        
        # Convert SQLAlchemy objects to dictionaries
        result = []
        for report in reports:
            company = DBService.get_company(db, report.company_id)
            result.append({
                "id": report.id,
                "company_id": report.company_id,
                "company_name": company.name if company else "",
                "year": report.year,
                "file_name": report.file_name,
                "upload_date": report.upload_date,
                "processing_status": report.processing_status,
                "page_count": report.page_count
            })
        
        return result
    except Exception as e:
        logger.error(f"Error getting reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting reports: {str(e)}")

@router.get("/reports/{report_id}")
async def get_report_analysis(
    report_id: int,
    db: Session = Depends(get_db)
):
    """Get the analysis for a specific report."""
    try:
        result = await analysis_service.get_report_analysis(db, report_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting report analysis: {str(e)}")

@router.get("/companies/{company_id}/reports")
async def get_company_reports(
    company_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all reports for a specific company."""
    try:
        from backend.services.db_service import DBService
        company = DBService.get_company(db, company_id)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company with ID {company_id} not found")
        
        reports = DBService.get_reports_by_company(db, company_id, skip, limit)
        
        # Convert SQLAlchemy objects to dictionaries
        result = []
        for report in reports:
            result.append({
                "id": report.id,
                "company_id": report.company_id,
                "company_name": company.name,
                "year": report.year,
                "file_name": report.file_name,
                "upload_date": report.upload_date,
                "processing_status": report.processing_status,
                "page_count": report.page_count
            })
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting company reports: {str(e)}")

@router.post("/reports/search/")
async def search_reports(
    params: SearchParams,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Search for reports based on various criteria."""
    try:
        from backend.services.db_service import DBService
        reports = DBService.search_reports(db, params, skip, limit)
        
        # Convert SQLAlchemy objects to dictionaries
        result = []
        for report in reports:
            company = DBService.get_company(db, report.company_id)
            result.append({
                "id": report.id,
                "company_id": report.company_id,
                "company_name": company.name if company else "",
                "year": report.year,
                "file_name": report.file_name,
                "upload_date": report.upload_date,
                "processing_status": report.processing_status,
                "page_count": report.page_count
            })
        
        return result
    except Exception as e:
        logger.error(f"Error searching reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching reports: {str(e)}")

@router.post("/reports/compare/")
async def compare_reports(
    comparison: ComparisonRequest,
    db: Session = Depends(get_db)
):
    """Compare multiple reports."""
    try:
        if len(comparison.report_ids) < 2:
            raise HTTPException(status_code=400, detail="At least two reports are required for comparison")
        
        result = await analysis_service.compare_reports(db, comparison.report_ids)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error comparing reports: {str(e)}")

@router.get("/companies/{company_id}/metrics")
async def get_company_metrics_history(
    company_id: int,
    metric_names: List[str] = Query(...),
    db: Session = Depends(get_db)
):
    """Get historical data for specific metrics for a company."""
    try:
        from backend.services.db_service import DBService
        company = DBService.get_company(db, company_id)
        if not company:
            raise HTTPException(status_code=404, detail=f"Company with ID {company_id} not found")
        
        result = await analysis_service.get_company_metrics_history(db, company_id, metric_names)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company metrics history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting company metrics history: {str(e)}")

# Dashboard routes
@router.get("/dashboard/summary")
async def get_dashboard_summary(
    db: Session = Depends(get_db)
):
    """Get summary statistics for the dashboard."""
    try:
        from backend.services.db_service import DBService
        
        # Get total number of companies
        companies = DBService.get_companies(db)
        company_count = len(companies)
        
        # Get total number of reports
        reports = DBService.get_reports(db)
        report_count = len(reports)
        
        # Get latest upload date
        latest_upload_date = None
        if reports:
            latest_upload_date = max(report.upload_date for report in reports)
        
        # Get reports by status
        status_counts = {}
        for report in reports:
            status = report.processing_status
            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1
        
        # Get reports by year
        year_counts = {}
        for report in reports:
            year = report.year
            if year not in year_counts:
                year_counts[year] = 0
            year_counts[year] += 1
        
        return {
            "company_count": company_count,
            "report_count": report_count,
            "latest_upload_date": latest_upload_date,
            "status_counts": status_counts,
            "year_counts": year_counts
        }
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting dashboard summary: {str(e)}")

@router.get("/dashboard/recent-reports")
async def get_recent_reports(
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """Get the most recently uploaded reports for the dashboard."""
    try:
        from backend.services.db_service import DBService
        reports = DBService.get_reports(db, 0, limit)
        
        # Convert SQLAlchemy objects to dictionaries
        result = []
        for report in reports:
            company = DBService.get_company(db, report.company_id)
            result.append({
                "id": report.id,
                "company_id": report.company_id,
                "company_name": company.name if company else "",
                "year": report.year,
                "file_name": report.file_name,
                "upload_date": report.upload_date,
                "processing_status": report.processing_status
            })
        
        return result
    except Exception as e:
        logger.error(f"Error getting recent reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting recent reports: {str(e)}")

@router.get("/dashboard/sectors")
async def get_sector_distribution(
    db: Session = Depends(get_db)
):
    """Get the distribution of companies by sector for the dashboard."""
    try:
        from backend.services.db_service import DBService
        companies = DBService.get_companies(db)
        
        # Count companies by sector
        sector_counts = {}
        for company in companies:
            sector = company.sector or "Unknown"
            if sector not in sector_counts:
                sector_counts[sector] = 0
            sector_counts[sector] += 1
        
        # Convert to list format for frontend
        result = [
            {"sector": sector, "count": count}
            for sector, count in sector_counts.items()
        ]
        
        return result
    except Exception as e:
        logger.error(f"Error getting sector distribution: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting sector distribution: {str(e)}") 