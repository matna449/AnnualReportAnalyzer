#!/usr/bin/env python3
"""
Script to generate sample data for the Annual Report Analyzer.
This script creates sample companies, reports, metrics, and summaries for testing.
"""

import os
import sys
import random
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.database import create_tables, Company, Report, Metric, Summary
from models.database_session import SessionLocal
from models.schemas import CompanyCreate, ReportCreate, MetricCreate, SummaryCreate
from services.db_service import DBService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Sample data
SAMPLE_COMPANIES = [
    {"name": "Apple Inc.", "ticker": "AAPL", "sector": "Technology", "description": "Manufacturer of consumer electronics and software."},
    {"name": "Microsoft Corporation", "ticker": "MSFT", "sector": "Technology", "description": "Developer of software and provider of cloud services."},
    {"name": "Amazon.com, Inc.", "ticker": "AMZN", "sector": "E-commerce", "description": "Online retailer and provider of cloud computing services."},
    {"name": "Alphabet Inc.", "ticker": "GOOGL", "sector": "Technology", "description": "Internet services and products company."},
    {"name": "Tesla, Inc.", "ticker": "TSLA", "sector": "Automotive", "description": "Electric vehicle and clean energy company."},
    {"name": "Meta Platforms, Inc.", "ticker": "META", "sector": "Technology", "description": "Social media and technology company."},
    {"name": "Johnson & Johnson", "ticker": "JNJ", "sector": "Healthcare", "description": "Pharmaceutical and consumer goods company."},
    {"name": "JPMorgan Chase & Co.", "ticker": "JPM", "sector": "Finance", "description": "Financial services and banking company."},
    {"name": "Walmart Inc.", "ticker": "WMT", "sector": "Retail", "description": "Multinational retail corporation."},
    {"name": "Exxon Mobil Corporation", "ticker": "XOM", "sector": "Energy", "description": "Oil and gas corporation."}
]

SAMPLE_YEARS = ["2019", "2020", "2021", "2022", "2023"]

SAMPLE_METRICS = [
    {"name": "revenue", "category": "financial", "unit": "USD"},
    {"name": "netIncome", "category": "financial", "unit": "USD"},
    {"name": "operatingIncome", "category": "financial", "unit": "USD"},
    {"name": "grossMargin", "category": "financial", "unit": "percentage"},
    {"name": "operatingMargin", "category": "financial", "unit": "percentage"},
    {"name": "netMargin", "category": "financial", "unit": "percentage"},
    {"name": "eps", "category": "financial", "unit": "USD"},
    {"name": "totalAssets", "category": "financial", "unit": "USD"},
    {"name": "totalLiabilities", "category": "financial", "unit": "USD"},
    {"name": "cashFlow", "category": "financial", "unit": "USD"},
    {"name": "rnd", "category": "financial", "unit": "USD"}
]

SAMPLE_SUMMARY_CATEGORIES = ["executive", "financial", "risk", "outlook"]

def generate_sample_data():
    """Generate sample data for testing."""
    logger.info("Generating sample data...")
    
    # Create database tables if they don't exist
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
            company_create = CompanyCreate(**company_data)
            company = DBService.create_company(db, company_create)
            companies.append(company)
            logger.info(f"Created company: {company.name}")
        
        # Create reports, metrics, and summaries for each company
        for company in companies:
            for year in SAMPLE_YEARS:
                # Create a report
                report_create = ReportCreate(
                    company_id=company.id,
                    year=year,
                    file_name=f"{company.ticker}_{year}_annual_report.pdf",
                    file_path=f"uploads/{company.ticker}_{year}_annual_report.pdf",
                    processing_status="completed",
                    page_count=random.randint(50, 200)
                )
                report = DBService.create_report(db, report_create)
                logger.info(f"Created report: {company.name} ({year})")
                
                # Create metrics for the report
                for metric_data in SAMPLE_METRICS:
                    # Generate a realistic value based on the metric
                    if metric_data["unit"] == "percentage":
                        value = str(round(random.uniform(1, 40), 2))
                    elif metric_data["name"] == "eps":
                        value = str(round(random.uniform(0.5, 20), 2))
                    elif metric_data["name"] in ["revenue", "totalAssets"]:
                        value = str(round(random.uniform(10000000000, 500000000000), 2))
                    elif metric_data["name"] in ["netIncome", "operatingIncome"]:
                        value = str(round(random.uniform(1000000000, 100000000000), 2))
                    else:
                        value = str(round(random.uniform(1000000, 10000000000), 2))
                    
                    metric_create = MetricCreate(
                        report_id=report.id,
                        name=metric_data["name"],
                        value=value,
                        unit=metric_data["unit"],
                        category=metric_data["category"]
                    )
                    DBService.create_metric(db, metric_create)
                
                # Create summaries for the report
                for category in SAMPLE_SUMMARY_CATEGORIES:
                    content = ""
                    if category == "executive":
                        content = f"{company.name} had a {random.choice(['strong', 'solid', 'challenging', 'transformative'])} year in {year}, with {random.choice(['growth', 'expansion', 'consolidation'])} in key markets. The company {random.choice(['exceeded', 'met', 'approached'])} its financial targets and continued to invest in innovation."
                    elif category == "financial":
                        content = f"Financial performance for {year} showed {random.choice(['strong', 'moderate', 'mixed'])} results. Revenue {random.choice(['increased', 'grew', 'expanded'])} by {random.randint(5, 25)}% year-over-year, while operating margins {random.choice(['improved', 'remained stable', 'decreased slightly'])}."
                    elif category == "risk":
                        content = f"Key risks identified include {random.choice(['market volatility', 'competitive pressures', 'regulatory changes'])}, {random.choice(['supply chain disruptions', 'cybersecurity threats', 'talent acquisition challenges'])}, and {random.choice(['geopolitical uncertainties', 'environmental concerns', 'technological disruption'])}."
                    elif category == "outlook":
                        content = f"Looking ahead to {int(year) + 1}, {company.name} expects to {random.choice(['continue its growth trajectory', 'focus on operational efficiency', 'expand into new markets'])}, while {random.choice(['investing in R&D', 'strengthening its market position', 'enhancing shareholder value'])}."
                    
                    summary_create = SummaryCreate(
                        report_id=report.id,
                        category=category,
                        content=content
                    )
                    DBService.create_summary(db, summary_create)
        
        logger.info("Sample data generation completed successfully.")
    
    except Exception as e:
        logger.error(f"Error generating sample data: {e}")
        db.rollback()
    
    finally:
        db.close()

if __name__ == "__main__":
    generate_sample_data() 