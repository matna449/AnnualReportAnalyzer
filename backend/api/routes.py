from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import os
import time
import re

from models.database_session import get_db
from models.schemas import (
    Company, CompanyCreate, CompanyUpdate,
    Report, SearchParams, ComparisonRequest,
    MetricCreate, Metric,
    SummaryCreate, Summary,
    UploadResponse, AnalysisResult,
    ComparisonResult,
    EntityCreate, SentimentAnalysisCreate, RiskAssessmentCreate,
    ReportCreate
)
from services.analysis_service import AnalysisService
from services.db_service import DBService  # Consistent import path
from api.pdf_processing_routes import router as pdf_router
from services.file_service import FileService
from services.huggingface_service import HuggingFaceService

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
    """
    Create a new company.
    
    Note: This endpoint is currently not used by the frontend.
    It's available for administrative purposes or future integration.
    
    Args:
        company: Company data to create
        db: Database session (injected)
        
    Returns:
        Created company object
        
    Raises:
        HTTPException: If company creation fails
    """
    company_obj, error = DBService.create_company(db, company)
    
    if error:
        logger.error(f"Error creating company: {error}")
        raise HTTPException(status_code=500, detail=error)
        
    return company_obj

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
    """
    Update an existing company.
    
    Note: This endpoint is currently not used by the frontend.
    It's available for administrative purposes or future integration.
    
    Args:
        company_id: ID of the company to update
        company: Updated company data
        db: Database session (injected)
        
    Returns:
        Updated company object
        
    Raises:
        HTTPException: If company not found or update fails
    """
    updated_company, error = DBService.update_company(db, company_id, company)
    
    if error:
        logger.error(f"Error updating company {company_id}: {error}")
        if "not found" in error.lower():
            raise HTTPException(status_code=404, detail=error)
        raise HTTPException(status_code=500, detail=error)
        
    return updated_company

