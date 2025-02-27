# Annual Report Analyzer

An AI-powered application for analyzing company annual reports. Extract key financial metrics, risk factors, and business outlooks from PDF reports using Hugging Face Transformers and Claude API.

## Features

- PDF upload and processing
- AI-powered text analysis
- Financial metrics extraction
- Risk factor identification
- Sentiment analysis
- Report comparison
- Historical data tracking

## Tech Stack

### Backend
- Python
- FastAPI
- SQLAlchemy
- PyPDF2
- pdfplumber
- Hugging Face Transformers
- Anthropic Claude API

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
- Claude API key (optional, get one at https://console.anthropic.com/settings/keys)

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
   python -m backend.main
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

## API Documentation

The API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT
