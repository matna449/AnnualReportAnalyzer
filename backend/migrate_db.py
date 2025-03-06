import os
import logging
import sqlite3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Database path - both possible locations
DB_PATHS = [
    os.path.join(os.getcwd(), "backend", "annual_reports.db"),
    os.path.join(os.getcwd(), "annual_reports.db")
]

def migrate_database():
    """Add error_message column to the reports table if it doesn't exist."""
    # Find the database file that exists
    db_path = None
    for path in DB_PATHS:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        logger.error("Database file not found")
        return False
    
    try:
        logger.info(f"Connecting to database at {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if error_message column exists
        cursor.execute("PRAGMA table_info(reports)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if "error_message" not in column_names:
            logger.info("Adding error_message column to reports table")
            cursor.execute("ALTER TABLE reports ADD COLUMN error_message TEXT")
            conn.commit()
            logger.info("Migration successful: Added error_message column")
        else:
            logger.info("error_message column already exists in reports table")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error during database migration: {str(e)}")
        return False

if __name__ == "__main__":
    if migrate_database():
        logger.info("Database migration completed successfully")
    else:
        logger.error("Database migration failed") 