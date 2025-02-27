import os
import PyPDF2
import pdfplumber
import re
from typing import List, Dict, Any, Tuple
import logging
from backend.utils.helpers import sanitize_filename

logger = logging.getLogger(__name__)

class PDFService:
    def __init__(self):
        pass
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from a PDF file using PyPDF2."""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                page_count = len(reader.pages)
                
                text = ""
                for page_num in range(page_count):
                    page = reader.pages[page_num]
                    text += page.extract_text() + "\n\n"
                
                return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise
    
    def extract_text_with_layout(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract text with layout information using pdfplumber."""
        try:
            pages = []
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    tables = page.extract_tables()
                    
                    # Process tables into a more usable format
                    processed_tables = []
                    for table in tables:
                        if table:
                            # Convert all cells to strings
                            processed_table = [[str(cell) if cell is not None else "" for cell in row] for row in table]
                            processed_tables.append(processed_table)
                    
                    pages.append({
                        "page_number": i + 1,
                        "text": text,
                        "tables": processed_tables
                    })
                
                return pages
        except Exception as e:
            logger.error(f"Error extracting text with layout from PDF: {str(e)}")
            raise
    
    def get_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from a PDF file."""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                metadata = reader.metadata
                page_count = len(reader.pages)
                
                return {
                    "title": metadata.title if metadata and metadata.title else None,
                    "author": metadata.author if metadata and metadata.author else None,
                    "subject": metadata.subject if metadata and metadata.subject else None,
                    "creator": metadata.creator if metadata and metadata.creator else None,
                    "producer": metadata.producer if metadata and metadata.producer else None,
                    "page_count": page_count
                }
        except Exception as e:
            logger.error(f"Error extracting metadata from PDF: {str(e)}")
            raise
    
    def chunk_text(self, text: str, chunk_size: int = 4000, overlap: int = 200) -> List[str]:
        """Split text into chunks of specified size with overlap."""
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            
            # If we're not at the end of the text, try to find a good breaking point
            if end < text_length:
                # Try to find a newline or period to break at
                newline_pos = text.rfind('\n', start, end)
                period_pos = text.rfind('. ', start, end)
                
                # Use the latest good breaking point
                if newline_pos > start + chunk_size // 2:
                    end = newline_pos + 1  # Include the newline
                elif period_pos > start + chunk_size // 2:
                    end = period_pos + 2  # Include the period and space
            
            # Add the chunk
            chunks.append(text[start:end])
            
            # Move the start position, accounting for overlap
            start = end - overlap if end < text_length else text_length
        
        return chunks
    
    def extract_financial_tables(self, pages: List[Dict[str, Any]]) -> List[List[List[str]]]:
        """Extract tables that are likely to contain financial information."""
        financial_tables = []
        
        # Keywords that suggest a table contains financial data
        financial_keywords = [
            'revenue', 'income', 'profit', 'loss', 'earnings', 'ebitda', 
            'assets', 'liabilities', 'equity', 'cash flow', 'balance sheet',
            'statement of operations', 'financial', 'fiscal', 'quarter', 'annual'
        ]
        
        for page in pages:
            for table in page["tables"]:
                # Check if any cell in the table contains financial keywords
                is_financial = False
                for row in table:
                    for cell in row:
                        cell_lower = cell.lower()
                        if any(keyword in cell_lower for keyword in financial_keywords):
                            is_financial = True
                            break
                    if is_financial:
                        break
                
                if is_financial:
                    financial_tables.append({
                        "page_number": page["page_number"],
                        "table": table
                    })
        
        return financial_tables
    
    def save_upload(self, file_content: bytes, filename: str, upload_dir: str) -> Tuple[str, str]:
        """Save an uploaded file to disk and return the file path."""
        try:
            # Ensure the upload directory exists
            if not os.path.exists(upload_dir):
                logger.info(f"Creating upload directory: {upload_dir}")
                os.makedirs(upload_dir, exist_ok=True)
            
            # Check if upload directory is writable
            if not os.access(upload_dir, os.W_OK):
                logger.error(f"Upload directory is not writable: {upload_dir}")
                raise PermissionError(f"Upload directory is not writable: {upload_dir}")
            
            # Sanitize and make the filename unique
            safe_filename = sanitize_filename(filename)
            file_path = os.path.join(upload_dir, safe_filename)
            
            logger.info(f"Saving file {filename} (sanitized to {safe_filename}) to {upload_dir}")
            logger.info(f"File content size: {len(file_content)} bytes")
            
            # Save the file
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
            
            # Verify the file was saved correctly
            if not os.path.exists(file_path):
                logger.error(f"File not found after save attempt: {file_path}")
                raise FileNotFoundError(f"Failed to save file at {file_path}")
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.error(f"File saved but has zero size: {file_path}")
                raise IOError(f"File saved but has zero size: {file_path}")
            
            logger.info(f"File saved successfully with size: {file_size} bytes")
                
            # Check if the file is readable
            try:
                with open(file_path, "rb") as test_read:
                    # Just read a small portion to verify it's accessible
                    test_read.read(1024)
                    logger.info(f"File is readable: {file_path}")
            except Exception as e:
                logger.error(f"File saved but not readable: {file_path}, Error: {str(e)}")
                raise IOError(f"File saved but not readable: {str(e)}")
                
            logger.info(f"Successfully saved file: {safe_filename} to {upload_dir}")
            return file_path, safe_filename
            
        except Exception as e:
            logger.error(f"Error saving uploaded file {filename}: {str(e)}")
            # Clean up any partially written file
            if 'file_path' in locals() and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up partial file: {file_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to clean up partial file: {str(cleanup_error)}")
            raise 