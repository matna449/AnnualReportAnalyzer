#!/usr/bin/env python3
"""
Script to generate sample data for the Annual Report Analyzer.
This script will create sample companies and reports in the database.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Add the parent directory to the path so we can import the backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.models.database import create_tables, Company, Report, Metric, Summary
from backend.models.database_session import SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Sample data
SAMPLE_COMPANIES = [
    {
        "name": "Apple Inc.",
        "ticker": "AAPL",
        "sector": "Technology",
        "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide."
    },
    {
        "name": "Microsoft Corporation",
        "ticker": "MSFT",
        "sector": "Technology",
        "description": "Microsoft Corporation develops, licenses, and supports software, services, devices, and solutions worldwide."
    },
    {
        "name": "Tesla, Inc.",
        "ticker": "TSLA",
        "sector": "Automotive",
        "description": "Tesla, Inc. designs, develops, manufactures, leases, and sells electric vehicles, and energy generation and storage systems."
    },
    {
        "name": "Amazon.com, Inc.",
        "ticker": "AMZN",
        "sector": "E-commerce",
        "description": "Amazon.com, Inc. engages in the retail sale of consumer products and subscriptions in North America and internationally."
    },
    {
        "name": "Alphabet Inc.",
        "ticker": "GOOGL",
        "sector": "Technology",
        "description": "Alphabet Inc. provides online advertising services, a search engine, the Android operating system, and various other products."
    }
]

SAMPLE_METRICS = [
    {"name": "Revenue", "category": "financial", "unit": "USD"},
    {"name": "Net Income", "category": "financial", "unit": "USD"},
    {"name": "EPS", "category": "financial", "unit": "USD"},
    {"name": "Operating Margin", "category": "financial", "unit": "%"},
    {"name": "Return on Equity", "category": "financial", "unit": "%"},
    {"name": "Debt to Equity", "category": "financial", "unit": "ratio"},
    {"name": "Current Ratio", "category": "financial", "unit": "ratio"},
    {"name": "Carbon Emissions", "category": "esg", "unit": "tons"},
    {"name": "Employee Count", "category": "operational", "unit": "count"}
]

SUMMARY_CATEGORIES = ["executive", "financial", "risk", "outlook"]

def generate_sample_data():
    """Generate sample data for the Annual Report Analyzer."""
    # Create database tables
    create_tables()
    
    # Create a database session
    db = SessionLocal()
    
    try:
        # Check if we already have data
        existing_companies = db.query(Company).count()
        if existing_companies > 0:
            logger.info(f"Database already contains {existing_companies} companies. Skipping sample data generation.")
            return
        
        # Create companies
        companies = []
        for company_data in SAMPLE_COMPANIES:
            company = Company(**company_data)
            db.add(company)
            db.flush()  # Flush to get the ID
            companies.append(company)
            logger.info(f"Created company: {company.name}")
        
        # Create reports for each company
        for company in companies:
            # Create reports for the last 3 years
            current_year = datetime.now().year
            for year_offset in range(3):
                year = current_year - year_offset
                
                # Create a report
                report = Report(
                    company_id=company.id,
                    year=str(year),
                    file_path=f"uploads/sample_{company.ticker}_{year}.pdf",
                    file_name=f"{company.name} Annual Report {year}.pdf",
                    upload_date=datetime.now() - timedelta(days=year_offset * 30),
                    processing_status="completed",
                    page_count=100 + year_offset * 10
                )
                db.add(report)
                db.flush()  # Flush to get the ID
                logger.info(f"Created report: {company.name} - {year}")
                
                # Create metrics for the report
                for metric_data in SAMPLE_METRICS:
                    # Generate a random value based on the metric
                    if metric_data["name"] == "Revenue":
                        value = f"{10000 + year_offset * 1000 + company.id * 500}"
                    elif metric_data["name"] == "Net Income":
                        value = f"{2000 + year_offset * 200 + company.id * 100}"
                    elif metric_data["name"] == "EPS":
                        value = f"{5 + year_offset * 0.5 + company.id * 0.2}"
                    elif metric_data["name"] == "Operating Margin":
                        value = f"{15 + year_offset * 1 + company.id * 0.5}"
                    elif metric_data["name"] == "Return on Equity":
                        value = f"{20 + year_offset * 2 + company.id * 1}"
                    elif metric_data["name"] == "Debt to Equity":
                        value = f"{1 + year_offset * 0.1 + company.id * 0.05}"
                    elif metric_data["name"] == "Current Ratio":
                        value = f"{1.5 + year_offset * 0.1 + company.id * 0.05}"
                    elif metric_data["name"] == "Carbon Emissions":
                        value = f"{1000 - year_offset * 100 - company.id * 50}"
                    elif metric_data["name"] == "Employee Count":
                        value = f"{10000 + year_offset * 1000 + company.id * 500}"
                    else:
                        value = "0"
                    
                    metric = Metric(
                        report_id=report.id,
                        name=metric_data["name"],
                        value=value,
                        unit=metric_data["unit"],
                        category=metric_data["category"]
                    )
                    db.add(metric)
                
                # Create summaries for the report
                for category in SUMMARY_CATEGORIES:
                    content = f"Sample {category} summary for {company.name} {year} annual report."
                    if category == "executive":
                        content = f"{company.name} reported strong financial results for fiscal year {year}, with revenue growth across most product categories and geographic segments. The company continues to invest in innovation and expand its ecosystem."
                    elif category == "financial":
                        content = f"For fiscal year {year}, {company.name} achieved revenue of ${10000 + year_offset * 1000 + company.id * 500} million, representing a growth of {5 + year_offset}% year-over-year. Net income was ${2000 + year_offset * 200 + company.id * 100} million."
                    elif category == "risk":
                        content = f"Key risk factors for {company.name} include global economic conditions, supply chain disruptions, intense competition, regulatory challenges, and rapid technological changes requiring continuous innovation."
                    elif category == "outlook":
                        content = f"{company.name} expects continued growth in its core business segments and stable performance in emerging markets. The company plans to expand its capabilities and invest in new technologies."
                    
                    summary = Summary(
                        report_id=report.id,
                        category=category,
                        content=content
                    )
                    db.add(summary)
        
        # Commit the changes
        db.commit()
        logger.info("Sample data generation completed successfully.")
    
    except Exception as e:
        db.rollback()
        logger.error(f"Error generating sample data: {str(e)}")
        raise
    
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("Starting sample data generation...")
    generate_sample_data() 