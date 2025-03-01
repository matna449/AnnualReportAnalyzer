#!/usr/bin/env python3
"""
Annual Report Processor Script

This script processes an annual report PDF file, extracts financial data,
calculates KPIs, and stores the results in the database.

Usage:
    python process_annual_report.py <pdf_path> <company_name> <year> [--ticker TICKER] [--sector SECTOR]

Example:
    python process_annual_report.py ./uploads/apple_annual_report_2023.pdf "Apple Inc." 2023 --ticker AAPL --sector "Technology"
"""

import os
import sys
import argparse
import logging
from sqlalchemy.orm import Session
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Add the parent directory to sys.path to ensure imports work correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from models.database_session import get_db
from services.pdf_processor import PDFProcessor
from services.db_service import DBService
from models.schemas import CompanyCreate, ReportCreate

def main():
    """Main function to process an annual report."""
    parser = argparse.ArgumentParser(description="Process an annual report PDF file")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("company_name", help="Name of the company")
    parser.add_argument("year", help="Year of the report")
    parser.add_argument("--ticker", help="Company ticker symbol")
    parser.add_argument("--sector", help="Company sector")
    
    args = parser.parse_args()
    
    # Print current working directory for debugging
    logger.info(f"Current working directory: {os.getcwd()}")
    
    # Validate PDF path
    if not os.path.exists(args.pdf_path):
        logger.error(f"PDF file not found: {args.pdf_path}")
        sys.exit(1)
    
    if not args.pdf_path.lower().endswith('.pdf'):
        logger.error(f"File is not a PDF: {args.pdf_path}")
        sys.exit(1)
    
    # Get database session
    try:
        db_generator = get_db()
        db = next(db_generator)
        logger.info("Successfully connected to database")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    try:
        # Initialize services
        db_service = DBService()
        pdf_processor = PDFProcessor()
        
        # Check if company exists, create if not
        company = db_service.get_company_by_name(db, args.company_name)
        if not company:
            logger.info(f"Creating new company: {args.company_name}")
            company_create = CompanyCreate(
                name=args.company_name,
                ticker=args.ticker or "",
                sector=args.sector or ""
            )
            company = db_service.create_company(db, company_create)
        
        # Create report entry
        file_name = os.path.basename(args.pdf_path)
        report_create = ReportCreate(
            company_id=company.id,
            year=args.year,
            file_path=args.pdf_path,
            file_name=file_name,
            processing_status="processing"
        )
        report = db_service.create_report(db, report_create)
        
        logger.info(f"Created report entry with ID {report.id}")
        
        # Process the report
        result = pdf_processor.process_annual_report(args.pdf_path, report.id, db)
        
        if "error" in result:
            logger.error(f"Error processing report: {result['error']}")
            sys.exit(1)
        
        logger.info(f"Successfully processed report: {file_name}")
        logger.info(f"Identified {len(result['financial_pages'])} financial pages")
        logger.info(f"Calculated {len(result['kpis'])} KPIs")
        logger.info(f"Generated {len(result['insights'])} insights")
        
        # Print summary of KPIs
        print("\nFinancial KPIs:")
        for key, value in result['kpis'].items():
            if key != "extracted_values" and isinstance(value, (int, float)):
                print(f"  {key.replace('_', ' ').title()}: {value:.2f}")
        
        # Print summary of insights
        print("\nAI-Generated Insights:")
        for key, value in result['insights'].items():
            if isinstance(value, str):
                print(f"\n{key.replace('_', ' ').title()}:")
                print(f"  {value}")
        
        print(f"\nResults stored in database for report ID: {report.id}")
        
    except Exception as e:
        logger.error(f"Error processing annual report: {e}")
        logger.error(traceback.format_exc())
        # Update report status to failed if it was created
        if 'report' in locals():
            try:
                db_service.update_report_status(db, report.id, "failed")
            except Exception as update_error:
                logger.error(f"Failed to update report status: {update_error}")
        sys.exit(1)
    finally:
        try:
            db.close()
            logger.info("Database connection closed")
        except Exception as close_error:
            logger.error(f"Error closing database connection: {close_error}")

if __name__ == "__main__":
    main() 