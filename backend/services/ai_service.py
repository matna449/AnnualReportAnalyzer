import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
import re
import json
import requests
from time import sleep
import time
from datetime import datetime

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")
        # Add task parameter to the URL to specify sentiment-analysis
        self.finbert_model_url = "https://api-inference.huggingface.co/models/matna449/my-finbert"
        self.finbert_model_url_with_task = f"{self.finbert_model_url}?task=sentiment-analysis"
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "4000"))
        self.overlap_size = int(os.getenv("OVERLAP_SIZE", "200"))
        
        # Validate API key
        self._validate_api_key()
        
        # Initialize tokenizer for chunking (if needed)
        self.tokenizer = None
        try:
            # We'll use a simple character-based tokenizer for chunking
            # No need to load the full model locally
            logger.info("Using character-based chunking for FinBERT model")
        except Exception as e:
            logger.error(f"Error initializing tokenizer: {str(e)}")
    
    def _validate_api_key(self):
        """Validate the Hugging Face API key for FinBERT model."""
        self.is_api_key_valid = False
        
        if not self.huggingface_api_key:
            logger.warning("No Hugging Face API key provided in environment variables.")
            return
            
        if len(self.huggingface_api_key) < 8:  # Basic length check
            logger.warning("Hugging Face API key appears to be invalid (too short).")
            return
            
        # Test API key with a simple request to the FinBERT model
        try:
            headers = {"Authorization": f"Bearer {self.huggingface_api_key}"}
            # Use a simple test request to validate the API key
            response = requests.post(
                self.finbert_model_url_with_task,  # Use URL with task parameter
                headers=headers,
                json={"inputs": "The company reported strong financial results."},
                timeout=5
            )
            
            # Log response details for debugging
            logger.debug(f"FinBERT API validation - Status code: {response.status_code}")
            logger.debug(f"FinBERT API validation - Response content: {response.text[:200]}")
            
            if response.status_code == 200:
                self.is_api_key_valid = True
                logger.info("Hugging Face API key validated successfully for FinBERT model.")
            elif response.status_code == 401:
                logger.error("Hugging Face API key is invalid for FinBERT model (401 Unauthorized).")
            else:
                logger.warning(f"FinBERT API key validation returned status code: {response.status_code}")
                logger.warning(response.text)
        except Exception as e:
            logger.error(f"Error validating Hugging Face API key for FinBERT: {str(e)}")
    
    def _call_finbert_api(self, text: str, max_retries: int = 3) -> Dict[str, Any]:
        """Make a call to the FinBERT API."""
        if not self.is_api_key_valid:
            logger.error("Cannot call FinBERT API: No valid API key configured")
            raise ValueError("Hugging Face API key not configured or invalid")
        
        headers = {
            "Authorization": f"Bearer {self.huggingface_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {"inputs": text}
        
        logger.info(f"Calling FinBERT API with {len(text)} characters of text")
        logger.debug(f"FinBERT API payload sample: {text[:100]}...")
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.finbert_model_url_with_task,  # Use URL with task parameter
                    headers=headers, 
                    json=payload, 
                    timeout=30
                )
                
                # Check for authentication errors
                if response.status_code == 401:
                    logger.error("Authentication failed: Invalid Hugging Face API key (401 Unauthorized)")
                    self.is_api_key_valid = False  # Mark as invalid for future calls
                    raise ValueError("Invalid Hugging Face API key (401 Unauthorized)")
                
                # Check if the model is still loading
                if response.status_code == 503 and "Model is loading" in response.text:
                    wait_time = min(2 ** attempt, 10)  # Exponential backoff
                    logger.info(f"FinBERT model is loading. Waiting {wait_time} seconds before retry.")
                    sleep(wait_time)
                    continue
                
                # Check for service unavailability
                if response.status_code == 503:
                    logger.error(f"FinBERT API service unavailable (503). Attempt {attempt+1}/{max_retries}")
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 10)  # Exponential backoff
                        logger.info(f"Waiting {wait_time} seconds before retry.")
                        sleep(wait_time)
                        continue
                    else:
                        logger.error("Maximum retries reached. Falling back to local processing.")
                        raise requests.exceptions.RequestException("Service unavailable after maximum retries")
                
                # Check for token limit errors
                if response.status_code == 400:
                    error_text = response.text
                    logger.error(f"FinBERT API request failed with 400 error: {error_text}")
                    
                    if "token" in error_text.lower() and "limit" in error_text.lower():
                        # If it's a token limit issue, try to reduce the input size
                        if len(text) > 512:  # Typical BERT token limit
                            # Reduce input size by half for the next attempt
                            reduced_text = text[:len(text)//2]
                            logger.info(f"Reduced input size to {len(reduced_text)} characters for next attempt")
                            return self._call_finbert_api(reduced_text, max_retries - attempt - 1)
                
                # Raise exception for other errors
                response.raise_for_status()
                
                # Log successful response
                logger.info(f"FinBERT API call successful")
                return response.json()
            
            except requests.exceptions.RequestException as e:
                logger.error(f"FinBERT API request failed (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    raise
                sleep(1)  # Wait before retrying
        
        raise Exception("Failed to get response from FinBERT API after multiple attempts")
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks for processing, respecting token limits."""
        if not text:
            return []
        
        # For BERT models, typical token limit is 512 tokens
        # We'll use a conservative estimate of 400 tokens per chunk
        # Assuming average of 4 characters per token for English text
        char_per_token = 4
        char_limit = 400 * char_per_token  # ~1600 characters per chunk
        
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
            
            chunks.append(text[start:end])
            
            # Calculate next start position with overlap
            overlap = min(self.overlap_size, char_limit // 10)  # 10% overlap by default
            start = end - overlap if end - overlap > start else end
        
        logger.info(f"Split text into {len(chunks)} chunks for FinBERT processing")
        return chunks
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment in text using FinBERT model or fallback method."""
        try:
            if self.is_api_key_valid:
                # Use only the first 1000 characters for sentiment analysis
                # This is typically enough for overall sentiment and avoids token limits
                limited_text = text[:1000]
                
                # Call FinBERT API
                response = self._call_finbert_api(limited_text)
                
                # Process FinBERT response
                # Expected format: [{'label': 'positive/negative/neutral', 'score': 0.XXX}]
                if isinstance(response, list) and len(response) > 0:
                    # Get the first prediction (highest confidence)
                    prediction = response[0]
                    sentiment = prediction.get('label', 'neutral').lower()
                    score = prediction.get('score', 0.0)
                    
                    # Format explanation based on confidence score
                    if score > 0.8:
                        confidence = "high"
                    elif score > 0.6:
                        confidence = "moderate"
                    else:
                        confidence = "low"
                        
                    explanation = f"FinBERT model detected {sentiment} sentiment with {confidence} confidence ({score:.2f})."
                    
                    return {
                        "sentiment": sentiment,
                        "explanation": explanation,
                        "score": score
                    }
                else:
                    logger.warning(f"Unexpected FinBERT response format: {response}")
                    return self._fallback_sentiment_analysis(text)
            else:
                # Fallback to simple keyword-based sentiment analysis
                return self._fallback_sentiment_analysis(text)
        except Exception as e:
            logger.error(f"Error analyzing sentiment with FinBERT: {str(e)}")
            return self._fallback_sentiment_analysis(text)
    
    def _fallback_sentiment_analysis(self, text: str) -> Dict[str, Any]:
        """Simple keyword-based sentiment analysis as fallback."""
        text_lower = text.lower()
        
        positive_words = ['growth', 'increase', 'profit', 'success', 'positive', 'opportunity', 
                         'improve', 'gain', 'strong', 'advantage', 'innovation', 'progress']
        negative_words = ['decline', 'decrease', 'loss', 'risk', 'negative', 'challenge', 
                         'difficult', 'weak', 'threat', 'problem', 'failure', 'concern']
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
            explanation = "The text contains more positive financial keywords than negative ones."
            score = min(0.5 + (positive_count - negative_count) * 0.05, 0.9)  # Scale to 0.5-0.9
        elif negative_count > positive_count:
            sentiment = "negative"
            explanation = "The text contains more negative financial keywords than positive ones."
            score = min(0.5 + (negative_count - positive_count) * 0.05, 0.9)  # Scale to 0.5-0.9
        else:
            sentiment = "neutral"
            explanation = "The text contains a balanced mix of positive and negative financial keywords."
            score = 0.5
        
        return {
            "sentiment": sentiment,
            "explanation": explanation,
            "score": score
        }
    
    def extract_financial_metrics(self, text: str) -> List[Dict[str, Any]]:
        """Extract financial metrics from text using FinBERT insights and regex patterns."""
        try:
            # First, try to extract metrics using regex patterns
            regex_metrics = self._extract_metrics_with_regex(text)
            
            # If we have a valid API key, enhance with FinBERT
            if self.is_api_key_valid:
                # Process text in chunks to avoid token limits
                chunks = self._chunk_text(text)
                all_metrics = list(regex_metrics)  # Start with regex metrics
                
                # Process first few chunks (financial highlights usually at beginning)
                for i, chunk in enumerate(chunks[:3]):
                    try:
                        # Call FinBERT API
                        response = self._call_finbert_api(chunk)
                        
                        # Use FinBERT sentiment to validate and enhance metrics
                        if isinstance(response, list) and len(response) > 0:
                            sentiment = response[0].get('label', 'neutral').lower()
                            
                            # Add sentiment context to metrics from this section
                            for metric in regex_metrics:
                                if "context" in metric and metric["context"] in chunk:
                                    metric["sentiment"] = sentiment
                            
                            # If positive sentiment, mark metrics as more reliable
                            if sentiment == "positive":
                                for metric in regex_metrics:
                                    if "context" in metric and metric["context"] in chunk:
                                        metric["reliability"] = "high"
                    except Exception as chunk_error:
                        logger.error(f"Error processing chunk {i} with FinBERT: {str(chunk_error)}")
                
                return all_metrics
            else:
                # If no valid API key, just return regex metrics
                return regex_metrics
                
        except Exception as e:
            logger.error(f"Error extracting financial metrics: {str(e)}")
            # Fallback to regex pattern matching
            return self._extract_metrics_with_regex(text)
    
    def _determine_metric_name(self, name: str, context: str) -> str:
        """Determine the standardized name for a financial metric based on context."""
        name_lower = name.lower()
        logger.debug(f"Determining metric name for: {name_lower}")
        
        # EPS metrics - check this first to catch "earnings per share" before it matches "earnings" in profit
        if 'eps' in name_lower or ('earning' in name_lower and 'per share' in name_lower):
            logger.debug(f"Matched EPS category: 'eps' in name: {'eps' in name_lower}, 'earning' and 'per share' in name: {('earning' in name_lower and 'per share' in name_lower)}")
            if 'diluted' in name_lower:
                return 'Diluted EPS'
            else:
                return 'EPS'
        
        # Revenue metrics
        elif any(term in name_lower for term in ['revenue', 'sales', 'turnover']):
            logger.debug(f"Matched revenue category")
            if 'net' in name_lower:
                return 'Net Revenue'
            elif 'gross' in name_lower:
                return 'Gross Revenue'
            elif 'total' in name_lower:
                return 'Total Revenue'
            else:
                return 'Revenue'
        
        # Profit metrics
        elif any(term in name_lower for term in ['profit', 'income', 'earnings']):
            logger.debug(f"Matched profit category")
            if 'net' in name_lower:
                return 'Net Income'
            elif 'gross' in name_lower:
                return 'Gross Profit'
            elif 'operating' in name_lower:
                return 'Operating Income'
            else:
                return 'Profit'
        
        # Asset metrics
        elif 'asset' in name_lower:
            logger.debug(f"Matched asset category")
            if 'total' in name_lower:
                return 'Total Assets'
            else:
                return 'Assets'
        
        # Liability metrics
        elif 'liabilit' in name_lower:
            logger.debug(f"Matched liability category")
            if 'total' in name_lower:
                return 'Total Liabilities'
            else:
                return 'Liabilities'
        
        # Cash metrics
        elif 'cash' in name_lower:
            logger.debug(f"Matched cash category")
            if 'flow' in name_lower:
                return 'Cash Flow'
            else:
                return 'Cash'
        
        # Growth metrics
        elif 'growth' in name_lower:
            logger.debug(f"Matched growth category")
            if 'revenue' in name_lower or 'sales' in name_lower:
                return 'Revenue Growth'
            else:
                return 'Growth'
        
        # Margin metrics
        elif 'margin' in name_lower:
            logger.debug(f"Matched margin category")
            if 'gross' in name_lower:
                return 'Gross Margin'
            elif 'operating' in name_lower:
                return 'Operating Margin'
            elif 'net' in name_lower:
                return 'Net Margin'
            else:
                return 'Margin'
        
        # Return metrics
        elif 'return' in name_lower or 'roi' in name_lower or 'roe' in name_lower or 'roa' in name_lower:
            logger.debug(f"Matched return category")
            if 'equity' in name_lower or 'roe' in name_lower:
                return 'ROE'
            elif 'asset' in name_lower or 'roa' in name_lower:
                return 'ROA'
            elif 'investment' in name_lower or 'roi' in name_lower:
                return 'ROI'
            else:
                return 'Return'
        
        # Market cap
        elif 'market' in name_lower and ('cap' in name_lower or 'capitalization' in name_lower):
            logger.debug(f"Matched market cap category")
            return 'Market Cap'
        
        # Dividend metrics
        elif 'dividend' in name_lower:
            logger.debug(f"Matched dividend category")
            if 'yield' in name_lower:
                return 'Dividend Yield'
            else:
                return 'Dividend'
        
        # Default: return the original name with first letter capitalized
        return name.strip().capitalize()
    
    def _standardize_unit(self, unit: str) -> str:
        """Standardize unit format."""
        if not unit:
            return ""
            
        unit_lower = unit.lower()
        
        # Handle currency units
        if 'million' in unit_lower or 'm' == unit_lower:
            return 'million'
        elif 'billion' in unit_lower or 'b' == unit_lower:
            return 'billion'
        elif 'trillion' in unit_lower or 't' == unit_lower:
            return 'trillion'
        
        # Handle percentage
        elif '%' in unit_lower or 'percent' in unit_lower:
            return '%'
        
        # Handle currency symbols
        elif '$' in unit or 'usd' in unit_lower:
            return 'USD'
        elif '€' in unit or 'eur' in unit_lower:
            return 'EUR'
        elif '£' in unit or 'gbp' in unit_lower:
            return 'GBP'
        
        # Return original if no match
        return unit.strip()
    
    def _determine_category(self, category: str) -> str:
        """Determine the category of a financial metric."""
        # Map raw categories to standardized categories
        category_map = {
            'revenue': 'income_statement',
            'profit': 'income_statement',
            'eps': 'income_statement',
            'income': 'income_statement',
            'margin': 'profitability',
            'growth': 'growth',
            'assets': 'balance_sheet',
            'liabilities': 'balance_sheet',
            'equity': 'balance_sheet',
            'cash_flow': 'cash_flow',
            'return': 'profitability',
            'dividend': 'shareholder_returns',
            'market_cap': 'valuation'
        }
        
        # Return mapped category or default to 'financial'
        return category_map.get(category.lower(), 'financial')
    
    def _extract_metrics_with_regex(self, text: str) -> List[Dict[str, Any]]:
        """Extract financial metrics using regex patterns."""
        metrics = []
        
        # Debug: Print the text we're analyzing
        logger.debug(f"Analyzing text for metrics (length: {len(text)})")
        logger.debug(f"Text sample: {text[:200]}...")
        
        # Define regex patterns for different financial metrics
        patterns = {
            'revenue': [
                r'(?:total|net|annual)?\s*revenue\s*(?:of|:|\s+was|\s+is|\s+reached)?\s*(?:\$|€|£)?(\d[\d\.,]+)\s*(million|billion|trillion|m|b|t|USD|EUR|GBP)?',
                r'(?:total|net|annual)?\s*sales\s*(?:of|:|\s+was|\s+is|\s+reached)?\s*(?:\$|€|£)?(\d[\d\.,]+)\s*(million|billion|trillion|m|b|t|USD|EUR|GBP)?'
            ],
            'profit': [
                r'(?:net|gross|operating)?\s*(?:income|profit|earnings)\s*(?:of|:|\s+was|\s+is|\s+reached)?\s*(?:\$|€|£)?(\d[\d\.,]+)\s*(million|billion|trillion|m|b|t|USD|EUR|GBP)?',
                r'(?:net|gross|operating)?\s*(?:income|profit|earnings)\s*(?:of|:|\s+was|\s+is|\s+reached)?\s*(?:\$|€|£)?(\d[\d\.,]+)\s*(million|billion|trillion|m|b|t|USD|EUR|GBP)?'
            ],
            'eps': [
                r'(?:diluted|basic)?\s*(?:earnings per share|EPS)(?:\s*\(EPS\))?\s*(?:of|:|\s+was|\s+is|\s+reached|compared to)?\s*(?:\$|€|£)?(\d[\d\.,]+)',
                r'(?:diluted|basic)?\s*(?:EPS|earnings per share)\s*(?:of|:|\s+was|\s+is|\s+reached)?\s*(?:\$|€|£)?(\d[\d\.,]+)',
                r'EPS\s*(?::|was|of|\(diluted\))?\s*(?:\$|€|£)?(\d[\d\.,]+)',
                r'earnings per share\s*\(eps\):\s*(?:\$|€|£)?(\d[\d\.,]+)'
            ],
            'assets': [
                r'(?:total)?\s*assets\s*(?:of|:|\s+was|\s+is|\s+reached)?\s*(?:\$|€|£)?(\d[\d\.,]+)\s*(million|billion|trillion|m|b|t|USD|EUR|GBP)?'
            ],
            'liabilities': [
                r'(?:total)?\s*liabilities\s*(?:of|:|\s+was|\s+is|\s+reached)?\s*(?:\$|€|£)?(\d[\d\.,]+)\s*(million|billion|trillion|m|b|t|USD|EUR|GBP)?'
            ],
            'market_cap': [
                r'(?:market\s*cap|market\s*capitalization)\s*(?:of|:|\s+was|\s+is|\s+reached)?\s*(?:\$|€|£)?(\d[\d\.,]+)\s*(million|billion|trillion|m|b|t|USD|EUR|GBP)?'
            ],
            'growth': [
                r'(?:revenue|sales|profit|income)?\s*growth\s*(?:of|:|\s+was|\s+is|\s+at)?\s*(\d[\d\.,]+)\s*(%|percent)',
                r'(?:grew|increased|decreased)\s*by\s*(\d[\d\.,]+)\s*(%|percent)'
            ],
            'margin': [
                r'(?:gross|operating|net|profit)?\s*margin\s*(?:of|:|\s+was|\s+is|\s+at)?\s*(\d[\d\.,]+)\s*(%|percent)'
            ],
            'dividend': [
                r'dividend\s*(?:of|:|\s+was|\s+is|\s+at)?\s*(?:\$|€|£)?(\d[\d\.,]+)\s*(per\s*share|USD|EUR|GBP)?',
                r'dividend\s*yield\s*(?:of|:|\s+was|\s+is|\s+at)?\s*(\d[\d\.,]+)\s*(%|percent)'
            ],
            'cash_flow': [
                r'(?:operating|free)?\s*cash\s*flow\s*(?:of|:|\s+was|\s+is|\s+reached)?\s*(?:\$|€|£)?(\d[\d\.,]+)\s*(million|billion|trillion|m|b|t|USD|EUR|GBP)?'
            ],
            'return': [
                r'(?:return\s*on\s*(?:equity|assets|investment)|ROE|ROA|ROI)\s*(?:of|:|\s+was|\s+is|\s+at)?\s*(\d[\d\.,]+)\s*(%|percent)',
                r'return\s*on\s*equity\s*\(roe\):\s*(\d[\d\.,]+)\s*(%|percent)?'
            ]
        }
        
        # Log the patterns we're searching for
        logger.debug(f"Searching for {len(patterns)} types of financial metrics")
        
        # Search for each pattern in the text
        for category, category_patterns in patterns.items():
            for pattern in category_patterns:
                logger.debug(f"Trying pattern for {category}: {pattern}")
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    logger.debug(f"Found match for {category}: {match.group(0)}")
                    # Extract the value and unit
                    value = match.group(1).replace(',', '')
                    unit = ""
                    if match.lastindex and match.lastindex > 1:
                        unit = match.group(2) if match.group(2) else ""
                    
                    # Get the context (text around the match)
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end]
                    
                    # Determine metric name based on match and context
                    full_match_text = match.group(0)
                    logger.debug(f"Full match text for {category}: {full_match_text}")
                    # For EPS, use the full match text to determine the name
                    if 'eps' in full_match_text.lower() or ('earnings' in full_match_text.lower() and 'per share' in full_match_text.lower()):
                        logger.debug(f"Using full match text for EPS: {full_match_text}")
                        metric_name = self._determine_metric_name(full_match_text, context)
                    else:
                        # For other metrics, use the first word as before
                        logger.debug(f"Using first word for {category}: {full_match_text.split()[0]}")
                        metric_name = self._determine_metric_name(full_match_text.split()[0], context)
                    
                    logger.debug(f"Determined metric name: {metric_name}")
                    
                    # Standardize unit format
                    standardized_unit = self._standardize_unit(unit)
                    
                    # Create metric object
                    metric = {
                        "name": metric_name,
                        "value": value,
                        "unit": standardized_unit,
                        "category": self._determine_category(category),
                        "context": context
                    }
                    
                    metrics.append(metric)
                    logger.debug(f"Found metric: {metric_name} = {value} {standardized_unit}")
        
        # Look for table-like patterns (e.g., "Revenue | $10.5B")
        table_pattern = r'([A-Za-z\s]+)\s*[\|\:\t]\s*(?:\$|€|£)?(\d[\d\.,]+)\s*(million|billion|trillion|m|b|t|USD|EUR|GBP|%|percent)?'
        table_matches = re.finditer(table_pattern, text)
        
        for match in table_matches:
            name = match.group(1).strip()
            value = match.group(2).replace(',', '')
            unit = match.group(3) if match.group(3) else ""
            
            # Skip if name is too short or generic
            if len(name) < 3 or name.lower() in ['the', 'and', 'for', 'year', 'quarter', 'period']:
                continue
                
            # Get context
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            context = text[start:end]
            
            # Determine category based on name
            category = "financial"
            for cat_name, cat_patterns in patterns.items():
                if any(term in name.lower() for term in cat_name.split('_')):
                    category = cat_name
                    break
            
            # Create metric object
            metric = {
                "name": self._determine_metric_name(name, context),
                "value": value,
                "unit": self._standardize_unit(unit),
                "category": self._determine_category(category),
                "context": context
            }
            
            metrics.append(metric)
        
        logger.info(f"Extracted {len(metrics)} financial metrics using regex patterns")
        return metrics
    
    def extract_risk_factors(self, text: str) -> List[str]:
        """Extract risk factors from text using FinBERT model or pattern matching."""
        try:
            # First try to extract risk factors using regex patterns
            regex_risks = self._extract_risks_with_regex(text)
            
            # If we have a valid API key, enhance with FinBERT
            if self.is_api_key_valid:
                # Process text in chunks to avoid token limits
                chunks = self._chunk_text(text)
                all_risks = list(regex_risks)  # Start with regex risks
                
                # Process chunks (focus on middle sections where risks are typically found)
                start_idx = min(3, len(chunks) // 3)  # Skip first few chunks (usually intro)
                end_idx = min(start_idx + 5, len(chunks))  # Process ~5 chunks in the middle
                
                for i, chunk in enumerate(chunks[start_idx:end_idx]):
                    try:
                        # Call FinBERT API
                        response = self._call_finbert_api(chunk)
                        
                        # Use FinBERT sentiment to identify potential risk sections
                        if isinstance(response, list) and len(response) > 0:
                            sentiment = response[0].get('label', 'neutral').lower()
                            score = response[0].get('score', 0.0)
                            
                            # Negative sentiment sections are more likely to contain risks
                            if sentiment == "negative" and score > 0.6:
                                # Extract sentences that might contain risks
                                sentences = re.split(r'(?<=[.!?])\s+', chunk)
                                for sentence in sentences:
                                    # Look for risk-related keywords in sentences
                                    if any(keyword in sentence.lower() for keyword in [
                                        'risk', 'threat', 'challenge', 'uncertainty', 'concern',
                                        'adverse', 'negative', 'decline', 'decrease', 'loss',
                                        'litigation', 'regulatory', 'compliance', 'failure'
                                    ]):
                                        # Clean up the sentence
                                        risk = sentence.strip()
                                        if risk and len(risk) > 20 and risk not in all_risks:
                                            all_risks.append(risk)
                    except Exception as chunk_error:
                        logger.error(f"Error processing chunk {i} with FinBERT for risk extraction: {str(chunk_error)}")
                
                return all_risks
            else:
                # If no valid API key, just return regex risks
                return regex_risks
                
        except Exception as e:
            logger.error(f"Error extracting risk factors: {str(e)}")
            # Fallback to regex pattern matching
            return self._extract_risks_with_regex(text)
    
    def _extract_risks_with_regex(self, text: str) -> List[str]:
        """Extract risk factors using regex patterns."""
        risks = []
        
        # Look for sections that might contain risk factors
        risk_section_patterns = [
            r'(?i)Risk\s+Factors.*?(?=\n\n\w+|\Z)',
            r'(?i)Risks\s+and\s+Uncertainties.*?(?=\n\n\w+|\Z)',
            r'(?i)Principal\s+Risks.*?(?=\n\n\w+|\Z)',
            r'(?i)Key\s+Risks.*?(?=\n\n\w+|\Z)'
        ]
        
        # Extract risk sections
        risk_sections = []
        for pattern in risk_section_patterns:
            matches = re.finditer(pattern, text, re.DOTALL)
            for match in matches:
                risk_sections.append(match.group(0))
        
        # If we found risk sections, extract individual risks
        if risk_sections:
            combined_section = "\n".join(risk_sections)
            
            # Extract bullet points or numbered items
            bullet_patterns = [
                r'•\s*(.*?)(?=•|\n\n|\Z)',
                r'[\n\r]\d+\.\s*(.*?)(?=[\n\r]\d+\.|\n\n|\Z)',
                r'[\n\r][-–]\s*(.*?)(?=[\n\r][-–]|\n\n|\Z)'
            ]
            
            for pattern in bullet_patterns:
                matches = re.finditer(pattern, combined_section, re.DOTALL)
                for match in matches:
                    risk = match.group(1).strip()
                    if risk and len(risk) > 20 and risk not in risks:  # Avoid short or duplicate entries
                        risks.append(risk)
        
        # If no structured risk sections found, look for sentences containing risk keywords
        if not risks:
            sentences = re.split(r'(?<=[.!?])\s+', text)
            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in [
                    'risk', 'threat', 'challenge', 'uncertainty', 'concern',
                    'adverse', 'negative', 'decline', 'decrease', 'loss',
                    'litigation', 'regulatory', 'compliance', 'failure'
                ]):
                    risk = sentence.strip()
                    if risk and len(risk) > 20 and risk not in risks:
                        risks.append(risk)
        
        logger.info(f"Extracted {len(risks)} risk factors using regex patterns")
        return risks[:10]  # Limit to top 10 risks
    
    def generate_business_outlook(self, text: str) -> str:
        """Generate a business outlook summary using Hugging Face or fallback method."""
        try:
            if self.text_generation:
                prompt = f"Summarize the business outlook, strategic plans, and growth expectations from this text: {text[:1000]}"
                
                response = self.text_generation(prompt, max_length=300, do_sample=False)[0]['generated_text']
                return response.strip()
            else:
                # Fallback to extractive method
                return self._extract_outlook_statements(text)
                
        except Exception as e:
            logger.error(f"Error generating business outlook: {str(e)}")
            return self._extract_outlook_statements(text)
    
    def _extract_outlook_statements(self, text: str) -> str:
        """Extract outlook statements using pattern matching."""
        outlook_statements = []
        
        # Look for outlook section
        outlook_section_pattern = r'(?i)(Outlook|Future Prospects|Forward-Looking Statements|Strategic Priorities|Future Plans).*?(?=\n\s*\n|$)'
        outlook_section_match = re.search(outlook_section_pattern, text, re.DOTALL)
        
        if outlook_section_match:
            outlook_section = outlook_section_match.group(0)
            sentences = re.split(r'(?<=[.!?])\s+', outlook_section)
            outlook_statements = sentences[:5]  # Take first 5 sentences
        
        # If no structured outlook found, look for outlook-related sentences
        if not outlook_statements:
            sentences = re.split(r'(?<=[.!?])\s+', text)
            for sentence in sentences:
                if len(sentence) > 30 and any(word in sentence.lower() for word in ['future', 'plan', 'expect', 'strategy', 'growth', 'outlook', 'anticipate']):
                    outlook_statements.append(sentence.strip())
                    if len(outlook_statements) >= 5:
                        break
        
        return " ".join(outlook_statements)
    
    def answer_question(self, question: str, context: str) -> str:
        """Answer a specific question based on the provided context."""
        try:
            if self.qa_pipeline:
                result = self.qa_pipeline(question=question, context=context[:self.chunk_size])
                return result['answer']
            else:
                # Simple fallback
                return "Question answering is not available without the Hugging Face model."
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            return "Error processing question."
    
    def generate_summary(self, text: str, summary_type: str = "executive") -> str:
        """Generate a summary of the text using FinBERT insights."""
        try:
            if not self.is_api_key_valid:
                logger.warning("No valid API key for FinBERT, using fallback summary method")
                return self._fallback_summary(text, summary_type)
            
            # Limit text to first 2000 characters for executive summary
            # or middle 2000 characters for business outlook
            if summary_type == "executive":
                text_to_summarize = text[:2000]
                prompt = "Provide a concise executive summary of this financial report section:"
            else:  # business outlook
                # Take text from middle of document for business outlook
                middle_start = max(0, len(text) // 3)
                middle_end = min(len(text), middle_start + 2000)
                text_to_summarize = text[middle_start:middle_end]
                prompt = "Summarize the business outlook and future prospects from this financial report section:"
            
            # We'll use FinBERT for sentiment analysis, but need to create our own summary
            # based on key sentences from the text
            
            # First, get sentiment from FinBERT
            sentiment_result = self.analyze_sentiment(text_to_summarize)
            sentiment = sentiment_result["sentiment"]
            
            # Extract key sentences based on financial keywords
            sentences = re.split(r'(?<=[.!?])\s+', text_to_summarize)
            key_sentences = []
            
            # Keywords relevant to financial reports
            financial_keywords = [
                'revenue', 'profit', 'growth', 'increase', 'decrease', 'market',
                'sales', 'earnings', 'performance', 'outlook', 'forecast',
                'strategy', 'investment', 'dividend', 'shareholder', 'future',
                'expansion', 'acquisition', 'innovation', 'technology', 'competitive'
            ]
            
            # Score sentences based on keyword presence
            scored_sentences = []
            for sentence in sentences:
                if len(sentence.split()) < 5:  # Skip very short sentences
                    continue
                    
                score = sum(1 for keyword in financial_keywords if keyword in sentence.lower())
                if score > 0:
                    scored_sentences.append((sentence, score))
            
            # Sort by score and take top sentences
            scored_sentences.sort(key=lambda x: x[1], reverse=True)
            key_sentences = [s[0] for s in scored_sentences[:5]]
            
            # Create summary
            if key_sentences:
                summary = " ".join(key_sentences)
                
                # Add sentiment context
                if sentiment == "positive":
                    summary += " Overall, the report indicates a positive financial outlook."
                elif sentiment == "negative":
                    summary += " Overall, the report indicates some financial challenges ahead."
                else:
                    summary += " Overall, the report presents a balanced financial picture."
                
                return summary
            else:
                return self._fallback_summary(text, summary_type)
                
        except Exception as e:
            logger.error(f"Error generating {summary_type} summary: {str(e)}")
            return self._fallback_summary(text, summary_type)
    
    def _fallback_summary(self, text: str, summary_type: str) -> str:
        """Generate a simple extractive summary as fallback."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        if len(sentences) <= 3:
            return text
        
        if summary_type == "executive":
            # For executive summary, take first 2 sentences and last sentence
            summary = " ".join(sentences[:2] + [sentences[-1]])
        else:  # business outlook
            # For business outlook, look for sentences with future-oriented terms
            future_terms = ['will', 'plan', 'expect', 'future', 'outlook', 'forecast', 
                           'anticipate', 'strategy', 'growth', 'target', 'goal']
            
            future_sentences = []
            for sentence in sentences:
                if any(term in sentence.lower() for term in future_terms):
                    future_sentences.append(sentence)
            
            if future_sentences:
                summary = " ".join(future_sentences[:3])  # Take up to 3 future-oriented sentences
            else:
                # Fallback to middle and last sentences
                middle_idx = len(sentences) // 2
                summary = " ".join([sentences[middle_idx], sentences[-1]])
        
        return summary
    
    def analyze_report_text(self, text: str) -> Dict[str, Any]:
        """Analyze report text using FinBERT model and extract insights."""
        if not text:
            logger.warning("Empty text provided for analysis")
            return {
                "status": "error",
                "message": "No text provided for analysis",
                "metrics": [],
                "risks": [],
                "executive_summary": "",
                "business_outlook": "",
                "sentiment": {"sentiment": "neutral", "explanation": "No text to analyze"}
            }
        
        logger.info(f"Starting analysis of report text ({len(text)} characters)")
        
        # Track component errors for graceful degradation
        component_errors = {
            "metrics": False,
            "risks": False,
            "executive_summary": False,
            "business_outlook": False,
            "sentiment": False
        }
        
        # Split text into chunks for processing
        chunks = self._chunk_text(text)
        logger.info(f"Split report into {len(chunks)} chunks for analysis")
        
        # Extract financial metrics (from first few chunks)
        metrics = []
        try:
            metrics = self.extract_financial_metrics(text)
            logger.info(f"Extracted {len(metrics)} financial metrics")
            
            # Deduplicate metrics by name
            unique_metrics = {}
            for metric in metrics:
                name = metric.get("name", "").lower()
                if name and (name not in unique_metrics or 
                           float(metric.get("value", 0)) > float(unique_metrics[name].get("value", 0))):
                    unique_metrics[name] = metric
            
            metrics = list(unique_metrics.values())
        except Exception as e:
            logger.error(f"Error extracting financial metrics: {str(e)}")
            component_errors["metrics"] = True
        
        # Extract risk factors (from middle chunks)
        risks = []
        try:
            risks = self.extract_risk_factors(text)
            logger.info(f"Extracted {len(risks)} risk factors")
        except Exception as e:
            logger.error(f"Error extracting risk factors: {str(e)}")
            component_errors["risks"] = True
        
        # Generate executive summary
        executive_summary = ""
        try:
            executive_summary = self.generate_summary(text, "executive")
            logger.info(f"Generated executive summary ({len(executive_summary)} characters)")
        except Exception as e:
            logger.error(f"Error generating executive summary: {str(e)}")
            component_errors["executive_summary"] = True
        
        # Generate business outlook
        business_outlook = ""
        try:
            business_outlook = self.generate_summary(text, "business")
            logger.info(f"Generated business outlook ({len(business_outlook)} characters)")
        except Exception as e:
            logger.error(f"Error generating business outlook: {str(e)}")
            component_errors["business_outlook"] = True
        
        # Analyze sentiment (based on executive summary)
        sentiment = {"sentiment": "neutral", "explanation": "Unable to determine sentiment"}
        try:
            sentiment = self.analyze_sentiment(executive_summary or text[:1000])
            logger.info(f"Analyzed sentiment: {sentiment['sentiment']}")
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            component_errors["sentiment"] = True
        
        # Determine overall status
        status = "success"
        message = "Analysis completed successfully"
        
        if all(component_errors.values()):
            status = "error"
            message = "All analysis components failed"
        elif any(component_errors.values()):
            status = "partial"
            failed_components = [comp for comp, failed in component_errors.items() if failed]
            message = f"Partial analysis completed. Failed components: {', '.join(failed_components)}"
        
        return {
            "status": status,
            "message": message,
            "metrics": metrics,
            "risks": risks,
            "executive_summary": executive_summary,
            "business_outlook": business_outlook,
            "sentiment": sentiment
        }
    
    def analyze_report(self, report_text: str) -> Dict[str, Any]:
        """Analyze a financial report and extract insights."""
        start_time = time.time()
        logger.info(f"Starting report analysis ({len(report_text)} characters)")
        
        try:
            # Check if API key is valid
            if not self.is_api_key_valid:
                logger.warning("No valid Hugging Face API key. Using fallback methods.")
            
            # Analyze the report text
            analysis_result = self.analyze_report_text(report_text)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            logger.info(f"Report analysis completed in {processing_time:.2f} seconds")
            
            # Add processing metadata
            analysis_result["processing_time"] = f"{processing_time:.2f} seconds"
            analysis_result["processing_date"] = datetime.now().isoformat()
            analysis_result["model_used"] = "matna449/my-finbert" if self.is_api_key_valid else "fallback methods"
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing report: {str(e)}")
            processing_time = time.time() - start_time
            
            # Return error result with as much information as possible
            return {
                "status": "error",
                "message": f"Error analyzing report: {str(e)}",
                "metrics": [],
                "risks": [],
                "executive_summary": "",
                "business_outlook": "",
                "sentiment": {"sentiment": "neutral", "explanation": "Analysis failed"},
                "processing_time": f"{processing_time:.2f} seconds",
                "processing_date": datetime.now().isoformat(),
                "model_used": "matna449/my-finbert" if self.is_api_key_valid else "fallback methods"
            }
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks for processing, respecting token limits."""
        if not text:
            return []
        
        # For BERT models, typical token limit is 512 tokens
        # We'll use a conservative estimate of 400 tokens per chunk
        # Assuming average of 4 characters per token for English text
        char_per_token = 4
        char_limit = 400 * char_per_token  # ~1600 characters per chunk
        
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
            
            chunks.append(text[start:end])
            
            # Calculate next start position with overlap
            overlap = min(self.overlap_size, char_limit // 10)  # 10% overlap by default
            start = end - overlap if end - overlap > start else end
        
        logger.info(f"Split text into {len(chunks)} chunks for FinBERT processing")
        return chunks 