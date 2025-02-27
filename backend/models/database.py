from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./annual_reports.db")
engine = create_engine(DATABASE_URL)
Base = declarative_base()


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    ticker = Column(String(10), nullable=True)
    sector = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    reports = relationship("Report", back_populates="company", cascade="all, delete-orphan")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    year = Column(String(4), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_name = Column(String(255), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    processing_status = Column(String(20), default="pending")  # pending, processing, completed, failed
    page_count = Column(Integer, nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="reports")
    metrics = relationship("Metric", back_populates="report", cascade="all, delete-orphan")
    summaries = relationship("Summary", back_populates="report", cascade="all, delete-orphan")


class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    name = Column(String(100), nullable=False)
    value = Column(String(100), nullable=False)
    unit = Column(String(20), nullable=True)
    category = Column(String(50), nullable=True)  # financial, esg, operational, etc.
    
    # Relationships
    report = relationship("Report", back_populates="metrics")


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    category = Column(String(50), nullable=False)  # executive, financial, risk, outlook
    content = Column(Text, nullable=False)
    
    # Relationships
    report = relationship("Report", back_populates="summaries")


# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine) 