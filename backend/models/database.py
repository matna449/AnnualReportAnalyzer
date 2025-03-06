from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, DateTime, create_engine, JSON
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
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    error_message = Column(Text, nullable=True)  # Store error message when processing fails
    
    # Relationships
    company = relationship("Company", back_populates="reports")
    metrics = relationship("Metric", back_populates="report", cascade="all, delete-orphan")
    summaries = relationship("Summary", back_populates="report", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="report", cascade="all, delete-orphan")
    sentiment_analyses = relationship("SentimentAnalysis", back_populates="report", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="report", cascade="all, delete-orphan")


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


class Entity(Base):
    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    entity_type = Column(String(50), nullable=False)  # MONEY, ORG, DATE, etc.
    text = Column(String(255), nullable=False)
    score = Column(Float, nullable=True)
    section = Column(String(100), nullable=True)  # Which section of the report this entity was found in
    
    # Relationships
    report = relationship("Report", back_populates="entities")


class SentimentAnalysis(Base):
    __tablename__ = "sentiment_analyses"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    section = Column(String(100), nullable=True)  # Which section of the report this sentiment applies to
    sentiment = Column(String(20), nullable=False)  # positive, negative, neutral
    score = Column(Float, nullable=False)
    distribution = Column(JSON, nullable=True)  # JSON object with sentiment distribution
    insight = Column(Text, nullable=True)
    
    # Relationships
    report = relationship("Report", back_populates="sentiment_analyses")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    overall_score = Column(Float, nullable=False)
    categories = Column(JSON, nullable=True)  # JSON object with risk categories and scores
    primary_factors = Column(JSON, nullable=True)  # JSON object with primary risk factors
    insight = Column(Text, nullable=True)
    
    # Relationships
    report = relationship("Report", back_populates="risk_assessments")


# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine) 