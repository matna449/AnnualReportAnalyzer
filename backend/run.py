#!/usr/bin/env python3
"""
Entry point script for the Annual Report Analyzer backend.
This script starts the FastAPI server.
"""

import os
import logging
import uvicorn
from dotenv import load_dotenv
from datetime import datetime

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

if __name__ == "__main__":
    # Get configuration from environment variables or use defaults
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    reload = os.getenv("RELOAD", "True").lower() in ("true", "1", "t")
    
    logger.info(f"Starting server on {host}:{port} (reload={reload})")
    
    # Start the server
    # Note: We use "main:app" instead of "backend.main:app" to avoid the module import issue
    uvicorn.run("main:app", host=host, port=port, reload=reload) 