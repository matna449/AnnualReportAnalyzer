import os
import shutil
import logging
from typing import Optional, Dict, Any
from fastapi import UploadFile
from pathlib import Path

logger = logging.getLogger(__name__)

class FileService:
    """Service for handling file operations."""
    
    @staticmethod
    async def save_uploaded_file(file: UploadFile, destination_path: str) -> Dict[str, Any]:
        """
        Save an uploaded file to the specified destination.
        
        Args:
            file: The uploaded file
            destination_path: The path where the file should be saved
            
        Returns:
            Dictionary with file information
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            
            # Save the file
            with open(destination_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Get file size
            file_size = os.path.getsize(destination_path)
            
            logger.info(f"File saved successfully: {destination_path} ({file_size} bytes)")
            
            return {
                "filename": file.filename,
                "path": destination_path,
                "size": file_size,
                "content_type": file.content_type,
                "success": True
            }
        
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            return {
                "filename": file.filename,
                "error": str(e),
                "success": False
            }
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """
        Delete a file from the filesystem.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File deleted successfully: {file_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False
        
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False
    
    @staticmethod
    def get_file_info(file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information or None if file doesn't exist
        """
        try:
            if not os.path.exists(file_path):
                return None
            
            file_stats = os.stat(file_path)
            file_path_obj = Path(file_path)
            
            return {
                "filename": file_path_obj.name,
                "path": file_path,
                "size": file_stats.st_size,
                "created": file_stats.st_ctime,
                "modified": file_stats.st_mtime,
                "extension": file_path_obj.suffix,
                "exists": True
            }
        
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return None 