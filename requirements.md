# Annual Report Analyzer - Requirements Specification

## 1. Project Overview

### 1.1 Purpose
To develop a web application that uses AI to extract, analyze, and present key information from company annual reports, allowing users to efficiently compare financial metrics, ESG performance, and business outlooks across companies and time periods.

### 1.2 Scope
The application will:
- Accept PDF uploads of annual reports
- Extract structured data using AI
- Store analysis results in a database
- Present information through an intuitive dashboard
- Enable comparisons and searches
- Focus on core financial metrics and business outlook

### 1.3 Project Constraints
- Development timeframe: One weekend (3 days)
- Use open-source or free-tier AI APIs
- Focus on functionality over appearance initially

## 2. Functional Requirements

### 2.1 Document Processing
- **REQ-1.1**: Accept PDF uploads up to 50MB
- **REQ-1.2**: Extract text content from PDFs while preserving structure
- **REQ-1.3**: Identify and parse tables and charts
- **REQ-1.4**: Track original page numbers for reference

### 2.2 AI Analysis
- **REQ-2.1**: Extract key financial metrics (revenue, profit, growth, etc.)
- **REQ-2.2**: Identify business segments and their performance
- **REQ-2.3**: Extract risk factors and management discussion points
- **REQ-2.4**: Generate summary of company outlook and strategy
- **REQ-2.5**: Detect sentiment in management discussion sections

### 2.3 Data Management
- **REQ-3.1**: Store structured data for each report (company, year, metrics)
- **REQ-3.2**: Enable searching across all processed reports
- **REQ-3.3**: Track upload history and processing status
- **REQ-3.4**: Export analyzed data in CSV/Excel format

### 2.4 User Interface
- **REQ-4.1**: Provide drag-and-drop upload functionality
- **REQ-4.2**: Display dashboard with key metrics for each report
- **REQ-4.3**: Enable side-by-side comparison of two or more companies
- **REQ-4.4**: Create visualizations for financial trends
- **REQ-4.5**: Implement search and filter capabilities

## 3. Technical Requirements

### 3.1 Backend Components
- **TECH-1.1**: Python-based API (FastAPI or Flask)
- **TECH-1.2**: PDF processing module (PyPDF2, pdfplumber, or similar)
- **TECH-1.3**: AI integration module (Hugging Face or Claude)
- **TECH-1.4**: Database (SQLite for prototype)
- **TECH-1.5**: User authentication (optional - simple token-based)

### 3.2 Frontend Components
- **TECH-2.1**: React-based SPA
- **TECH-2.2**: Chart visualization library (Recharts)
- **TECH-2.3**: Component library (optional - Material UI or similar)
- **TECH-2.4**: Responsive design for desktop (mobile optional)

### 3.3 AI Implementation
- **TECH-3.1**: Document chunking strategy for API limits
- **TECH-3.2**: Prompt engineering for consistent extraction
- **TECH-3.3**: Error handling for AI processing failures
- **TECH-3.4**: Caching strategy to avoid redundant processing

## 4. Implementation Plan

### 4.1 Day 1 (Friday) - Basic Infrastructure
1. Set up project repository structure
2. Create API boilerplate with endpoints
3. Implement PDF upload and text extraction
4. Set up database models
5. Create frontend project with routing

### 4.2 Day 2 (Saturday) - Core Functionality
6. Implement AI analysis for financial metrics
7. Develop dashboard UI components
8. Create data storage and retrieval functions
9. Add single-report view functionality
10. Implement basic search functionality

### 4.3 Day 3 (Sunday) - Refinement
11. Add comparison functionality
12. Implement data visualizations
13. Add export capabilities
14. Polish UI and fix bugs
15. Create documentation and demo

## 5. Technical Architecture

### 5.1 System Components
```
┌───────────────┐     ┌───────────────────────┐     ┌───────────────┐
│  React        │     │  FastAPI Backend      │     │  Database     │
│  Frontend     │─────▶  - PDF Processing     │─────▶  (SQLite)     │
│               │     │  - AI Integration     │     │               │
└───────────────┘     │  - Data Management    │     └───────────────┘
                      └───────────────────────┘
                                │
                                ▼
                      ┌───────────────────────┐
                      │  AI Services          │
                      │  - Hugging Face       │
                      │  - Claude API         │
                      └───────────────────────┘
```

### 5.2 Database Schema
```
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ Companies     │       │ Reports       │       │ Metrics       │
│ - id          │       │ - id          │       │ - id          │
│ - name        │═══════│ - company_id  │═══════│ - report_id   │
│ - ticker      │       │ - year        │       │ - name        │
│ - sector      │       │ - file_path   │       │ - value       │
│ - description │       │ - upload_date │       │ - unit        │
└───────────────┘       └───────────────┘       └───────────────┘
                                                        │
                                                        ▼
                                               ┌───────────────┐
                                               │ MetricTypes   │
                                               │ - id          │
                                               │ - name        │
                                               │ - category    │
                                               └───────────────┘
```

## 6. API Endpoints

### 6.1 Document Management
- `POST /api/reports/upload` - Upload new annual report
- `GET /api/reports` - List all processed reports
- `GET /api/reports/{id}` - Get report details and analysis
- `DELETE /api/reports/{id}` - Remove report from system

### 6.2 Analysis
- `GET /api/companies/{id}/metrics` - Get all metrics for a company
- `GET /api/reports/{id}/summary` - Get AI-generated summary
- `GET /api/compare?companies=id1,id2&year=YYYY` - Compare companies

### 6.3 Data Export
- `GET /api/export/company/{id}` - Export company data
- `GET /api/export/comparison?ids=id1,id2` - Export comparison data

## 7. Frontend Pages

### 7.1 Main Views
- Upload Page - For submitting new reports
- Dashboard - Overview of all analyzed companies
- Company Detail - In-depth view of single company
- Comparison View - Side-by-side comparison
- Search Results - List view of filtered reports

### 7.2 Components
- FileUploader - Handles PDF uploads
- MetricsTable - Displays financial data
- TimelineChart - Shows metrics over time
- ComparisonGrid - Side-by-side company comparison
- SentimentIndicator - Visualizes positive/negative outlook

## 8. AI Implementation Details

### 8.1 Key Extraction Targets
- Financial metrics (revenue, net income, EPS, etc.)
- Growth rates year-over-year
- Segment performance
- Risk factors
- ESG commitments and metrics
- Management outlook statements
- Capital allocation strategy

### 8.2 Prompt Templates
- Financial extraction prompt
- Risk analysis prompt
- Sentiment analysis prompt
- Executive summary generation prompt

## 9. Testing Strategy

### 9.1 Key Test Cases
- Upload of different PDF formats and sizes
- Extraction accuracy for various report layouts
- Database retrieval performance
- UI responsiveness with large datasets

### 9.2 Success Criteria
- Successful extraction of at least 80% of key metrics
- Processing time under 5 minutes per report
- Correct association of metrics to companies and years
- Functional comparison between any two processed reports

## 10. Future Enhancements (Post-Weekend)

### 10.1 Features for Later
- User accounts and authentication
- Improved table extraction
- Chart/graph recognition and digitization
- Industry benchmarking
- Advanced search with natural language
- Mobile optimization
- Export to presentation formats