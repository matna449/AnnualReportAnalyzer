import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from datetime import datetime

from api.routes import router
from models.database import create_tables
from middleware.log_streaming import setup_log_streaming

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.getcwd(), "backend", "logs")
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Generate log file name with timestamp
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
log_file_path = os.path.join(logs_dir, f"app_{timestamp}.log")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file_path)
    ]
)

logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {log_file_path}")

# Load environment variables
load_dotenv()

# Create uploads directory if it doesn't exist
uploads_dir = os.path.join(os.getcwd(), "uploads")
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir)
    logger.info(f"Created uploads directory at {uploads_dir}")

# Initialize database
create_tables()
logger.info("Database tables created or verified")

# Create FastAPI app
app = FastAPI(
    title="Annual Report Analyzer API",
    description="API for analyzing annual reports using AI",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add log streaming middleware
setup_log_streaming(app)
logger.info("Log streaming middleware initialized")

# Include API routes
app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    """Root endpoint to verify API is running."""
    return {
        "message": "Annual Report Analyzer API is running",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True) 