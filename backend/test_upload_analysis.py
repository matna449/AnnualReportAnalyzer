import os
import time
import requests
import logging
from datetime import datetime
import sys
import random
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO

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

def create_test_pdf(file_path):
    """Create a test PDF file with reportlab."""
    try:
        # Create a PDF with reportlab
        c = canvas.Canvas(file_path, pagesize=letter)
        
        # Add a title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "Annual Report for Test Company 2023")
        
        # Add executive summary
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 720, "Executive Summary")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, 700, "Test Company had a strong financial year with revenue growth of 15%.")
        c.drawString(100, 680, "Total revenue was $500 million, up from $435 million in the previous year.")
        c.drawString(100, 660, "Net income was $75 million, representing a profit margin of 15%.")
        c.drawString(100, 640, "Earnings per share was $2.50, compared to $2.10 in the previous year.")
        
        # Add financial highlights
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 610, "Financial Highlights")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, 590, "- Revenue: $500 million")
        c.drawString(100, 570, "- Net Income: $75 million")
        c.drawString(100, 550, "- EPS: $2.50")
        c.drawString(100, 530, "- Operating Cash Flow: $90 million")
        c.drawString(100, 510, "- Capital Expenditures: $30 million")
        
        # Add risk factors
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 480, "Risk Factors")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, 460, "The company faces several risks including market competition and regulatory changes.")
        c.drawString(100, 440, "Economic downturns could impact consumer spending and affect our revenue.")
        c.drawString(100, 420, "Supply chain disruptions remain a concern for our manufacturing operations.")
        
        # Add business outlook
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 390, "Business Outlook")
        
        c.setFont("Helvetica", 12)
        c.drawString(100, 370, "We expect continued growth in the coming year with projected revenue of $550 million.")
        c.drawString(100, 350, "New product launches are expected to drive additional revenue in Q2 and Q3.")
        c.drawString(100, 330, "We plan to expand into new markets in Asia and Europe during the next fiscal year.")
        
        # Add more text to ensure sufficient content
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 300, "Additional Information")
        
        c.setFont("Helvetica", 12)
        for i in range(10):
            y_pos = 280 - (i * 20)
            c.drawString(100, y_pos, f"This is additional text line {i+1} to ensure sufficient content for extraction.")
        
        # Save the PDF
        c.save()
        logger.info(f"Created test PDF file with reportlab: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error creating test PDF: {str(e)}")
        return False

def test_upload_and_analysis():
    """
    Test uploading a PDF and verify the analysis process is started.
    
    This function:
    1. Uploads a PDF file to the backend
    2. Checks if the upload is successful
    3. Monitors the analysis process
    4. Verifies the report status changes
    """
    # Create a sample PDF file for testing
    uploads_dir = os.path.join(os.getcwd(), "backend", "uploads")
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        logger.info(f"Created uploads directory: {uploads_dir}")
    
    # Check if there are existing PDF files in the uploads directory
    existing_pdfs = [f for f in os.listdir(uploads_dir) if f.endswith('.pdf') and not f.startswith('test_upload_')]
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_filename = f"test_upload_{timestamp}.pdf"
    test_file_path = os.path.join(uploads_dir, test_filename)
    
    # Create a test PDF file
    if not create_test_pdf(test_file_path):
        logger.error("Failed to create test PDF file")
        return False
    
    # Prepare upload data
    company_name = "Test Company"
    year = 2023
    
    # Upload the file
    try:
        with open(test_file_path, "rb") as file:
            files = {"file": (test_filename, file, "application/pdf")}
            data = {
                "company_name": company_name,
                "year": str(year),
                "ticker": "TEST",
                "sector": "Technology"
            }
            
            logger.info("Uploading PDF file to backend...")
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
            max_checks = 30  # Check for up to 5 minutes (10 seconds between checks)
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
                        
                        # Check if summaries were generated
                        summaries_response = requests.get(f"{API_URL}/reports/{report_id}/summaries")
                        if summaries_response.status_code == 200:
                            summaries = summaries_response.json()
                            logger.info(f"Generated summaries: {list(summaries.keys())}")
                        
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
    finally:
        # Clean up the test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            logger.info(f"Removed test file: {test_file_path}")

if __name__ == "__main__":
    logger.info("Starting upload and analysis test")
    success = test_upload_and_analysis()
    
    if success:
        logger.info("Test completed successfully!")
    else:
        logger.error("Test failed!") 