# Annual Report PDF Processor

This module provides selective processing of annual reports in PDF format, focusing on extracting and analyzing financial data.

## Features

- **Selective Processing**: Identifies and extracts only financial sections from large PDFs (400-500 pages)
- **Smart Section Detection**: Uses table of contents, section headings, and regex patterns to locate financial data
- **Table Extraction**: Extracts tables from financial sections using tabula-py and pdfplumber
- **Financial KPI Calculation**: Automatically calculates important financial metrics
- **AI-Powered Insights**: Generates summaries and insights using Hugging Face models
- **Database Integration**: Stores all extracted data and analysis in the database

## Key Financial KPIs Calculated

- **Profitability Metrics**: Return on Equity (ROE), Return on Assets (ROA), Net Profit Margin
- **Liquidity Metrics**: Current Ratio, Quick Ratio, Working Capital
- **Efficiency Metrics**: Asset Turnover, Inventory Turnover
- **Solvency Metrics**: Debt-to-Equity Ratio, Interest Coverage Ratio
- **Cash Flow Metrics**: Cash Ratio

## Usage

### Command Line

Process a PDF file directly from the command line:

```bash
python process_annual_report.py ./uploads/annual_report.pdf "Company Name" 2023 --ticker TICK --sector "Industry Sector"
```

### API Endpoints

- **POST /api/pdf/process**: Upload and process a PDF file
- **GET /api/pdf/status/{report_id}**: Check processing status
- **GET /api/pdf/metrics/{report_id}**: Get calculated metrics
- **GET /api/pdf/insights/{report_id}**: Get AI-generated insights

## Implementation Details

### Processing Pipeline

1. **First Pass**: Identify financial sections by scanning table of contents and looking for financial keywords
2. **Selective Extraction**: Extract text and tables only from identified financial pages
3. **KPI Calculation**: Calculate financial KPIs from extracted data
4. **AI Analysis**: Generate insights using Hugging Face models
5. **Database Storage**: Store results in the database

### Dependencies

- **PyPDF2**: For basic PDF text extraction
- **pdfplumber**: For PDF text extraction with layout information
- **tabula-py**: For table extraction from PDFs
- **Hugging Face Transformers**: For AI-powered analysis and insights

## Configuration

The PDF processor can be configured through environment variables:

- **HUGGINGFACE_API_KEY**: API key for Hugging Face
- **MODEL_NAME**: Name of the Hugging Face model to use (default: google/flan-t5-large)
- **CHUNK_SIZE**: Size of text chunks for processing (default: 4000)
- **OVERLAP_SIZE**: Overlap between text chunks (default: 200)

## Example

```python
from services.pdf_processor import PDFProcessor
from models.database_session import get_db_session

# Initialize processor
processor = PDFProcessor()

# Get database session
db = next(get_db_session())

# Process a report
result = processor.process_annual_report("path/to/annual_report.pdf", report_id, db)

# Print results
print(f"Identified {len(result['financial_pages'])} financial pages")
print(f"Calculated {len(result['kpis'])} KPIs")
print(f"Generated {len(result['insights'])} insights")
``` 