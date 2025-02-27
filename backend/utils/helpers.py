import os
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to ensure it's safe for storage.
    
    Args:
        filename: The original filename
        
    Returns:
        A sanitized version of the filename
    """
    # Remove any path components
    filename = os.path.basename(filename)
    
    # Replace problematic characters
    filename = re.sub(r'[^\w\s.-]', '_', filename)
    
    # Add timestamp to ensure uniqueness
    name, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    
    return f"{name}_{timestamp}{ext}"

def extract_year_from_text(text: str) -> Optional[str]:
    """
    Extract a year (likely the report year) from text.
    
    Args:
        text: The text to search for a year
        
    Returns:
        A year string (e.g., "2023") or None if not found
    """
    # Look for patterns like "Annual Report 2023" or "Fiscal Year 2023"
    year_patterns = [
        r'annual\s+report\s+(\d{4})',
        r'fiscal\s+year\s+(\d{4})',
        r'fy\s+(\d{4})',
        r'year\s+ended\s+.*?\s+(\d{4})',
        r'december\s+\d+,\s+(\d{4})',
        r'20\d{2}\s+annual\s+report',
        r'annual\s+report\s+.*?20\d{2}',
    ]
    
    text_lower = text.lower()
    
    for pattern in year_patterns:
        matches = re.search(pattern, text_lower)
        if matches:
            return matches.group(1)
    
    # If no specific pattern matches, look for any 4-digit year between 2000-2030
    years = re.findall(r'\b(20[0-2]\d)\b', text)
    if years:
        # Return the most recent year found
        return max(years)
    
    return None

def extract_company_info(text: str) -> Dict[str, Any]:
    """
    Extract company information from text.
    
    Args:
        text: The text to search for company information
        
    Returns:
        A dictionary with company information
    """
    # Initialize result
    result = {
        "name": None,
        "ticker": None,
        "sector": None
    }
    
    # Look for company name patterns
    name_patterns = [
        r'([\w\s]+),?\s+Inc\.', 
        r'([\w\s]+)\s+Corporation',
        r'([\w\s]+)\s+Company',
        r'([\w\s]+)\s+Ltd\.?',
        r'([\w\s]+)\s+PLC',
        r'([\w\s]+)\s+Group'
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, text)
        if match:
            result["name"] = match.group(0).strip()
            break
    
    # Look for ticker symbol (usually in parentheses)
    ticker_match = re.search(r'\(([A-Z]{1,5})\)', text)
    if ticker_match:
        result["ticker"] = ticker_match.group(1)
    
    return result

def format_financial_value(value: str) -> str:
    """
    Format a financial value for consistent display.
    
    Args:
        value: The financial value as a string
        
    Returns:
        A formatted string
    """
    # Try to convert to float
    try:
        # Remove any non-numeric characters except decimal point
        clean_value = re.sub(r'[^\d.-]', '', value)
        num_value = float(clean_value)
        
        # Format based on magnitude
        if abs(num_value) >= 1_000_000_000:
            return f"${num_value / 1_000_000_000:.2f}B"
        elif abs(num_value) >= 1_000_000:
            return f"${num_value / 1_000_000:.2f}M"
        elif abs(num_value) >= 1_000:
            return f"${num_value / 1_000:.2f}K"
        else:
            return f"${num_value:.2f}"
    except (ValueError, TypeError):
        # If conversion fails, return the original value
        return value 