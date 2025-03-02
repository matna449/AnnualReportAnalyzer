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
from api.pdf_processing_routes import router as pdf_router

logger = logging.getLogger(__name__)
router = APIRouter()
analysis_service = AnalysisService()

# Include PDF processing routes
router.include_router(pdf_router)

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
    """Compare metrics and summaries between multiple reports."""
    try:
        # Validate report IDs
        report_ids = comparison_request.report_ids
        if len(report_ids) < 2:
            raise HTTPException(status_code=400, detail="At least two reports are required for comparison")
        
        # Get reports data
        reports_data = []
        for report_id in report_ids:
            report = DBService.get_report(db, report_id)
            if not report:
                raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
            reports_data.append(report)
        
        # Get metrics for comparison
        metrics_comparison = {}
        for report in reports_data:
            metrics = db.query(Metric).filter(Metric.report_id == report.id).all()
            
            # Filter metrics if specified
            if comparison_request.metrics:
                metrics = [m for m in metrics if m.name in comparison_request.metrics]
            
            # Organize metrics by name
            for metric in metrics:
                if metric.name not in metrics_comparison:
                    metrics_comparison[metric.name] = {}
                
                metrics_comparison[metric.name][report.id] = {
                    "value": metric.value,
                    "unit": metric.unit,
                    "year": report.year,
                    "company_name": report.company.name if report.company else "Unknown"
                }
        
        # Get summaries for comparison
        summaries_comparison = {}
        for report in reports_data:
            summaries = DBService.get_summaries_by_report(db, report.id)
            
            # Organize summaries by category
            report_summaries = {}
            for summary in summaries:
                report_summaries[summary.category] = summary.content
            
            summaries_comparison[report.id] = {
                "summaries": report_summaries,
                "year": report.year,
                "company_name": report.company.name if report.company else "Unknown"
            }
        
        # Generate AI comparison analysis if available
        comparison_analysis = {}
        try:
            # Get the summaries for each report
            report1_summaries = summaries_comparison[report_ids[0]]["summaries"]
            report2_summaries = summaries_comparison[report_ids[1]]["summaries"]
            
            # Compare executive summaries
            if "executive" in report1_summaries and "executive" in report2_summaries:
                comparison_analysis["executive"] = await analysis_service.compare_texts(
                    report1_summaries["executive"],
                    report2_summaries["executive"],
                    "Compare these two executive summaries and highlight key differences and similarities:"
                )
            
            # Compare risk factors
            if "risks" in report1_summaries and "risks" in report2_summaries:
                comparison_analysis["risks"] = await analysis_service.compare_texts(
                    report1_summaries["risks"],
                    report2_summaries["risks"],
                    "Compare these two risk assessments and identify which report presents higher risks:"
                )
            
            # Compare business outlook
            if "outlook" in report1_summaries and "outlook" in report2_summaries:
                comparison_analysis["outlook"] = await analysis_service.compare_texts(
                    report1_summaries["outlook"],
                    report2_summaries["outlook"],
                    "Compare these two business outlooks and determine which is more optimistic:"
                )
            
            # Compare sentiment
            if "sentiment" in report1_summaries and "sentiment" in report2_summaries:
                comparison_analysis["sentiment"] = await analysis_service.compare_texts(
                    report1_summaries["sentiment"],
                    report2_summaries["sentiment"],
                    "Compare these two sentiment analyses and determine which report has a more positive tone:"
                )
        except Exception as e:
            logger.warning(f"Error generating AI comparison: {str(e)}")
            comparison_analysis = {"error": str(e)}
        
        # Format the response
        result = {
            "reports": [
                {
                    "id": report.id,
                    "company_id": report.company_id,
                    "company_name": report.company.name if report.company else "Unknown",
                    "year": report.year,
                    "file_name": report.file_name
                }
                for report in reports_data
            ],
            "metrics_comparison": metrics_comparison,
            "summaries_comparison": summaries_comparison,
            "ai_analysis": comparison_analysis
        }
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error comparing reports: {str(e)}")

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
        latest_report_id = None
        if report_count > 0:
            recent_reports = DBService.get_recent_reports(db, limit=1)
            if recent_reports:
                latest_report = recent_reports[0]
                latest_upload_date = latest_report.upload_date
                latest_report_id = latest_report.id
        
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
        
        # Get latest summaries if available
        latest_summaries = {}
        if latest_report_id:
            summaries = DBService.get_summaries_by_report(db, latest_report_id)
            for summary in summaries:
                latest_summaries[summary.category] = summary.content
        
        return {
            "company_count": company_count,
            "report_count": report_count,
            "latest_upload_date": latest_upload_date,
            "status_counts": status_counts,
            "year_counts": year_counts,
            "latest_summaries": latest_summaries
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

@router.get("/reports/{report_id}/summaries", response_model=Dict[str, str])
async def get_report_summaries(
    report_id: int,
    db: Session = Depends(get_db)
):
    """Get all summaries for a specific report, organized by category."""
    try:
        summaries = DBService.get_summaries_by_report(db, report_id)
        
        # Organize summaries by category
        summaries_by_category = {}
        for summary in summaries:
            summaries_by_category[summary.category] = summary.content
            
        return summaries_by_category
    except Exception as e:
        logger.error(f"Error fetching summaries for report {report_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching summaries: {str(e)}") 