from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
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