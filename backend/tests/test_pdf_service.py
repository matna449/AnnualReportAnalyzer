import os
import pytest
import tempfile
from backend.services.pdf_service import PDFService

# Initialize the service
pdf_service = PDFService()

def test_chunk_text():
    """Test the chunk_text method."""
    # Create a sample text
    text = "This is a test. " * 100
    
    # Test with default parameters
    chunks = pdf_service.chunk_text(text)
    assert len(chunks) > 0
    
    # Test with custom parameters
    chunks = pdf_service.chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) > 0
    
    # Test with empty text
    chunks = pdf_service.chunk_text("")
    assert len(chunks) == 0

def test_save_upload():
    """Test the save_upload method."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        temp.write(b"Test content")
        temp_path = temp.name
    
    try:
        # Read the file content
        with open(temp_path, "rb") as f:
            content = f.read()
        
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test saving the file
            file_path, filename = pdf_service.save_upload(content, "test.pdf", temp_dir)
            
            # Check that the file exists
            assert os.path.exists(file_path)
            
            # Check that the filename contains the original filename
            assert "test" in filename
            assert filename.endswith(".pdf")
            
            # Check that the content was saved correctly
            with open(file_path, "rb") as f:
                saved_content = f.read()
                assert saved_content == content
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path) 