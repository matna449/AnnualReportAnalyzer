from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import sys
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get absolute path to the project root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
logger.info(f"Root directory: {ROOT_DIR}")
logger.info(f"Current working directory: {os.getcwd()}")

# Define database path - try multiple approaches for reliability
db_filename = "annual_reports.db"
db_path = os.path.join(ROOT_DIR, db_filename)
logger.info(f"Attempted database path: {db_path}")

# Ensure the directory exists with proper permissions
db_dir = os.path.dirname(db_path)
if not os.path.exists(db_dir):
    try:
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created directory: {db_dir}")
    except Exception as e:
        logger.error(f"Error creating directory: {e}")

# Try to create an explicit test file to check write permissions
try:
    test_file_path = os.path.join(db_dir, "test_write.txt")
    with open(test_file_path, "w") as f:
        f.write("test")
    logger.info(f"Successfully wrote test file to {db_dir}")
    # Clean up test file
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
except Exception as e:
    logger.error(f"Cannot write to directory: {e}")

# Set absolute path for SQLite database
DATABASE_URL = f"sqlite:///{db_path}"
logger.info(f"Default DATABASE_URL: {DATABASE_URL}")

# Check if the DB URL from env is also absolute
env_db_url = os.getenv("DATABASE_URL")
if env_db_url:
    logger.info(f"Env DATABASE_URL: {env_db_url}")
    # If env URL is relative, convert to absolute
    if env_db_url.startswith("sqlite:///") and not env_db_url.startswith("sqlite:////"):
        relative_path = env_db_url.replace("sqlite:///", "")
        if not os.path.isabs(relative_path):
            abs_path = os.path.abspath(relative_path)
            DATABASE_URL = f"sqlite:///{abs_path}"
            logger.info(f"Converted relative path to absolute: {DATABASE_URL}")
    else:
        DATABASE_URL = env_db_url

# For SQLite, ensure we're using the correct number of slashes for absolute paths
if DATABASE_URL.startswith("sqlite:///") and os.path.isabs(DATABASE_URL.replace("sqlite:///", "")):
    # For absolute paths on Unix/Linux, use four slashes
    abs_path = DATABASE_URL.replace("sqlite:///", "")
    DATABASE_URL = f"sqlite:////{abs_path}"
    logger.info(f"Adjusted to four-slash absolute path: {DATABASE_URL}")

logger.info(f"Final DATABASE_URL: {DATABASE_URL}")

# Create engine with verbose error reporting
try:
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False},
        echo=True  # Enable SQL logging
    )

    # Test connection immediately to verify it works
    connection = engine.connect()
    connection.close()
    logger.info("Database connection test successful")
except Exception as e:
    logger.error(f"Database connection test failed: {e}")
    
    # Try with memory database as fallback for testing
    logger.warning("Attempting fallback to in-memory database")
    DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 