# Report routes
@router.post("/reports/upload")
async def upload_report(
    file: UploadFile = File(...),
    company_name: str = Form(...),
    year: int = Form(...),
    ticker: Optional[str] = Form(None),
    sector: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Upload a report and start analysis.
    """
    try:
        logger.info(f"===== PIPELINE: UPLOAD STARTED =====")
        
        # Basic validation
        if not file.filename.lower().endswith('.pdf'):
            logger.warning(f"PIPELINE: UPLOAD REJECTED - File type not PDF: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail="File must be a PDF"
            )
        
        if not year or year < 1900 or year > datetime.now().year:
            logger.warning(f"PIPELINE: UPLOAD REJECTED - Invalid year: {year}")
            raise HTTPException(
                status_code=400,
                detail="Year must be valid (between 1900 and current year)"
            )
            
        if not company_name:
            logger.warning(f"PIPELINE: UPLOAD REJECTED - Missing company name")
            raise HTTPException(
                status_code=400,
                detail="Company name is required"
            )
        
        # Get or create company
        logger.info(f"PIPELINE: Creating or retrieving company: {company_name}")
        company = DBService.get_company_by_name(db, company_name)
        if not company:
            company_result = DBService.create_company(db, CompanyCreate(
                name=company_name,
                ticker=ticker,
                sector=sector
            ))
            
            # Handle the tuple return value (company, error_message)
            if isinstance(company_result, tuple) and len(company_result) == 2:
                company, error_message = company_result
                if error_message:
                    logger.error(f"PIPELINE: Error creating company: {error_message}")
                    return JSONResponse(
                        status_code=500,
                        content={"error": f"Error creating company: {error_message}"}
                    )
            else:
                company = company_result  # For backward compatibility
                
            logger.info(f"PIPELINE: Created new company with ID {company.id}")
        else:
            logger.info(f"PIPELINE: Found existing company with ID {company.id}")
            
        # Save the file
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '', company_name.replace(' ', '_'))
        filename = f"{sanitized_name}_{year}_{timestamp}.pdf"
        file_path = os.path.join("uploads", filename)
        
        # Create uploads directory if it doesn't exist
        if not os.path.exists("uploads"):
            os.makedirs("uploads")
            
        logger.info(f"PIPELINE: Saving PDF file to {file_path}")
        
        # Handle potential tuples or lists in file object
        file_obj = file
        if isinstance(file, tuple) or isinstance(file, list):
            logger.info(f"PIPELINE: File object is a tuple/list, extracting first element")
            file_obj = file[0] if len(file) > 0 else None
            if not file_obj:
                logger.error("PIPELINE: UPLOAD FAILED - Invalid file tuple/list")
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid file object received"}
                )
        
        # Now safely use file_obj
        with open(file_path, "wb") as buffer:
            buffer.write(await file_obj.read())
        
        # Create report
        logger.info(f"PIPELINE: Creating report record for company {company.id}")
        report_create = ReportCreate(
            company_id=company.id,
            year=str(year),
            file_name=file_obj.filename if hasattr(file_obj, 'filename') else filename,
            file_path=file_path,
            processing_status="pending"
        )
        db_report = DBService.create_report(db, report_create)
        logger.info(f"PIPELINE: Created report with ID {db_report.id}, status: pending")
        
        # Start analysis in background
        logger.info(f"PIPELINE: Starting background analysis task for report {db_report.id}")
        background_tasks.add_task(
            analysis_service.analyze_report,
            db=db,
            report_id=db_report.id
        )
        
        logger.info(f"===== PIPELINE: UPLOAD COMPLETE - Report ID: {db_report.id} =====")
        
        return JSONResponse(
            status_code=200,
            content={
                "report_id": db_report.id,
                "company_id": company.id,
                "status": "pending",
                "message": f"Report uploaded successfully. Analysis started in background."
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PIPELINE: UPLOAD FAILED - {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error uploading file: {str(e)}"}
        )

@router.get("/reports/", response_model=List[Dict[str, Any]])
async def get_reports(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Get a list of all reports with pagination.
    
    Note: This endpoint is currently not directly used by the frontend.
    The dashboard and search pages use more specific endpoints instead.
    This endpoint is maintained for API completeness and future use.
    
    Args:
        db: Database session (injected)
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        
    Returns:
        List of report objects
    """
    reports = DBService.get_reports(db, skip, limit)
    
    return [
        {
            "id": report.id,
            "company_name": report.company.name if report.company else "Unknown",
            "ticker": report.company.ticker if report.company else None,
            "year": report.year,
            "upload_date": report.upload_date.isoformat(),
            "processing_status": report.processing_status
        }
        for report in reports
    ]

@router.get("/reports/{report_id}", response_model=Dict[str, Any])
async def get_report(
    report_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific report by ID with all associated data.
    
    Args:
        report_id: The ID of the report to retrieve
        db: Database session (injected)
        
    Returns:
        Complete report data with metrics and summaries
        
    Raises:
        HTTPException: If report is not found or database error occurs
    """
    report_data, error = DBService.get_report_full_data(db, report_id)
    
    if error:
        logger.error(f"Error retrieving report {report_id}: {error}")
        raise HTTPException(status_code=404 if "not found" in error.lower() else 500, 
                           detail=error)
    
    return report_data

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
    """
    Compare two or more annual reports and generate AI analysis of differences.
    
    Args:
        comparison_request: Request containing list of report IDs to compare
        db: Database session (injected)
        
    Returns:
        Dictionary with comparison data and analysis
        
    Raises:
        HTTPException: If reports not found or comparison fails
    """
    report_ids = comparison_request.report_ids
    
    if len(report_ids) < 2:
        raise HTTPException(status_code=400, detail="At least two reports are required for comparison")
    
    try:
        # Fetch all reports in a single query with their company relationships
        reports = db.query(Report).filter(Report.id.in_(report_ids)).options(
            joinedload(Report.company)
        ).all()
        
        if len(reports) != len(report_ids):
            raise HTTPException(status_code=404, detail="One or more reports not found")
        
        # Map reports by ID for easy access
        reports_by_id = {report.id: report for report in reports}
        
        # Collect all report IDs for batch loading summaries
        all_report_ids = list(reports_by_id.keys())
        
        # Fetch all summaries for these reports in a single query
        all_summaries = db.query(Summary).filter(
            Summary.report_id.in_(all_report_ids)
        ).all()
        
        # Group summaries by report ID
        summaries_by_report = {}
        for summary in all_summaries:
            if summary.report_id not in summaries_by_report:
                summaries_by_report[summary.report_id] = []
            summaries_by_report[summary.report_id].append(summary)
        
        # Format the report data for comparison
        comparison_data = {
            "reports": []
        }
        
        # Process each report
        for report_id in report_ids:
            report = reports_by_id.get(report_id)
            report_summaries = {}
            
            # Process summaries for this report
            for summary in summaries_by_report.get(report_id, []):
                report_summaries[summary.category] = summary.content
            
            # Add report data to comparison result
            comparison_data["reports"].append({
                "id": report.id,
                "company_id": report.company_id,
                "company_name": report.company.name if report.company else "Unknown",
                "year": report.year,
                "summaries": report_summaries
            })
        
        # Generate AI comparison analysis if available
        if len(report_ids) == 2:
            comparison_analysis = {}
            report1_data = comparison_data["reports"][0]
            report2_data = comparison_data["reports"][1]
            
            # Compare executive summaries
            if "executive" in report1_data["summaries"] and "executive" in report2_data["summaries"]:
                comparison_analysis["executive"] = await analysis_service.compare_texts(
                    report1_data["summaries"]["executive"],
                    report2_data["summaries"]["executive"],
                    "Compare these two executive summaries and highlight key differences and similarities:"
                )
            
            # Compare risk factors
            if "risks" in report1_data["summaries"] and "risks" in report2_data["summaries"]:
                comparison_analysis["risks"] = await analysis_service.compare_texts(
                    report1_data["summaries"]["risks"],
                    report2_data["summaries"]["risks"],
                    "Compare these two risk assessments and identify which report presents higher risks:"
                )
            
            # Compare business outlook
            if "outlook" in report1_data["summaries"] and "outlook" in report2_data["summaries"]:
                comparison_analysis["outlook"] = await analysis_service.compare_texts(
                    report1_data["summaries"]["outlook"],
                    report2_data["summaries"]["outlook"],
                    "Compare these two business outlooks and determine which is more optimistic:"
                )
            
            comparison_data["analysis"] = comparison_analysis
        
        return comparison_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing reports: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error comparing reports: {str(e)}")

@router.get("/companies/{company_id}/metrics", response_model=Dict[str, Any])
async def get_company_metrics(
    company_id: int,
    metric_names: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get metrics for a specific company across all reports.
    
    Args:
        company_id: ID of the company to get metrics for
        metric_names: Optional comma-separated list of metric names to filter by
        db: Database session (injected)
        
    Returns:
        Dictionary with metrics organized by metric name
        
    Raises:
        HTTPException: If company not found or database error occurs
    """
    # Parse metric names if provided
    metric_names_list = None
    if metric_names:
        metric_names_list = [name.strip() for name in metric_names.split(',')]
    
    # Get metrics from database service
    metrics_data, error = DBService.get_company_metrics(db, company_id, metric_names_list)
    
    if error:
        logger.error(f"Error retrieving metrics for company {company_id}: {error}")
        raise HTTPException(status_code=404 if "no reports found" in error.lower() else 500, 
                           detail=error)
    
    return metrics_data

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

@router.get("/reports/{report_id}/status", response_model=Dict[str, Any])
def get_report_status(
    report_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the processing status of a report.
    """
    try:
        logger.info(f"PIPELINE: Checking status for report {report_id}")
        
        # Get the report from the database
        report = DBService.get_report_by_id(db, report_id)
        if not report:
            logger.error(f"PIPELINE: Status check failed - Report with ID {report_id} not found")
            raise HTTPException(status_code=404, detail=f"Report with ID {report_id} not found")
        
        # Get the current timestamp
        current_time = datetime.now()
        
        # If still processing after 10 minutes, consider it as failed
        if report.processing_status in ['pending', 'processing'] and report.upload_date:
            time_elapsed = (current_time - report.upload_date).total_seconds() / 60
            
            if time_elapsed > 10:  # If more than 10 minutes
                logger.warning(f"PIPELINE: Report {report_id} processing timeout after {time_elapsed:.1f} minutes, marking as failed")
                report.processing_status = "failed"
                db.commit()
        
        logger.info(f"PIPELINE: Report {report_id} status check: {report.processing_status}")
        
        # Safely get the last_updated field
        last_updated = None
        try:
            if hasattr(report, 'last_updated') and report.last_updated:
                last_updated = report.last_updated.isoformat()
        except AttributeError as e:
            logger.warning(f"PIPELINE: Could not access last_updated field for report {report_id}: {str(e)}")
        
        # Return the status information
        return {
            "status": report.processing_status,
            "report_id": report_id,
            "company_name": report.company.name if report.company else None,
            "year": report.year,
            "upload_date": report.upload_date.isoformat() if report.upload_date else None,
            "last_updated": last_updated,
            "error_message": report.error_message if hasattr(report, 'error_message') and report.error_message else None
        }
    
    except HTTPException as e:
        logger.error(f"PIPELINE: HTTP exception in status check for report {report_id}: {str(e)}")
        raise
    
    except Exception as e:
        logger.error(f"PIPELINE: Error getting status for report {report_id}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Error getting report status: {str(e)}"}
        ) 