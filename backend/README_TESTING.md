# Annual Report Analyzer - Testing Guide

This document provides instructions on how to test the Annual Report Analyzer backend.

## Prerequisites

- Python 3.8 or higher
- Required Python packages: `requests`, `reportlab`
- Backend server running on `http://localhost:8000`

## Test Scripts

The following test scripts are available:

### 1. Automated Test with Generated PDF

This script creates a test PDF file with sample financial data, uploads it to the backend, and monitors the analysis process.

```bash
python backend/run_test.py
```

This script:
1. Creates a PDF file with reportlab containing sample financial data
2. Uploads the PDF to the backend
3. Monitors the analysis process
4. Verifies that the analysis completes successfully
5. Checks if metrics and summaries were generated

### 2. Test with Real PDF

This script allows you to test the analysis pipeline with a real PDF file.

```bash
python backend/test_with_real_pdf.py <pdf_path> <company_name> <year> [--ticker <ticker>] [--sector <sector>]
```

Arguments:
- `pdf_path`: Path to the PDF file
- `company_name`: Name of the company
- `year`: Year of the report
- `--ticker`: Company ticker symbol (optional)
- `--sector`: Company sector (optional)

Example:
```bash
python backend/test_with_real_pdf.py /path/to/annual_report.pdf "Apple Inc." 2023 --ticker AAPL --sector "Technology"
```

This script:
1. Uploads the specified PDF file to the backend
2. Monitors the analysis process
3. Verifies that the analysis completes successfully
4. Displays extracted metrics and summaries

## Monitoring Logs

You can monitor the backend logs during testing to see what's happening in the pipeline:

```bash
tail -f backend/logs/app.log
```

## Troubleshooting

If the tests fail, check the following:

1. Make sure the backend server is running on `http://localhost:8000`
2. Check the backend logs for error messages
3. Verify that the PDF file is valid and contains sufficient text
4. Ensure that the database is properly set up and accessible
5. Check if the HuggingFace API key is valid (if using HuggingFace models)

## Adding New Tests

To add new tests:

1. Create a new Python file in the `backend` directory
2. Import the necessary modules
3. Define a function that performs the test
4. Add command-line argument parsing if needed
5. Run the test and return an appropriate exit code

## Continuous Integration

These test scripts can be integrated into a CI/CD pipeline to automatically test the backend after changes are made.

Example GitHub Actions workflow:

```yaml
name: Backend Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install reportlab
    - name: Start backend server
      run: |
        bash run_backend.sh &
        sleep 10  # Wait for server to start
    - name: Run tests
      run: |
        python backend/run_test.py
``` 