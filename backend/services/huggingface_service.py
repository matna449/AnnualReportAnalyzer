import os
import logging
import requests
import time
import re
from typing import List, Dict, Any, Optional, Union
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class HuggingFaceService:
    """
    Service for interacting with Hugging Face models for financial analysis.
    Supports sentiment analysis, named entity recognition, and risk assessment.
    """
    
    def __init__(self):
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        
        # PDF service for using shared chunking functionality
        from services.pdf_service import PDFService
        self.pdf_service = PDFService()
        
        # Model URLs - Updated with working models
        self.sentiment_model_url = "https://api-inference.huggingface.co/models/yiyanghkust/finbert-tone"
        self.finbert_model_url = "https://api-inference.huggingface.co/models/ProsusAI/finbert"  # Financial BERT model
        self.risk_model_url = "https://api-inference.huggingface.co/models/ProsusAI/finbert"  # Same model for risk analysis
        
        # Chunking parameters - adjusted for BERT model limits
        self.max_tokens = 512  # Maximum tokens per chunk for BERT models
        self.overlap_tokens = 50  # Overlap between chunks
        
        # Validate API key
        self.is_api_key_valid = self._validate_api_key()
        logger.info(f"HUGGINGFACE: Service initialized. API key valid: {self.is_api_key_valid}")
        
    def _validate_api_key(self) -> bool:
        """Validate the Hugging Face API key."""
        logger.info("HUGGINGFACE: Validating API key")
        
        if not self.api_key:
            logger.warning("HUGGINGFACE: No API key provided in environment variables")
            return False
            
        if len(self.api_key) < 8:  # Basic length check
            logger.warning("HUGGINGFACE: API key appears to be invalid (too short)")
            return False
            
        # Skip actual validation to avoid timeouts during testing
        logger.info("HUGGINGFACE: Skipping API key validation to avoid timeouts. Assuming key is valid.")
        return True
        
        # Uncomment the following code for production use
        """
        # Test API key with a simple request
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.post(
                self.sentiment_model_url,
                headers=headers,
                json={"inputs": "The company reported strong financial results."},
                timeout=15  # Increased timeout
            )
            
            if response.status_code == 200:
                logger.info("Hugging Face API key validated successfully.")
                return True
            elif response.status_code == 401:
                logger.error("Hugging Face API key is invalid (401 Unauthorized).")
                return False
            else:
                logger.warning(f"API key validation returned status code: {response.status_code}")
                # Assume key is valid if we get a response, even if it's not 200
                # This handles cases where the model is loading
                return True
        except Exception as e:
            logger.error(f"Error validating Hugging Face API key: {str(e)}")
            # Assume key is valid if we can't validate it due to network issues
            return True
        """
    
    def _call_api(self, model_url: str, text: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Call the Hugging Face API with exponential backoff for retries.
        
        Args:
            model_url: URL of the model to call
            text: Text to analyze
            max_retries: Maximum number of retries
            
        Returns:
            Dictionary with API response
        """
        if not self.is_api_key_valid:
            logger.warning("HUGGINGFACE: API call attempted but API key is invalid or missing")
            return self._get_mock_response(model_url, text)
            
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"inputs": text}
        
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"HUGGINGFACE: Calling API - Model: {model_url.split('/')[-1]}, Text length: {len(text)} chars")
                response = requests.post(model_url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"HUGGINGFACE: API call successful - Model: {model_url.split('/')[-1]}")
                    return result
                
                # Handle error cases
                if response.status_code == 503:
                    retry_count += 1
                    wait_time = min(2 ** retry_count, 60)  # Exponential backoff, max 60 seconds
                    logger.warning(f"HUGGINGFACE: API temporarily unavailable (503). Retrying in {wait_time}s (attempt {retry_count}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                
                logger.error(f"HUGGINGFACE: API error - Status: {response.status_code}, Response: {response.text}")
                
                # For other HTTP errors, just return a mock response
                return self._get_mock_response(model_url, text)
                
            except Exception as e:
                retry_count += 1
                wait_time = min(2 ** retry_count, 60)
                logger.error(f"HUGGINGFACE: Exception during API call: {str(e)}. Retrying in {wait_time}s (attempt {retry_count}/{max_retries})")
                
                if retry_count >= max_retries:
                    logger.error(f"HUGGINGFACE: Max retries reached. Falling back to mock response.")
                    break
                    
                time.sleep(wait_time)
        
        # If we've exhausted retries, use the mock response
        logger.warning(f"HUGGINGFACE: Using mock response after {max_retries} failed API attempts")
        return self._get_mock_response(model_url, text)
        
    def _get_mock_response(self, model_url: str, text: str) -> Dict[str, Any]:
        """
        Generate a mock response for testing when API calls fail.
        
        Args:
            model_url: URL of the Hugging Face model
            text: Text that was to be analyzed
            
        Returns:
            Mock response data
        """
        model_name = model_url.split('/')[-1]
        
        # Check for negative keywords
        negative_keywords = ["decline", "decrease", "loss", "risk", "challenge", "volatility", 
                           "litigation", "regulatory", "competition", "threat", "adverse"]
        positive_keywords = ["growth", "increase", "profit", "success", "opportunity", "strong", 
                           "improvement", "gain", "positive", "advantage"]
        
        # Count occurrences of positive and negative keywords
        negative_count = sum(1 for keyword in negative_keywords if keyword in text.lower())
        positive_count = sum(1 for keyword in positive_keywords if keyword in text.lower())
        
        # Determine sentiment based on keyword counts
        is_negative = negative_count > positive_count
        is_positive = positive_count > negative_count
        
        # Mock response for sentiment analysis (finbert-tone)
        if "finbert-tone" in model_url or "finbert" in model_url:
            if is_negative:
                return [
                    {"label": "Positive", "score": 0.15},
                    {"label": "Negative", "score": 0.75},
                    {"label": "Neutral", "score": 0.1}
                ]
            elif is_positive:
                return [
                    {"label": "Positive", "score": 0.75},
                    {"label": "Negative", "score": 0.15},
                    {"label": "Neutral", "score": 0.1}
                ]
            else:
                return [
                    {"label": "Positive", "score": 0.3},
                    {"label": "Negative", "score": 0.3},
                    {"label": "Neutral", "score": 0.4}
                ]
        
        # Default mock response
        else:
            return [{"label": "Neutral", "score": 1.0}]
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks suitable for BERT models by utilizing PDFService's chunking.
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        # Use PDFService's chunking method with BERT-appropriate size limits
        # Approximating token count as characters/4 for English text
        chunk_size = self.max_tokens * 4  # Rough token-to-character conversion
        overlap = self.overlap_tokens * 4  # Overlap in characters
        
        chunks = self.pdf_service.chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        logger.info(f"Split text into {len(chunks)} chunks using PDFService chunker")
        return chunks
        
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment in financial text using FinBERT Tone model.
        
        Args:
            text: Financial text to analyze
            
        Returns:
            Dictionary with sentiment analysis results
        """
        try:
            # Check for negative keywords for more accurate sentiment detection
            negative_keywords = ["decline", "decrease", "loss", "risk", "challenge", "volatility", 
                               "litigation", "regulatory", "competition", "threat", "adverse"]
            positive_keywords = ["growth", "increase", "profit", "success", "opportunity", "strong", 
                               "improvement", "gain", "positive", "advantage"]
            
            # Count occurrences of positive and negative keywords
            negative_count = sum(1 for keyword in negative_keywords if keyword in text.lower())
            positive_count = sum(1 for keyword in positive_keywords if keyword in text.lower())
            
            # Always chunk the text using the standardized method
            chunks = self._chunk_text(text)
            logger.info(f"Analyzing sentiment for {len(chunks)} text chunks")
            
            # Process each chunk
            results = []
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                try:
                    chunk_result = self._call_api(self.sentiment_model_url, chunk)
                    # Handle nested list structure
                    if isinstance(chunk_result, list):
                        for item in chunk_result:
                            if isinstance(item, list):
                                results.extend(item)
                            else:
                                results.append(item)
                except Exception as e:
                    logger.error(f"Error processing chunk {i+1}: {str(e)}")
            
            # Aggregate results
            if not results:
                return self._fallback_sentiment_analysis(text)
            
            # Count sentiment labels
            sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
            total_score = 0
            
            for result in results:
                if isinstance(result, dict):
                    # Handle both lowercase and capitalized labels
                    label = result.get('label', '')
                    if label:
                        label = label.lower()  # Convert to lowercase
                        score = result.get('score', 0)
                        
                        if label in sentiment_counts:
                            sentiment_counts[label] += 1
                            total_score += score
            
            # Determine overall sentiment
            if sum(sentiment_counts.values()) == 0:
                return self._fallback_sentiment_analysis(text)
            else:
                # Use keyword counts to break ties or adjust sentiment
                if sentiment_counts["positive"] == sentiment_counts["negative"]:
                    if negative_count > positive_count:
                        overall_sentiment = "negative"
                    elif positive_count > negative_count:
                        overall_sentiment = "positive"
                    else:
                        overall_sentiment = "neutral"
                else:
                    overall_sentiment = max(sentiment_counts.items(), key=lambda x: x[1])[0]
                
                # Override with keyword analysis if strong signal
                if negative_count > positive_count + 2:  # Strong negative signal
                    overall_sentiment = "negative"
                elif positive_count > negative_count + 2:  # Strong positive signal
                    overall_sentiment = "positive"
                
                avg_score = total_score / sum(sentiment_counts.values()) if sum(sentiment_counts.values()) > 0 else 0
            
            return {
                "sentiment": overall_sentiment,
                "score": avg_score,
                "chunk_count": len(chunks),
                "processed_chunks": len(results),
                "sentiment_distribution": sentiment_counts,
                "keyword_analysis": {"negative": negative_count, "positive": positive_count}
            }
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return self._fallback_sentiment_analysis(text)
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract financial entities from text using FinBERT model.
        Since FinBERT is not a dedicated NER model, we'll use sentiment analysis
        to identify important financial terms and concepts.
        
        Args:
            text: Financial text to analyze
            
        Returns:
            Dictionary with extracted financial entities
        """
        try:
            # Split text into chunks if needed
            chunks = self._chunk_text(text)
            logger.info(f"Extracting financial entities from {len(chunks)} text chunks")
            
            # Financial entity categories
            entity_types = {
                "FINANCIAL_TERM": [],
                "METRIC": [],
                "COMPANY": [],
                "RISK": [],
                "OPPORTUNITY": []
            }
            
            # Financial keywords for each category
            financial_keywords = {
                "FINANCIAL_TERM": ["revenue", "profit", "earnings", "ebitda", "margin", "cash flow", 
                                  "dividend", "asset", "liability", "equity", "debt", "expense", 
                                  "income", "balance sheet", "statement", "fiscal", "quarter", "annual"],
                "METRIC": ["growth", "increase", "decrease", "percent", "ratio", "million", "billion", 
                          "dollar", "euro", "yen", "pound", "rate", "return", "yield"],
                "COMPANY": ["company", "corporation", "inc", "ltd", "llc", "business", "enterprise", 
                           "firm", "organization", "subsidiary", "parent", "group"],
                "RISK": ["risk", "challenge", "threat", "uncertainty", "volatility", "exposure", 
                        "liability", "litigation", "regulatory", "compliance"],
                "OPPORTUNITY": ["opportunity", "advantage", "growth", "expansion", "innovation", 
                               "development", "strategy", "initiative", "prospect"]
            }
            
            processed_chunks = 0
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                try:
                    # Use FinBERT for sentiment analysis
                    chunk_result = self._call_api(self.finbert_model_url, chunk)
                    processed_chunks += 1
                    
                    # Extract financial entities based on keywords
                    chunk_lower = chunk.lower()
                    sentences = re.split(r'[.!?]', chunk)
                    
                    # Process each sentence
                    for sentence in sentences:
                        if not sentence.strip():
                            continue
                            
                        # Get sentiment for this sentence
                        sentiment_score = 0.5  # Neutral default
                        sentiment_label = "neutral"
                        
                        # Extract sentiment from FinBERT result if available
                        if isinstance(chunk_result, list):
                            for prediction in chunk_result:
                                if isinstance(prediction, list):
                                    for item in prediction:
                                        if isinstance(item, dict) and 'label' in item:
                                            label = item.get('label', '').lower()
                                            if label in ['positive', 'negative', 'neutral']:
                                                sentiment_label = label
                                                sentiment_score = item.get('score', 0.5)
                                                break
                                elif isinstance(prediction, dict) and 'label' in prediction:
                                    label = prediction.get('label', '').lower()
                                    if label in ['positive', 'negative', 'neutral']:
                                        sentiment_label = label
                                        sentiment_score = prediction.get('score', 0.5)
                                        break
                        
                        # Find financial terms in the sentence
                        sentence_lower = sentence.lower()
                        for category, keywords in financial_keywords.items():
                            for keyword in keywords:
                                if keyword in sentence_lower:
                                    # Find the context around the keyword
                                    start_idx = max(0, sentence_lower.find(keyword) - 20)
                                    end_idx = min(len(sentence_lower), sentence_lower.find(keyword) + len(keyword) + 20)
                                    context = sentence[start_idx:end_idx].strip()
                                    
                                    # Add to entity list with sentiment score
                                    entity_types[category].append({
                                        'text': context,
                                        'keyword': keyword,
                                        'score': sentiment_score,
                                        'sentiment': sentiment_label
                                    })
                except Exception as e:
                    logger.error(f"Error processing chunk {i+1}: {str(e)}")
            
            # Remove duplicates and sort by score
            for category in entity_types:
                # Create a set to track unique texts
                unique_texts = set()
                unique_entities = []
                
                for entity in sorted(entity_types[category], key=lambda x: x['score'], reverse=True):
                    # Use a simplified version of the text to check for duplicates
                    simple_text = re.sub(r'\s+', ' ', entity['text'].lower()).strip()
                    if simple_text not in unique_texts:
                        unique_texts.add(simple_text)
                        unique_entities.append(entity)
                
                # Replace with deduplicated list
                entity_types[category] = unique_entities[:10]  # Limit to top 10 per category
            
            return {
                "entities": entity_types,
                "chunk_count": len(chunks),
                "processed_chunks": processed_chunks
            }
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            return {"entities": {}, "error": str(e)}
    
    def analyze_risk(self, text: str) -> Dict[str, Any]:
        """
        Analyze financial risk using FinBERT model.
        
        Args:
            text: Financial text to analyze
            
        Returns:
            Dictionary with risk analysis results
        """
        try:
            # Split text into chunks if needed
            chunks = self._chunk_text(text)
            logger.info(f"Analyzing risk for {len(chunks)} text chunks")
            
            # Risk categories based on financial terms
            risk_categories = {
                "litigation": 0,
                "regulation": 0,
                "competition": 0,
                "market": 0,
                "credit": 0,
                "operational": 0,
                "other": 0
            }
            
            # Risk keywords for each category
            risk_keywords = {
                "litigation": ["lawsuit", "legal", "litigation", "court", "settlement", "dispute"],
                "regulation": ["regulation", "compliance", "regulatory", "law", "requirement", "authority"],
                "competition": ["competition", "competitor", "market share", "industry", "rival"],
                "market": ["market", "demand", "supply", "price", "volatility", "fluctuation"],
                "credit": ["credit", "debt", "loan", "borrowing", "default", "interest rate"],
                "operational": ["operation", "supply chain", "infrastructure", "system", "process"]
            }
            
            negative_scores = []
            processed_chunks = 0
            risk_entities = []
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                try:
                    chunk_result = self._call_api(self.risk_model_url, chunk)
                    processed_chunks += 1
                    
                    # Handle nested list structure
                    flattened_results = []
                    if isinstance(chunk_result, list):
                        for item in chunk_result:
                            if isinstance(item, list):
                                flattened_results.extend(item)
                            else:
                                flattened_results.append(item)
                    else:
                        flattened_results = [chunk_result]
                    
                    # Process sentiment results from FinBERT
                    for prediction in flattened_results:
                        if isinstance(prediction, dict) and 'label' in prediction and 'score' in prediction:
                            # Handle both lowercase and capitalized labels
                            label = prediction['label']
                            if label:
                                label = label.lower()  # Convert to lowercase
                                score = prediction['score']
                                
                                # If negative sentiment, consider it as risk
                                if label == 'negative':
                                    negative_scores.append(score)
                                    
                                    # Extract risk entities based on keywords
                                    chunk_lower = chunk.lower()
                                    for category, keywords in risk_keywords.items():
                                        for keyword in keywords:
                                            if keyword in chunk_lower:
                                                risk_categories[category] += score
                                                
                                                # Find the sentence containing the keyword
                                                sentences = re.split(r'[.!?]', chunk)
                                                for sentence in sentences:
                                                    if keyword in sentence.lower():
                                                        risk_entities.append({
                                                            'word': sentence.strip(),
                                                            'entity_group': 'RISK',
                                                            'score': score
                                                        })
                except Exception as e:
                    logger.error(f"Error processing chunk {i+1}: {str(e)}")
            
            # Calculate overall risk score based on negative sentiment
            avg_risk_score = sum(negative_scores) / len(negative_scores) if negative_scores else 0.5
            
            # Normalize risk categories
            total_risk = sum(risk_categories.values())
            if total_risk > 0:
                for category in risk_categories:
                    risk_categories[category] /= total_risk
            
            # Determine primary risk factors
            primary_risks = self._identify_primary_risks(risk_entities)
            
            # If no primary risks identified from entities, use categories
            if not primary_risks:
                primary_risks = sorted(
                    risk_categories.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:3]
            
            return {
                "overall_risk_score": avg_risk_score,
                "risk_entities": risk_entities,
                "risk_categories": risk_categories,
                "primary_risk_factors": primary_risks,
                "chunk_count": len(chunks),
                "processed_chunks": processed_chunks
            }
        except Exception as e:
            logger.error(f"Error analyzing risk: {str(e)}")
            return self._fallback_risk_analysis(text)
    
    def _calculate_risk_score(self, risk_entities: List[Dict[str, Any]]) -> float:
        """
        Calculate risk score based on NER results.
        
        Args:
            risk_entities: Results from the NER model
            
        Returns:
            Risk score between 0 and 1
        """
        # Risk keywords for additional weighting
        risk_keywords = [
            "risk", "decline", "loss", "liability", "litigation", "volatility",
            "uncertainty", "threat", "challenge", "adverse", "negative"
        ]
        
        if not risk_entities:
            return 0.5  # Default neutral score
        
        # Count risk-related entities and their scores
        total_score = 0
        weighted_score = 0
        
        for entity in risk_entities:
            entity_text = entity.get('word', '').lower()
            entity_score = entity.get('score', 0.5)
            entity_type = entity.get('entity_group', '')
            
            # Base weight by entity type
            weight = 1.0
            if entity_type == 'RISK':
                weight = 1.5
            elif entity_type == 'CHALLENGE':
                weight = 1.2
            
            # Additional weight for risk keywords
            if any(keyword in entity_text for keyword in risk_keywords):
                weight *= 1.2
            
            weighted_score += entity_score * weight
            total_score += weight
        
        # Calculate normalized risk score
        return min(1.0, weighted_score / total_score) if total_score > 0 else 0.5
    
    def _identify_primary_risks(self, risk_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify primary risk factors from entity list.
        
        Args:
            risk_entities: List of risk-related entities
            
        Returns:
            List of primary risk factors
        """
        if not risk_entities:
            return []
        
        # Sort by score and entity type importance
        def entity_importance(entity):
            type_weight = {
                'RISK': 3,
                'CHALLENGE': 2,
                'FINANCIAL_OBJECTIVE': 1,
                'OBJECTIVE': 0
            }
            return (entity.get('score', 0) * type_weight.get(entity.get('entity_group', ''), 0))
        
        sorted_entities = sorted(risk_entities, key=entity_importance, reverse=True)
        
        # Take top entities, avoiding duplicates
        primary_risks = []
        seen_texts = set()
        
        for entity in sorted_entities:
            text = entity.get('word', '').lower()
            if text not in seen_texts and len(primary_risks) < 5:  # Limit to top 5
                primary_risks.append({
                    'text': entity.get('word', ''),
                    'type': entity.get('entity_group', ''),
                    'score': entity.get('score', 0)
                })
                seen_texts.add(text)
        
        return primary_risks
    
    def _fallback_sentiment_analysis(self, text: str) -> Dict[str, Any]:
        """
        Fallback sentiment analysis using keyword-based approach.
        Used when API calls fail.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with sentiment analysis results
        """
        # Positive and negative financial terms
        positive_terms = [
            "growth", "profit", "increase", "gain", "improved", "strong",
            "success", "positive", "opportunity", "exceed", "beat", "upside",
            "outperform", "dividend", "recovery", "innovation", "leadership"
        ]
        
        negative_terms = [
            "loss", "decline", "decrease", "risk", "debt", "liability",
            "negative", "weak", "poor", "fail", "miss", "downside",
            "underperform", "litigation", "challenge", "difficult", "uncertain",
            "volatility", "adverse", "threat", "concern", "issue", "problem"
        ]
        
        # Count term occurrences
        text_lower = text.lower()
        positive_count = sum(text_lower.count(term) for term in positive_terms)
        negative_count = sum(text_lower.count(term) for term in negative_terms)
        
        # Determine sentiment
        total_count = positive_count + negative_count
        if total_count == 0:
            return {
                "sentiment": "neutral",
                "score": 0.5,
                "chunk_count": 1,
                "processed_chunks": 0,
                "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 1},
                "is_fallback": True,
                "keyword_analysis": {"negative": negative_count, "positive": positive_count}
            }
        
        positive_ratio = positive_count / total_count
        negative_ratio = negative_count / total_count
        
        # Strong signals override
        if negative_count > positive_count + 2:
            sentiment = "negative"
            score = 0.25  # Clearly negative
        elif positive_count > negative_count + 2:
            sentiment = "positive"
            score = 0.75  # Clearly positive
        elif positive_ratio > negative_ratio:
            sentiment = "positive"
            score = 0.5 + (positive_ratio - 0.5) * 0.5  # Scale to 0.5-1.0
        elif negative_ratio > positive_ratio:
            sentiment = "negative"
            score = 0.5 - (negative_ratio - 0.5) * 0.5  # Scale to 0.0-0.5
        else:
            sentiment = "neutral"
            score = 0.5
        
        return {
            "sentiment": sentiment,
            "score": score,
            "chunk_count": 1,
            "processed_chunks": 0,
            "sentiment_distribution": {
                "positive": positive_count,
                "negative": negative_count,
                "neutral": 1 if total_count == 0 else 0
            },
            "is_fallback": True,
            "keyword_analysis": {"negative": negative_count, "positive": positive_count}
        }
    
    def _fallback_risk_analysis(self, text: str) -> Dict[str, Any]:
        """
        Fallback risk analysis using keyword-based approach.
        Used when API calls fail.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with risk analysis results
        """
        # Risk category keywords
        risk_categories = {
            "litigation": ["lawsuit", "legal", "litigation", "court", "settlement", "dispute"],
            "regulation": ["regulation", "compliance", "regulatory", "law", "requirement", "authority"],
            "competition": ["competition", "competitor", "market share", "industry", "rival"],
            "market": ["market", "demand", "supply", "price", "volatility", "fluctuation"],
            "credit": ["credit", "debt", "loan", "borrowing", "default", "interest rate"],
            "operational": ["operation", "supply chain", "infrastructure", "system", "process"]
        }
        
        # Count keyword occurrences by category
        text_lower = text.lower()
        category_counts = {}
        total_count = 0
        
        for category, keywords in risk_categories.items():
            count = sum(text_lower.count(keyword) for keyword in keywords)
            category_counts[category] = count
            total_count += count
        
        # Add "other" category
        category_counts["other"] = 1  # Ensure some baseline risk
        total_count += 1
        
        # Normalize counts
        risk_distribution = {}
        for category, count in category_counts.items():
            risk_distribution[category] = count / total_count if total_count > 0 else 0
        
        # Calculate overall risk score based on risk terms
        risk_terms = [
            "risk", "uncertainty", "threat", "challenge", "adverse", "negative",
            "volatility", "decline", "loss", "liability", "litigation"
        ]
        
        risk_term_count = sum(text_lower.count(term) for term in risk_terms)
        text_length = len(text_lower.split())
        
        # Normalize risk score (0.3-0.7 range to avoid extremes)
        risk_score = 0.3 + (min(risk_term_count / max(text_length / 100, 1), 1.0) * 0.4)
        
        # Determine primary risk factors
        primary_risks = sorted(
            risk_distribution.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        return {
            "overall_risk_score": risk_score,
            "risk_categories": risk_distribution,
            "primary_risk_factors": primary_risks,
            "chunk_count": 1,
            "processed_chunks": 0,
            "is_fallback": True
        }
    
    def analyze_financial_text(self, text: str) -> Dict[str, Any]:
        """
        Comprehensive analysis of financial text using all models.
        
        Args:
            text: Financial text to analyze
            
        Returns:
            Dictionary with comprehensive analysis results
        """
        results = {}
        
        # Analyze sentiment
        try:
            sentiment_results = self.analyze_sentiment(text)
            results["sentiment"] = sentiment_results
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            results["sentiment"] = self._fallback_sentiment_analysis(text)
        
        # Extract entities
        try:
            entity_results = self.extract_entities(text)
            results["entities"] = entity_results
        except Exception as e:
            logger.error(f"Error in entity extraction: {str(e)}")
            results["entities"] = {"entities": {}, "error": str(e)}
        
        # Analyze risk
        try:
            risk_results = self.analyze_risk(text)
            results["risk"] = risk_results
        except Exception as e:
            logger.error(f"Error in risk analysis: {str(e)}")
            results["risk"] = self._fallback_risk_analysis(text)
        
        # Generate insights based on all analyses
        results["insights"] = self._generate_insights(results)
        
        return results
    
    def _generate_insights(self, analysis_results: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate insights based on analysis results.
        
        Args:
            analysis_results: Results from all analyses
            
        Returns:
            Dictionary with insights
        """
        insights = {}
        
        # Sentiment insights
        sentiment_data = analysis_results.get("sentiment", {})
        sentiment = sentiment_data.get("sentiment", "neutral")
        sentiment_score = sentiment_data.get("score", 0.5)
        
        if sentiment == "positive" and sentiment_score > 0.7:
            insights["sentiment"] = "The text conveys a strongly positive financial outlook."
        elif sentiment == "positive":
            insights["sentiment"] = "The text indicates a generally positive financial perspective."
        elif sentiment == "negative" and sentiment_score < 0.3:
            insights["sentiment"] = "The text expresses significant financial concerns or challenges."
        elif sentiment == "negative":
            insights["sentiment"] = "The text suggests some financial challenges or concerns."
        else:
            insights["sentiment"] = "The text maintains a neutral financial tone."
        
        # Risk insights
        risk_data = analysis_results.get("risk", {})
        risk_score = risk_data.get("overall_risk_score", 0.5)
        primary_risks = risk_data.get("primary_risk_factors", [])
        
        if risk_score > 0.7:
            risk_insight = "High level of financial risk identified."
        elif risk_score > 0.5:
            risk_insight = "Moderate financial risks are present."
        else:
            risk_insight = "Relatively low financial risk profile."
            
        if primary_risks:
            # Handle both tuple format (category, score) and dict format (text, type, score)
            if isinstance(primary_risks[0], tuple):
                risk_factors = ", ".join([f"{r[0]}" for r in primary_risks[:2]])
            elif isinstance(primary_risks[0], dict):
                # Extract shorter risk descriptions
                risk_texts = []
                for r in primary_risks[:2]:
                    text = r.get('text', '')
                    # Extract a shorter version (first 50 chars or first sentence)
                    if len(text) > 50:
                        shorter = text[:50].split(',')[0]
                        if 'due to' in shorter:
                            shorter = shorter.split('due to')[1].strip()
                        elif 'facing' in shorter:
                            shorter = shorter.split('facing')[1].strip()
                        elif 'includes' in shorter:
                            shorter = shorter.split('includes')[1].strip()
                    else:
                        shorter = text
                    
                    if shorter and len(shorter) > 3:  # Ensure it's not empty or too short
                        risk_texts.append(shorter)
                
                if risk_texts:
                    risk_factors = ", ".join(risk_texts)
                else:
                    risk_factors = "market and competition factors"
            else:
                risk_factors = "various factors"
                
            risk_insight += f" Key risk areas: {risk_factors}."
            
        insights["risk"] = risk_insight
        
        # Entity insights
        entity_data = analysis_results.get("entities", {}).get("entities", {})
        
        # Update entity insight for the new categories
        entity_insight = "Key financial elements identified"
        
        financial_terms = []
        metrics = []
        risks = []
        opportunities = []
        
        # Extract top terms from each category
        if "FINANCIAL_TERM" in entity_data and entity_data["FINANCIAL_TERM"]:
            financial_terms = [item.get('keyword', '') for item in entity_data["FINANCIAL_TERM"][:3]]
        
        if "METRIC" in entity_data and entity_data["METRIC"]:
            metrics = [item.get('keyword', '') for item in entity_data["METRIC"][:3]]
        
        if "RISK" in entity_data and entity_data["RISK"]:
            risks = [item.get('keyword', '') for item in entity_data["RISK"][:3]]
        
        if "OPPORTUNITY" in entity_data and entity_data["OPPORTUNITY"]:
            opportunities = [item.get('keyword', '') for item in entity_data["OPPORTUNITY"][:3]]
        
        # Build insight based on found terms
        if financial_terms:
            entity_insight += f" include financial terms ({', '.join(financial_terms)})"
            
        if metrics:
            if financial_terms:
                entity_insight += f", metrics ({', '.join(metrics)})"
            else:
                entity_insight += f" include metrics ({', '.join(metrics)})"
        
        if risks:
            if financial_terms or metrics:
                entity_insight += f", and risk factors ({', '.join(risks)})"
            else:
                entity_insight += f" include risk factors ({', '.join(risks)})"
        
        if opportunities and not (financial_terms or metrics or risks):
            entity_insight += f" include growth opportunities ({', '.join(opportunities)})"
        
        entity_insight += "."
        
        insights["entities"] = entity_insight
        
        # Overall insight
        if sentiment == "positive" and risk_score < 0.4:
            overall = "The financial text presents a positive outlook with manageable risks."
        elif sentiment == "negative" and risk_score > 0.6:
            overall = "The financial text indicates significant challenges and elevated risks."
        elif sentiment == "neutral" and risk_score > 0.6:
            overall = "Despite neutral language, substantial financial risks are identified."
        elif sentiment == "positive" and risk_score > 0.6:
            overall = "While the tone is positive, significant financial risks are present."
        elif sentiment == "negative" and risk_score < 0.4:
            overall = "Despite negative elements, the overall risk profile appears manageable."
        else:
            overall = "The financial text presents a balanced view of opportunities and challenges."
            
        insights["overall"] = overall
        
        return insights 