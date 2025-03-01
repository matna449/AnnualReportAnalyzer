#!/usr/bin/env python3
"""
Test script to verify database connection
"""

import os
import sys
import logging
import sqlite3
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Add the parent directory to sys.path to ensure imports work correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

def test_working_directory():
    """Test the current working directory"""
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Script directory: {os.path.dirname(os.path.abspath(__file__))}")
    
    # Check if we can create a file in the current directory
    try:
        with open("test_write.txt", "w") as f:
            f.write("test")
        logger.info("Successfully wrote test file to current directory")
        os.remove("test_write.txt")
    except Exception as e:
        logger.error(f"Error writing to current directory: {e}")

def test_sqlite_direct():
    """Test direct SQLite connection"""
    try:
        # Try to create a test database in the current directory
        conn = sqlite3.connect('test.db')
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS test (id INTEGER)')
        cursor.execute('INSERT INTO test VALUES (1)')
        conn.commit()
        logger.info("Successfully created and wrote to test database in current directory")
        
        # Verify we can read from it
        cursor.execute('SELECT * FROM test')
        result = cursor.fetchall()
        logger.info(f"Read from test database: {result}")
        
        conn.close()
        
        # Clean up
        if os.path.exists('test.db'):
            os.remove('test.db')
            logger.info("Removed test database")
    except Exception as e:
        logger.error(f"Error with direct SQLite connection: {e}")
        logger.error(traceback.format_exc())

def test_sqlalchemy_connection():
    """Test SQLAlchemy connection"""
    try:
        from models.database_session import get_db, engine
        from sqlalchemy import text
        
        # Test if we can create tables
        from sqlalchemy import Column, Integer, String, MetaData, Table
        
        metadata = MetaData()
        test_table = Table(
            'test_table', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String)
        )
        
        # Create the table
        metadata.create_all(engine)
        logger.info("Successfully created test table with SQLAlchemy")
        
        # Get a session and try to use it
        db_generator = get_db()
        db = next(db_generator)
        
        # Execute a simple query
        result = db.execute(text("SELECT 1")).fetchall()
        logger.info(f"SQLAlchemy query result: {result}")
        
        # Close the session
        db.close()
        logger.info("Successfully closed SQLAlchemy session")
        
        # Drop the test table
        metadata.drop_all(engine)
        logger.info("Successfully dropped test table")
        
    except Exception as e:
        logger.error(f"Error with SQLAlchemy connection: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Starting database connection tests")
    
    test_working_directory()
    test_sqlite_direct()
    test_sqlalchemy_connection()
    
    logger.info("Database connection tests completed") 