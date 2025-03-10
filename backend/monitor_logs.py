import os
import time
import re
import sys
import logging
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

def monitor_logs(log_file_path=None, duration=300):
    """
    Monitor backend logs for HuggingFace API calls and analysis process.
    
    Args:
        log_file_path: Path to the log file to monitor. If None, will look for the most recent log file.
        duration: How long to monitor the logs in seconds (default: 5 minutes)
    """
    # If no log file path provided, look for the most recent log file
    if not log_file_path:
        # Check both possible log directories
        log_dirs = [
            os.path.join(os.getcwd(), "backend", "logs"),
            os.path.join(os.getcwd(), "backend", "backend", "logs")
        ]
        
        for log_dir in log_dirs:
            if os.path.exists(log_dir):
                # First look for app log files
                app_log_files = glob.glob(os.path.join(log_dir, "app_*.log"))
                if app_log_files:
                    # Sort by modification time (most recent first)
                    app_log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                    log_file_path = app_log_files[0]
                    logger.info(f"Found app log file: {log_file_path}")
                    break
                
                # Then look for pipeline log files
                pipeline_log_files = glob.glob(os.path.join(log_dir, "pipeline_*.log"))
                if pipeline_log_files:
                    # Sort by modification time (most recent first)
                    pipeline_log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                    log_file_path = pipeline_log_files[0]
                    logger.info(f"Found pipeline log file: {log_file_path}")
                    break
                
                # Fall back to any log file
                log_files = [f for f in os.listdir(log_dir) if f.endswith(".log")]
                if log_files:
                    # Sort by modification time (most recent first)
                    log_files.sort(key=lambda x: os.path.getmtime(os.path.join(log_dir, x)), reverse=True)
                    log_file_path = os.path.join(log_dir, log_files[0])
                    logger.info(f"Found log file: {log_file_path}")
                    break
        
        if not log_file_path:
            logger.error("No log files found")
            return
    
    logger.info(f"Monitoring log file: {log_file_path}")
    
    # Patterns to look for
    patterns = {
        "upload": r"PIPELINE: UPLOAD STARTED",
        "analysis_start": r"PIPELINE: INITIAL ANALYSIS STARTED",
        "text_extraction": r"PIPELINE: TEXT EXTRACTION - Completed",
        "ai_analysis_start": r"PIPELINE: Starting AI analysis",
        "huggingface_call": r"Calling HuggingFace API",
        "sentiment_analysis": r"Sentiment analysis completed",
        "entity_extraction": r"Entity extraction completed",
        "risk_analysis": r"Risk analysis completed",
        "summary_generation": r"Generated executive summary",
        "insights_generation": r"Generating insights from analysis data",
        "analysis_complete": r"PIPELINE: ANALYSIS COMPLETED",
        "error": r"ERROR|FAILED|failed|error"
    }
    
    # Counters for each pattern
    counters = {key: 0 for key in patterns}
    
    # Start monitoring
    start_time = time.time()
    last_position = 0
    
    logger.info(f"Starting log monitoring for {duration} seconds...")
    
    while time.time() - start_time < duration:
        try:
            # Check if file exists
            if not os.path.exists(log_file_path):
                logger.error(f"Log file not found: {log_file_path}")
                time.sleep(5)
                continue
            
            # Open the file and seek to the last position
            with open(log_file_path, "r") as f:
                f.seek(last_position)
                new_content = f.read()
                last_position = f.tell()
            
            # If there's new content, check for patterns
            if new_content:
                for key, pattern in patterns.items():
                    # Skip the error pattern for now, we'll handle it separately
                    if key == "error":
                        continue
                        
                    matches = re.findall(pattern, new_content)
                    if matches:
                        counters[key] += len(matches)
                        for match in matches:
                            # Extract the line containing the match
                            line = next((line for line in new_content.split("\n") if pattern in line), "")
                            logger.info(f"[{key.upper()}] {line}")
                
                # Handle error pattern separately
                if "error" in patterns:
                    error_pattern = patterns["error"]
                    # Look for lines that contain ERROR or error but not in a way that would match normal log levels
                    error_matches = []
                    for line in new_content.split("\n"):
                        if re.search(r'\bERROR\b|\berror\b|\bfailed\b|\bFAILED\b', line, re.IGNORECASE):
                            # Skip lines that are just log level indicators
                            if not re.match(r'.*\b(INFO|DEBUG|WARNING)\b.*', line):
                                error_matches.append(line)
                    
                    if error_matches:
                        counters["error"] += len(error_matches)
                        for match in error_matches:
                            logger.info(f"[ERROR] {match}")
            
            # Wait before checking again
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error monitoring logs: {str(e)}")
            time.sleep(5)
    
    # Print summary
    logger.info("\n--- Monitoring Summary ---")
    for key, count in counters.items():
        logger.info(f"{key}: {count} occurrences")
    
    # Check if the analysis pipeline was triggered
    if counters["upload"] > 0 and counters["analysis_start"] > 0:
        logger.info("✅ Analysis pipeline was triggered successfully")
    else:
        logger.error("❌ Analysis pipeline was NOT triggered")
    
    # Check if HuggingFace API was called
    if counters["huggingface_call"] > 0:
        logger.info("✅ HuggingFace API was called successfully")
    else:
        logger.error("❌ HuggingFace API was NOT called")
    
    # Check if analysis completed
    if counters["analysis_complete"] > 0:
        logger.info("✅ Analysis completed successfully")
    else:
        logger.error("❌ Analysis did NOT complete")
    
    # Check for errors
    if counters["error"] > 0:
        logger.warning(f"⚠️ {counters['error']} errors detected in the logs")

if __name__ == "__main__":
    logger.info("Starting log monitoring")
    monitor_logs() 