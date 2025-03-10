"""
Centralized logging configuration for the Annual Report Analyzer.
This module provides functions to set up logging with consistent settings across the application.
"""

import os
import logging
from datetime import datetime

def setup_logging(app_name="app"):
    """
    Set up logging with consistent settings across the application.
    
    Args:
        app_name: Name prefix for log files
        
    Returns:
        tuple: (logger, log_file_path, sql_log_path)
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.getcwd(), "backend", "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    # Generate log file names with timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    log_file_path = os.path.join(logs_dir, f"{app_name}_{timestamp}.log")
    sql_log_path = os.path.join(logs_dir, f"sql_{timestamp}.log")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create handlers
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)

    # Create SQL-specific file handler
    sql_file_handler = logging.FileHandler(sql_log_path)
    sql_file_handler.setFormatter(formatter)

    # Configure root logger with console and file handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Configure SQLAlchemy logger to only log to file
    sql_logger = logging.getLogger('sqlalchemy.engine')
    sql_logger.setLevel(logging.INFO)
    sql_logger.propagate = False  # Don't propagate to root logger
    
    # Remove any existing handlers to avoid duplicates
    for handler in sql_logger.handlers[:]:
        sql_logger.removeHandler(handler)
    
    sql_logger.addHandler(sql_file_handler)

    # Get a logger for the calling module
    logger = logging.getLogger(app_name)
    logger.info(f"Application logs: {log_file_path}")
    logger.info(f"SQL logs: {sql_log_path}")
    
    return logger, log_file_path, sql_log_path

def get_logger(name):
    """
    Get a logger with the given name.
    
    Args:
        name: Name of the logger
        
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name) 