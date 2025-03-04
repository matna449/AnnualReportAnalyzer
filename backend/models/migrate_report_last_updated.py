"""
Migration script to add the last_updated column to the reports table.
"""
import os
import logging
import sqlite3
from datetime import datetime

logging.basicConfig(level=logging.INFO, 
                   format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def migrate_database():
    """
    Add the last_updated column to the reports table if it doesn't exist.
    """
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'annual_reports.db')
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found at {db_path}")
        return False
    
    logger.info(f"Starting migration on database: {db_path}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the last_updated column already exists
        cursor.execute("PRAGMA table_info(reports)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if "last_updated" in column_names:
            logger.info("last_updated column already exists in reports table")
            conn.close()
            return True
        
        # Add the last_updated column
        logger.info("Adding last_updated column to reports table")
        cursor.execute(
            "ALTER TABLE reports ADD COLUMN last_updated TIMESTAMP"
        )
        
        # Update the column with current timestamp for existing records
        current_time = datetime.utcnow().isoformat()
        cursor.execute(
            f"UPDATE reports SET last_updated = '{current_time}'"
        )
        
        conn.commit()
        logger.info("Migration completed successfully")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(reports)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if "last_updated" in column_names:
            logger.info("Verified: last_updated column exists in reports table")
        else:
            logger.error("Verification failed: last_updated column not found after migration")
            
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    result = migrate_database()
    if result:
        logger.info("Migration script completed successfully")
    else:
        logger.error("Migration script failed") 