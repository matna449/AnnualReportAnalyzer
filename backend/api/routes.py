from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from models.database_session import get_db
from models.schemas import (
    Company, CompanyCreate, CompanyUpdate,
    Report, SearchParams, ComparisonRequest
)
from services.analysis_service import AnalysisService
from services.db_service import DBService  # Consistent import path

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
    return DBService.create_company(db, company)

@router.get("/companies/", response_model=List[Company])
async def get_companies(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get all companies."""
    return DBService.get_companies(db, skip, limit)

@router.get("/companies/{company_id}", response_model=Company)
async def get_company(
    company_id: int,
    db: Session = Depends(get_db)
):
    """Get a company by ID."""
    company = DBService.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.put("/companies/{company_id}", response_model=Company)
async def update_company(
    company_id: int,
    company: CompanyUpdate,
    db: Session = Depends(get_db)
):
    """Update a company."""
    try:
        updated_company = DBService.update_company(db, company_id, company)
        if updated_company is None:
            raise HTTPException(status_code=404, detail="Company not found")
        return updated_company
    except Exception as e:
        logger.error(f"Error updating company: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Report routes
@router.post("/reports/upload")
async def upload_report(
    file: UploadFile = File(...),
    company_name: str = Form(...),
    year: int = Form(...),
    ticker: Optional[str] = Form(None),
    sector: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload and process an annual report."""
    logger.info(f"Received upload request for file: {file.filename}, company: {company_name}, year: {year}")
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
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """Get all reports."""
    return DBService.get_reports(db, skip, limit)

@router.get("/reports/{report_id}", response_model=Dict[str, Any])
async def get_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    """Get a report by ID with all associated data."""
    report = DBService.get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    result = {
        "id": report.id,
        "company_id": report.company_id,
        "company_name": report.company.name if report.company else "",
        "year": report.year,
        "file_name": report.file_name,
        "upload_date": report.upload_date,
        "processing_status": report.processing_status,
        "page_count": report.page_count
    }
    return result

@router.get("/companies/{company_id}/reports")
async def get_company_reports(
    company_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get reports for a specific company."""
    try:
        company = DBService.get_company(db, company_id)
        if company is None:
            raise HTTPException(status_code=404, detail="Company not found")
        
        reports = DBService.get_reports_by_company(db, company_id, skip, limit)
        
        # Format the response
        result = []
        for report in reports:
            result.append({
                "id": report.id,
                "year": report.year,
                "file_path": report.file_path,
                "upload_date": report.upload_date,
                "processing_status": report.processing_status,
                "company_id": report.company_id,
                "company_name": company.name,
                "company_ticker": company.ticker
            })
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company reports: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/reports/search/", response_model=Dict[str, List])
async def search_reports(
    search_params: SearchParams,
    db: Session = Depends(get_db)
):
    """Search for reports and companies based on search parameters."""
    results = DBService.search_reports(db, search_params)
    return results

@router.post("/reports/compare", response_model=Dict[str, Any])
async def compare_reports(
    comparison_request: ComparisonRequest,
    db: Session = Depends(get_db)
):
    """Compare metrics between multiple reports."""
    result = DBService.compare_reports(db, comparison_request)
    return result

@router.get("/companies/{company_id}/metrics", response_model=Dict[str, List])
async def get_company_metrics(
    company_id: int,
    metric_names: str = Query(None),
    db: Session = Depends(get_db)
):
    """Get metrics for a specific company across all reports."""
    # Parse metric names if provided
    metric_list = None
    if metric_names:
        metric_list = [name.strip() for name in metric_names.split(",")]
    
    metrics = DBService.get_company_metrics(db, company_id, metric_list)
    return metrics

# Dashboard routes
@router.get("/dashboard/summary", response_model=Dict[str, Any])
async def get_dashboard_summary(
    db: Session = Depends(get_db)
):
    """Get summary statistics for the dashboard."""
    try:
        # Get counts
        company_count = DBService.get_company_count(db)
        report_count = DBService.get_report_count(db)
        
        # Get latest upload date
        latest_upload_date = None
        if report_count > 0:
            latest_upload_date = max(report.upload_date for report in DBService.get_reports(db))
        
        # Get reports by status
        status_counts = {}
        for report in DBService.get_reports(db):
            status = report.processing_status
            if status not in status_counts:
                status_counts[status] = 0
            status_counts[status] += 1
        
        # Get reports by year
        year_counts = {}
        for report in DBService.get_reports(db):
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
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/dashboard/recent-reports", response_model=List[Dict[str, Any]])
async def get_recent_reports(
    db: Session = Depends(get_db),
    limit: int = 5
):
    """Get the most recently uploaded reports for the dashboard."""
    reports = DBService.get_recent_reports(db, limit)
    
    result = []
    for report in reports:
        result.append({
            "id": report.id,
            "company_id": report.company_id,
            "company_name": report.company.name if report.company else "",
            "year": report.year,
            "file_name": report.file_name,
            "upload_date": report.upload_date,
            "processing_status": report.processing_status
        })
    
    return result

@router.get("/dashboard/sectors")
async def get_sector_distribution(
    db: Session = Depends(get_db)
):
    """Get distribution of companies by sector."""
    try:
        companies = DBService.get_companies(db)
        
        # Count companies by sector
        sector_counts = {}
        for company in companies:
            sector = company.sector or "Unknown"
            if sector not in sector_counts:
                sector_counts[sector] = 0
            sector_counts[sector] += 1
        
        # Format the response
        result = [
            {"sector": sector, "count": count}
            for sector, count in sector_counts.items()
        ]
        
        return result
    except Exception as e:
        logger.error(f"Error getting sector distribution: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") 