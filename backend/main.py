import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.routes import router
from models.database import create_tables
from middleware.log_streaming import setup_log_streaming
from utils.logging_config import setup_logging

# Set up logging
logger, _, _ = setup_logging("main")

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