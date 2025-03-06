import os
import time
import requests
import logging
import sys
import argparse
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

# Backend API URL
API_URL = "http://localhost:8000/api"

def test_with_real_pdf(pdf_path, company_name, year, ticker="", sector=""):
    """
    Test the analysis pipeline with a real PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        company_name: Name of the company
        year: Year of the report
        ticker: Company ticker symbol (optional)
        sector: Company sector (optional)
    
    Returns:
        bool: True if the test was successful, False otherwise
    """
    if not os.path.exists(pdf_path):
        logger.error(f"PDF file not found: {pdf_path}")
        return False
    
    # Get the filename from the path
    filename = os.path.basename(pdf_path)
    
    # Upload the file
    try:
        with open(pdf_path, "rb") as file:
            files = {"file": (filename, file, "application/pdf")}
            data = {
                "company_name": company_name,
                "year": str(year),
                "ticker": ticker,
                "sector": sector
            }
            
            logger.info(f"Uploading PDF file: {filename}")
            response = requests.post(f"{API_URL}/reports/upload", files=files, data=data)
            
            if response.status_code != 200:
                logger.error(f"Upload failed with status code {response.status_code}: {response.text}")
                return False
            
            # Get the report ID from the response
            response_data = response.json()
            report_id = response_data.get("report_id")
            
            if not report_id:
                logger.error("No report ID returned in the response")
                return False
            
            logger.info(f"Upload successful. Report ID: {report_id}")
            
            # Monitor the analysis process
            max_checks = 60  # Check for up to 10 minutes (10 seconds between checks)
            checks = 0
            
            while checks < max_checks:
                checks += 1
                
                # Check the report status
                status_response = requests.get(f"{API_URL}/reports/{report_id}/status")
                
                if status_response.status_code != 200:
                    logger.error(f"Failed to get report status: {status_response.text}")
                    time.sleep(10)
                    continue
                
                status_data = status_response.json()
                status = status_data.get("status")
                
                logger.info(f"Report status (check {checks}/{max_checks}): {status}")
                
                # If the status is completed or failed, we're done
                if status in ["completed", "failed"]:
                    if status == "completed":
                        logger.info("Analysis completed successfully!")
                        
                        # Check if metrics were extracted
                        metrics_response = requests.get(f"{API_URL}/reports/{report_id}/metrics")
                        if metrics_response.status_code == 200:
                            metrics = metrics_response.json()
                            logger.info(f"Extracted {len(metrics)} metrics")
                            
                            # Print the metrics
                            for metric in metrics:
                                logger.info(f"  - {metric.get('name')}: {metric.get('value')} {metric.get('unit')}")
                        
                        # Check if summaries were generated
                        summaries_response = requests.get(f"{API_URL}/reports/{report_id}/summaries")
                        if summaries_response.status_code == 200:
                            summaries = summaries_response.json()
                            logger.info(f"Generated summaries: {list(summaries.keys())}")
                            
                            # Print the executive summary
                            if "executive" in summaries:
                                logger.info("\nExecutive Summary:")
                                logger.info(summaries["executive"][:500] + "..." if len(summaries["executive"]) > 500 else summaries["executive"])
                            
                            # Print the sentiment
                            if "sentiment" in summaries:
                                logger.info("\nSentiment Analysis:")
                                logger.info(summaries["sentiment"])
                        
                        return True
                    else:
                        error_message = status_data.get("error_message", "Unknown error")
                        logger.error(f"Analysis failed: {error_message}")
                        return False
                
                # Wait before checking again
                logger.info("Waiting 10 seconds before checking status again...")
                time.sleep(10)
            
            logger.error("Analysis timed out after maximum number of checks")
            return False
            
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        return False

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test the analysis pipeline with a real PDF file")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("company_name", help="Name of the company")
    parser.add_argument("year", type=int, help="Year of the report")
    parser.add_argument("--ticker", default="", help="Company ticker symbol")
    parser.add_argument("--sector", default="", help="Company sector")
    
    args = parser.parse_args()
    
    logger.info(f"Starting test with real PDF: {args.pdf_path}")
    success = test_with_real_pdf(
        args.pdf_path,
        args.company_name,
        args.year,
        args.ticker,
        args.sector
    )
    
    if success:
        logger.info("Test completed successfully!")
        sys.exit(0)
    else:
        logger.error("Test failed!")
        sys.exit(1) 