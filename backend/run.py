#!/usr/bin/env python3
"""
Entry point script for the Annual Report Analyzer backend.
This script starts the FastAPI server.
"""

import os
import logging
import uvicorn
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

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