# Annual Report Analyzer Backend

This is the backend API for the Annual Report Analyzer application, which provides AI-powered analysis of company annual reports.

## Features

- PDF processing and text extraction
- AI-powered analysis using Hugging Face Transformers and Claude API
- Financial metrics extraction
- Risk factor identification
- Sentiment analysis
- Report comparison
- Historical data tracking

## Tech Stack

- **Framework**: FastAPI
- **Database**: SQLAlchemy with SQLite (development)
- **PDF Processing**: PyPDF2, pdfplumber
- **AI Integration**: Hugging Face Transformers, Anthropic Claude API

## Setup

### Prerequisites

- Python 3.9+
- Virtual environment (recommended)

### Installation

1. Clone the repository
2. Navigate to the backend directory
3. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

6. Edit the `.env` file with your API keys and configuration

### Running the Server

Start the development server:

```bash
python -m backend.main
```

The API will be available at http://localhost:8000

API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Companies

- `GET /api/companies/` - List all companies
- `POST /api/companies/` - Create a new company
- `GET /api/companies/{company_id}` - Get company details
- `PUT /api/companies/{company_id}` - Update company details

### Reports

- `POST /api/reports/upload/` - Upload and analyze a new report
- `GET /api/reports/` - List all reports
- `GET /api/reports/{report_id}` - Get report analysis
- `GET /api/companies/{company_id}/reports` - Get reports for a company
- `POST /api/reports/search/` - Search for reports
- `POST /api/reports/compare/` - Compare multiple reports
- `GET /api/companies/{company_id}/metrics` - Get historical metrics for a company

### Dashboard

- `GET /api/dashboard/summary` - Get dashboard summary statistics
- `GET /api/dashboard/recent-reports` - Get recently uploaded reports
- `GET /api/dashboard/sectors` - Get sector distribution

## Development

### Project Structure

```
backend/
├── api/
│   └── routes.py          # API endpoints
├── models/
│   ├── database.py        # SQLAlchemy models
│   ├── database_session.py # Database session management
│   └── schemas.py         # Pydantic models
├── services/
│   ├── ai_service.py      # AI analysis service
│   ├── analysis_service.py # Coordination service
│   ├── db_service.py      # Database operations
│   └── pdf_service.py     # PDF processing
├── .env.example           # Example environment variables
├── main.py                # Application entry point
└── requirements.txt       # Dependencies
```

### Testing

Run tests with pytest:

```bash
pytest
```

## License

[MIT License](LICENSE) 