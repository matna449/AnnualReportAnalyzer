import os
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
import time
import requests
from datetime import datetime
import math

logger = logging.getLogger(__name__)

def estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in text based on a conservative ratio.
    
    Args:
        text: Text to estimate tokens for
        
    Returns:
        Estimated number of tokens
    """
    # For English text, a conservative estimate is 4 chars per token
    # This varies by model - BERT, GPT, T5 all tokenize differently
    # We're using a conservative estimate that works across models
    words = text.split()
    word_count = len(words)
    
    # English averages ~1.3 tokens per word for most tokenizers
    estimated_tokens = math.ceil(word_count * 1.3)
    
    # Return conservative estimate plus 10% buffer
    return math.ceil(estimated_tokens * 1.1)

def chunk_text(text: str, chunk_size: int = 1600, overlap_size: int = 200, max_tokens: int = 1024) -> List[str]:
    """
    Split text into chunks for processing, respecting token limits.
    
    Args:
        text: Text to split into chunks
        chunk_size: Target size of each chunk in characters
        overlap_size: Number of characters to overlap between chunks
        max_tokens: Maximum number of tokens per chunk (for model context limits)
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    # Reduce chunk size to a safer default (1600 characters instead of ~4000)
    char_limit = min(chunk_size, 1600)
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + char_limit, len(text))
        
        # If not at the end, try to break at a sentence boundary
        if end < len(text):
            # Look for sentence boundary within the last 20% of the chunk
            boundary_search_start = max(start + int(char_limit * 0.8), start)
            sentence_boundary = text.rfind('. ', boundary_search_start, end)
            if sentence_boundary != -1:
                end = sentence_boundary + 2  # Include the period and space
        
        # Get the chunk
        chunk = text[start:end]
        
        # Check if this chunk might be too large in terms of tokens
        estimated_token_count = estimate_tokens(chunk)
        if estimated_token_count > max_tokens:
            logger.warning(f"Chunk exceeds token limit ({estimated_token_count} > {max_tokens}). Splitting recursively.")
            # Recursively split this chunk into smaller pieces
            subchart_token_limit = max_tokens // 2  # Use half the token limit for sub-chunks
            subchunk_char_size = len(chunk) // 2   # Use half the characters
            subchunks = chunk_text(chunk, subchunk_char_size, overlap_size // 2, subchart_token_limit)
            chunks.extend(subchunks)
        else:
            chunks.append(chunk)
        
        # Calculate next start position with overlap
        overlap = min(overlap_size, char_limit // 10)  # 10% overlap by default
        start = end - overlap if end - overlap > start else end
    
    logger.info(f"Split text into {len(chunks)} chunks for processing (max {max_tokens} tokens per chunk)")
    return chunks

def extract_metrics_with_regex(text: str) -> List[Dict[str, Any]]:
    """
    Extract financial metrics using regex patterns.
    
    Args:
        text: Financial text to analyze
        
    Returns:
        List of dictionaries containing extracted metrics
    """
    # Common financial metrics patterns
    patterns = [
        # Revenue pattern
        r'(?:total )?revenue(?:s)? (?:of|was|were|amounted to)? \$?(\d+(?:\.\d+)?)\s?(million|billion|m|b|k|thousand)?',
        # Net income pattern
        r'net income (?:of|was|were|amounted to)? \$?(\d+(?:\.\d+)?)\s?(million|billion|m|b|k|thousand)?',
        # EPS pattern
        r'earnings per share (?:of|was|were|amounted to)? \$?(\d+(?:\.\d+)?)',
        # Profit pattern
        r'(?:gross|operating|net) profit (?:of|was|were|amounted to)? \$?(\d+(?:\.\d+)?)\s?(million|billion|m|b|k|thousand)?',
    ]
    
    results = []
    
    # Process each pattern
    for pattern in patterns:
        matches = re.finditer(pattern, text.lower())
        for match in matches:
            value = match.group(1)
            unit = match.group(2) if len(match.groups()) > 1 and match.group(2) else ""
            
            # Determine metric name from the matched pattern
            if "revenue" in pattern:
                name = "Revenue"
                category = "Income Statement"
            elif "net income" in pattern:
                name = "Net Income"
                category = "Income Statement"
            elif "earnings per share" in pattern:
                name = "EPS"
                category = "Financial Ratios"
            elif "profit" in pattern:
                name = "Profit"
                category = "Income Statement"
            else:
                name = "Unknown Metric"
                category = "Other"
            
            # Standardize unit
            if unit:
                unit = unit.lower()
                if unit in ["m", "million"]:
                    unit = "million"
                    value_numeric = float(value) * 1_000_000
                elif unit in ["b", "billion"]:
                    unit = "billion"
                    value_numeric = float(value) * 1_000_000_000
                elif unit in ["k", "thousand"]:
                    unit = "thousand"
                    value_numeric = float(value) * 1_000
                else:
                    value_numeric = float(value)
            else:
                value_numeric = float(value)
                unit = ""
            
            # Create metric object
            metric = {
                "name": name,
                "value": value,
                "value_numeric": value_numeric,
                "unit": unit,
                "category": category,
                "context": text[max(0, match.start() - 50):min(len(text), match.end() + 50)]
            }
            
            results.append(metric)
    
    return results

def extract_risk_factors_with_regex(text: str) -> List[str]:
    """
    Extract risk factors from financial text using regex patterns.
    
    Args:
        text: Financial text to analyze
        
    Returns:
        List of extracted risk factors
    """
    # Common risk section headers
    risk_section_patterns = [
        r'(?:Item\s+)?1A\.?\s+Risk\s+Factors',
        r'(?:ITEM\s+)?1A\.?\s+RISK\s+FACTORS',
        r'Risk\s+Factors',
        r'RISK\s+FACTORS',
        r'Risks\s+and\s+Uncertainties',
        r'RISKS\s+AND\s+UNCERTAINTIES'
    ]
    
    # Find risk section
    risk_section_text = ""
    for pattern in risk_section_patterns:
        match = re.search(pattern, text)
        if match:
            # Extract text after the risk section header
            section_start = match.end()
            # Look for the next section header
            next_section_match = re.search(r'(?:Item|ITEM)\s+\d+[AB]?\.', text[section_start:])
            if next_section_match:
                section_end = section_start + next_section_match.start()
                risk_section_text = text[section_start:section_end]
            else:
                # If no next section, take a reasonable chunk
                risk_section_text = text[section_start:section_start + 20000]  # Limit to ~20k chars
            break
    
    # If no risk section found, return empty list
    if not risk_section_text:
        return []
    
    # Extract individual risk factors
    # Look for bullet points, numbered lists, or paragraph breaks
    risk_patterns = [
        r'•\s+([A-Z].*?)\n',  # Bullet points
        r'[\d]+\.\s+([A-Z].*?)\n',  # Numbered lists
        r'(?:\n\n|\r\n\r\n)([A-Z][^.]*?(?:\.|;))',  # Paragraphs starting with capital letter
        r'(?<=[.;])\s+([A-Z][^.]*?(?:could|may|might|will|would)\s+(?:adversely|negatively)\s+.*?[.;])'  # Sentences with risk language
    ]
    
    risks = []
    for pattern in risk_patterns:
        matches = re.finditer(pattern, risk_section_text)
        for match in matches:
            risk = match.group(1).strip()
            if len(risk) > 20 and len(risk) < 500:  # Reasonable length for a risk statement
                risks.append(risk)
    
    # Deduplicate and limit to top risks
    unique_risks = list(set(risks))
    return unique_risks[:20]  # Limit to top 20 risks for manageability

def extract_basic_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract basic entities using regex patterns.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with keys 'organizations' and 'locations' containing extracted entities
    """
    # Common organization suffixes
    org_patterns = [
        r'\b[A-Z][a-zA-Z]+ (?:Inc|Corp|Corporation|Company|Co|Ltd|LLC)\b',
        r'\b[A-Z][a-zA-Z]+ Technologies\b',
        r'\b[A-Z][a-zA-Z]+ Systems\b'
    ]
    
    # Common location patterns
    location_patterns = [
        r'\b(?:in|at|from) ([A-Z][a-zA-Z]+(?:, [A-Z][a-zA-Z]+)?)\b'
    ]
    
    # Extract organizations
    organizations = []
    for pattern in org_patterns:
        matches = re.findall(pattern, text)
        organizations.extend(matches)
    
    # Remove duplicates and limit
    organizations = list(set(organizations))[:10]
    
    # Extract locations
    locations = []
    for pattern in location_patterns:
        matches = re.findall(pattern, text)
        locations.extend(matches)
    
    # Remove duplicates and limit
    locations = list(set(locations))[:10]
    
    return {
        "organizations": organizations,
        "locations": locations
    }

def fallback_sentiment_analysis(text: str) -> Dict[str, Any]:
    """
    Fallback method for sentiment analysis when API calls fail.
    
    Args:
        text: Text to analyze
        
    Returns:
        Dictionary with sentiment analysis results
    """
    logger.info("Using fallback sentiment analysis method")
    
    # Define positive and negative word lists
    positive_words = ["increase", "growth", "profit", "success", "improve", "positive", 
                     "advantage", "opportunity", "strong", "exceed", "gain"]
    negative_words = ["decrease", "decline", "loss", "risk", "challenge", "negative", 
                     "difficult", "weak", "fail", "threat", "liability"]
    
    # Count occurrences
    positive_count = sum(text.lower().count(word) for word in positive_words)
    negative_count = sum(text.lower().count(word) for word in negative_words)
    
    # Determine sentiment
    if positive_count > negative_count * 1.5:
        sentiment = "positive"
        explanation = "More positive terms than negative terms"
    elif negative_count > positive_count * 1.5:
        sentiment = "negative"
        explanation = "More negative terms than negative terms"
    else:
        sentiment = "neutral" 
        explanation = "Balance of positive and negative terms"
    
    logger.info(f"Fallback sentiment result: {sentiment} (pos:{positive_count}, neg:{negative_count})")
    
    return {
        "sentiment": sentiment,
        "explanation": explanation,
        "confidence": 0.6,  # Lower confidence for fallback method
        "method": "fallback"
    } 