from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime


# Company schemas
class CompanyBase(BaseModel):
    name: str
    ticker: Optional[str] = None
    sector: Optional[str] = None
    description: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(CompanyBase):
    name: Optional[str] = None


class CompanyInDB(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Company(CompanyInDB):
    pass


# Report schemas
class ReportBase(BaseModel):
    company_id: int
    year: str


class ReportCreate(ReportBase):
    file_name: str
    file_path: str
    processing_status: str = "pending"
    page_count: Optional[int] = None


class ReportUpdate(BaseModel):
    company_id: Optional[int] = None
    year: Optional[str] = None
    processing_status: Optional[str] = None
    page_count: Optional[int] = None


class ReportInDB(ReportBase):
    id: int
    file_path: str
    file_name: str
    upload_date: datetime
    processing_status: str
    page_count: Optional[int] = None

    class Config:
        from_attributes = True


class Report(ReportInDB):
    company: Company


# Metric schemas
class MetricBase(BaseModel):
    name: str
    value: str
    unit: Optional[str] = None
    category: Optional[str] = None


class MetricCreate(MetricBase):
    report_id: int


class MetricInDB(MetricBase):
    id: int
    report_id: int

    class Config:
        from_attributes = True


class Metric(MetricInDB):
    pass


# Summary schemas
class SummaryBase(BaseModel):
    category: str
    content: str


class SummaryCreate(SummaryBase):
    report_id: int


class SummaryInDB(SummaryBase):
    id: int
    report_id: int

    class Config:
        from_attributes = True


class Summary(SummaryInDB):
    pass


# Entity schemas
class EntityBase(BaseModel):
    entity_type: str
    text: str
    score: Optional[float] = None
    section: Optional[str] = None


class EntityCreate(EntityBase):
    report_id: int


class EntityInDB(EntityBase):
    id: int
    report_id: int

    class Config:
        from_attributes = True


class Entity(EntityInDB):
    pass


# Sentiment Analysis schemas
class SentimentAnalysisBase(BaseModel):
    section: Optional[str] = None
    sentiment: str
    score: float
    distribution: Optional[Dict[str, float]] = None
    insight: Optional[str] = None


class SentimentAnalysisCreate(SentimentAnalysisBase):
    report_id: int


class SentimentAnalysisInDB(SentimentAnalysisBase):
    id: int
    report_id: int

    class Config:
        from_attributes = True


class SentimentAnalysis(SentimentAnalysisInDB):
    pass


# Risk Assessment schemas
class RiskAssessmentBase(BaseModel):
    overall_score: float
    categories: Optional[Dict[str, float]] = None
    primary_factors: Optional[List[Dict[str, Union[str, float]]]] = None
    insight: Optional[str] = None


class RiskAssessmentCreate(RiskAssessmentBase):
    report_id: int


class RiskAssessmentInDB(RiskAssessmentBase):
    id: int
    report_id: int

    class Config:
        from_attributes = True


class RiskAssessment(RiskAssessmentInDB):
    pass


# Upload schemas
class UploadResponse(BaseModel):
    company_id: int
    report_id: int
    file_name: str
    status: str
    message: str


# Analysis schemas
class AnalysisResult(BaseModel):
    report_id: int
    status: str
    metrics: List[Metric] = []
    summaries: Dict[str, str] = {}
    entities: Optional[Dict[str, List[Entity]]] = None
    sentiment: Optional[SentimentAnalysis] = None
    risk: Optional[RiskAssessment] = None
    insights: Optional[Dict[str, str]] = None


# Search schemas
class SearchParams(BaseModel):
    company_name: Optional[str] = None
    ticker: Optional[str] = None
    year: Optional[str] = None
    sector: Optional[str] = None


class SearchResult(BaseModel):
    companies: List[Company] = []
    reports: List[Report] = []


# Comparison schemas
class ComparisonRequest(BaseModel):
    report_ids: List[int]
    metrics: Optional[List[str]] = None


class ComparisonResult(BaseModel):
    reports: List[Report]
    metrics: Dict[str, Dict[int, Any]] 