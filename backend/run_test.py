import os
import sys
import time
import logging
import threading
import glob
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_test():
    """Run the upload test and monitor logs in parallel."""
    # Import the test modules
    from test_upload_analysis import test_upload_and_analysis
    from monitor_logs import monitor_logs
    
    # Check for app log files in both possible locations
    log_dirs = [
        os.path.join(os.getcwd(), "backend", "logs"),
        os.path.join(os.getcwd(), "backend", "backend", "logs")
    ]
    
    app_log_file = None
    
    # Try to find the most recent app log file
    for log_dir in log_dirs:
        if os.path.exists(log_dir):
            app_log_files = glob.glob(os.path.join(log_dir, "app_*.log"))
            if app_log_files:
                # Sort by modification time (most recent first)
                app_log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                app_log_file = app_log_files[0]
                logger.info(f"Found app log file: {app_log_file}")
                break
    
    # If no app log file found, check for pipeline log files
    if not app_log_file:
        for log_dir in log_dirs:
            if os.path.exists(log_dir):
                pipeline_log_files = glob.glob(os.path.join(log_dir, "pipeline_*.log"))
                if pipeline_log_files:
                    # Sort by modification time (most recent first)
                    pipeline_log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                    app_log_file = pipeline_log_files[0]
                    logger.info(f"Found pipeline log file: {app_log_file}")
                    break
    
    # If still no log file found, create a test run log file
    if not app_log_file:
        log_dir = os.path.join(os.getcwd(), "backend", "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        app_log_file = os.path.join(log_dir, f"test_run_{timestamp}.log")
        
        # Create an empty log file
        with open(app_log_file, "w") as f:
            f.write(f"Test run started at {datetime.now().isoformat()}\n")
        
        logger.info(f"Created test run log file: {app_log_file}")
    
    # Start the log monitoring in a separate thread
    monitor_thread = threading.Thread(
        target=monitor_logs,
        args=(app_log_file, 300)  # Monitor for 5 minutes
    )
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Wait a moment for the monitoring to start
    time.sleep(2)
    
    # Run the upload test
    logger.info("Starting upload test...")
    test_result = test_upload_and_analysis()
    
    # Wait for the monitoring thread to finish
    monitor_thread.join(timeout=310)  # Wait a bit longer than the monitoring duration
    
    # Log the final result
    if test_result:
        logger.info("✅ Test completed successfully!")
    else:
        logger.error("❌ Test failed!")
    
    return test_result

if __name__ == "__main__":
    logger.info("Starting combined test run")
    success = run_test()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 