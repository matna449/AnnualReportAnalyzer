# Annual Report Analyzer

An AI-powered application for analyzing company annual reports. Extract key financial metrics, risk factors, and business outlooks from PDF reports using Hugging Face Transformers.

## Features

- PDF upload and processing
- AI-powered text analysis
- Financial metrics extraction
- Risk factor identification
- Sentiment analysis
- Report comparison
- Historical data tracking
- Interactive dashboard

> **Note:** The Enhanced AI Analysis feature has been removed from the application due to stability issues. This feature previously provided additional entity extraction, sentiment analysis, and risk assessment using Hugging Face models.

## Tech Stack

### Backend
- Python
- FastAPI
- SQLAlchemy
- PyPDF2
- pdfplumber
- Hugging Face Transformers

### Frontend
- React
- Next.js
- Material UI
- Recharts

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- Hugging Face API key (get one at https://huggingface.co/settings/tokens)

### Setup and Running

#### Quick Start

1. Clone the repository
2. Run the backend:
   ```bash
   ./run_backend.sh
   ```
3. In a separate terminal, run the frontend:
   ```bash
   ./run_frontend.sh
   ```

The backend will be available at http://localhost:8000 and the frontend at http://localhost:3000.

#### Manual Setup

##### Backend

1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install backend dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

3. Set up your API keys:
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env with your API keys
   # Or run: python backend/setup_api_keys.py
   ```

4. Start the backend server:
   ```bash
   cd backend
   python run.py
   ```

##### Frontend

1. Install frontend dependencies:
   ```bash
   npm install
   ```

2. Start the frontend development server:
   ```bash
   npm run dev
   ```

## Usage

1. Open http://localhost:3000 in your browser
2. Upload a company annual report (PDF format)
3. View the analysis results
4. Explore the dashboard for insights
5. Compare reports and track metrics over time

## Troubleshooting

### Backend Import Issues

If you encounter import errors when starting the backend, make sure you're running the server from the `backend` directory:

```bash
cd backend
python run.py
```

This ensures that the Python modules can be imported correctly without needing to use the `backend.` prefix.

### Sample Data

To generate sample data for testing:

```bash
cd backend
python utils/generate_sample_data.py
```

This will create sample companies, reports, metrics, and summaries in the database.

## API Documentation

The API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
├── backend/                  # Python FastAPI backend
│   ├── api/                  # API routes
│   ├── models/               # Database models and schemas
│   ├── services/             # Business logic services
│   ├── tests/                # Unit tests
│   ├── uploads/              # Uploaded PDF files
│   ├── utils/                # Utility functions
│   ├── .env.example          # Environment variables template
│   ├── main.py               # FastAPI application
│   ├── run.py                # Entry point script
│   └── requirements.txt      # Python dependencies
│
├── src/                      # React frontend
│   ├── app/                  # Next.js pages
│   ├── components/           # React components
│   └── styles/               # CSS styles
│
├── run_backend.sh            # Script to run the backend
├── run_frontend.sh           # Script to run the frontend
└── run_tests.sh              # Script to run tests
```

## License

MIT

## Feature Flags

The Annual Report Analyzer uses a feature flag system to control the visibility of certain features, particularly debugging tools. The main flags are:

- `SHOW_DEVELOPER_TOOLS`: Shows developer-oriented components and tools
- `SHOW_PROCESSING_LOGS`: Shows detailed processing logs

You can enable these features by:

1. In development: Toggle "Admin Mode" in the navigation bar
2. In production: Set environment variables:
   - `NEXT_PUBLIC_SHOW_DEVELOPER_TOOLS=true`
   - `NEXT_PUBLIC_SHOW_PROCESSING_LOGS=true`

### Development Admin Mode

When running in development mode, you can toggle "Admin Mode" in the navigation bar to show debugging components like the LogViewer. This is a convenient way to test the application with and without these components visible.
