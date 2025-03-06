import os
import logging
import re
import json
import time
from typing import List, Dict, Any, Optional, Tuple
import requests
from dotenv import load_dotenv

# Import shared utilities
from services.nlp_utils import (
    chunk_text, 
    call_huggingface_api, 
    fallback_sentiment_analysis,
    extract_basic_entities
)

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class HuggingFaceService:
    """Service for interacting with HuggingFace models."""
    
    def __init__(self):
        """Initialize the HuggingFace service with API keys and models."""
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        
        # Define model URLs
        self.finbert_model_url = "https://api-inference.huggingface.co/models/ProsusAI/finbert"
        self.bart_model_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
        self.t5_model_url = "https://api-inference.huggingface.co/models/google/flan-t5-xl"
        self.ner_model_url = "https://api-inference.huggingface.co/models/dslim/bert-base-NER"
        
        # Validate API key
        self.is_api_key_valid = self._validate_api_key()
        
        # Configure chunking parameters
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "4000"))
        self.overlap_size = int(os.getenv("OVERLAP_SIZE", "200"))
        
        logger.info("HuggingFaceService initialized")
    
    def _validate_api_key(self) -> bool:
        """
        Validate the HuggingFace API key.
        
        Returns:
            bool: True if the API key is valid, False otherwise
        """
        if not self.api_key:
            logger.warning("No HuggingFace API key provided")
            return False
            
        if len(self.api_key) < 8:  # Basic check for key length
            logger.warning("HuggingFace API key appears to be invalid (too short)")
            return False
            
        try:
            # Test API call to validate the key
            response = requests.post(
                self.finbert_model_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"inputs": "The company reported strong financial results."},
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info("HuggingFace API key validated successfully")
                return True
            elif response.status_code == 401:
                logger.error("HuggingFace API key is invalid (401 Unauthorized)")
                return False
            else:
                logger.warning(f"HuggingFace API key validation returned status code: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error validating HuggingFace API key: {str(e)}")
            return False
    
    def _call_api(self, model_url: str, text: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Call the HuggingFace API with proper error handling.
        
        Args:
            model_url: URL of the model to use
            text: Text to process
            max_retries: Maximum number of retries
            
        Returns:
            Dictionary with API response
            
        Raises:
            ValueError: If the API key is invalid
            TimeoutError: If the API call times out
            Exception: For other errors
        """
        # Validate that we have a valid API key
        if not self.is_api_key_valid:
            logger.error("Cannot call HuggingFace API without a valid API key")
            raise ValueError("HuggingFace API key not configured or invalid")
            
        # Use the shared utility function to make the API call
        return call_huggingface_api(self.api_key, model_url, text, max_retries)
    
    def _get_mock_response(self, model_url: str, text: str) -> Dict[str, Any]:
        """
        Generate mock responses for testing or when API is unavailable.
        
        Args:
            model_url: URL of the model that would be called
            text: Text that would be processed
            
        Returns:
            Dictionary with mock response
        """
        logger.info(f"Generating mock response for model {model_url}")
        
        # Generate appropriate mock response based on the model URL
        if "finbert" in model_url:
            # Mock sentiment analysis response
            return [
                [
                    {"label": "positive", "score": 0.75},
                    {"label": "neutral", "score": 0.20},
                    {"label": "negative", "score": 0.05}
                ]
            ]
        elif "bart" in model_url or "t5" in model_url:
            # Mock summarization response
            return [
                {"summary_text": f"Mock summary of the text: {text[:100]}..."}
            ]
        elif "NER" in model_url:
            # Mock named entity recognition response
            return [
                {"entity": "B-ORG", "score": 0.95, "word": "Company"},
                {"entity": "I-ORG", "score": 0.90, "word": "Inc"},
                {"entity": "B-LOC", "score": 0.85, "word": "New"},
                {"entity": "I-LOC", "score": 0.80, "word": "York"}
            ]
        else:
            # Generic mock response
            return {"result": "Mock response for testing purposes"}
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of financial text using HuggingFace models.
        
        Args:
            text: Financial text to analyze
            
        Returns:
            Dictionary with sentiment analysis results
        """
        logger.info(f"Analyzing sentiment of text with length {len(text)}")
        
        try:
            # Break into chunks if text is long
            chunks = chunk_text(text, self.chunk_size, self.overlap_size)
            
            # Process each chunk
            chunk_results = []
            for i, chunk in enumerate(chunks[:5]):  # Limit to first 5 chunks for efficiency
                logger.info(f"Processing chunk {i+1}/{min(len(chunks), 5)} for sentiment analysis")
                
                try:
                    # Call the FinBERT API
                    result = self._call_api(self.finbert_model_url, chunk)
                    chunk_results.append(result)
                except Exception as e:
                    logger.error(f"Error analyzing sentiment for chunk {i+1}: {str(e)}")
                    # Continue with other chunks
            
            # Combine results from all chunks
            if chunk_results:
                # Process and aggregate sentiment scores
                positive_score = 0
                neutral_score = 0
                negative_score = 0
                
                for result in chunk_results:
                    for label_info in result[0]:
                        if label_info["label"].lower() == "positive":
                            positive_score += label_info["score"]
                        elif label_info["label"].lower() == "negative":
                            negative_score += label_info["score"]
                        else:
                            neutral_score += label_info["score"]
                
                # Normalize scores
                total_chunks = len(chunk_results)
                positive_score /= total_chunks
                neutral_score /= total_chunks
                negative_score /= total_chunks
                
                # Determine overall sentiment
                if positive_score > negative_score and positive_score > neutral_score:
                    sentiment = "positive"
                    explanation = "The text contains predominantly positive financial language."
                    score = positive_score
                elif negative_score > positive_score and negative_score > neutral_score:
                    sentiment = "negative"
                    explanation = "The text contains predominantly negative financial language."
                    score = negative_score
                else:
                    sentiment = "neutral"
                    explanation = "The text contains balanced or neutral financial language."
                    score = neutral_score
                
                # Return structured results
                return {
                    "sentiment": sentiment,
                    "score": score,
                    "explanation": explanation,
                    "raw_scores": {
                        "positive": positive_score,
                        "neutral": neutral_score,
                        "negative": negative_score
                    },
                    "method": "finbert"
                }
            else:
                # If no chunks were successfully processed, use fallback
                logger.warning("No chunks were successfully processed for sentiment analysis, using fallback")
                return fallback_sentiment_analysis(text)
                
        except Exception as e:
            logger.error(f"Error in HuggingFaceService.analyze_sentiment: {str(e)}")
            # Use fallback sentiment analysis
            return fallback_sentiment_analysis(text)
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract named entities from text using HuggingFace models.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with extracted entities
        """
        logger.info(f"Extracting entities from text with length {len(text)}")
        
        try:
            # Break into chunks if text is long
            chunks = chunk_text(text, self.chunk_size, self.overlap_size)
            
            # Process each chunk
            all_entities = []
            for i, chunk in enumerate(chunks[:3]):  # Limit to first 3 chunks for efficiency
                logger.info(f"Processing chunk {i+1}/{min(len(chunks), 3)} for entity extraction")
                
                try:
                    # Call the NER API
                    result = self._call_api(self.ner_model_url, chunk)
                    all_entities.extend(result)
                except Exception as e:
                    logger.error(f"Error extracting entities for chunk {i+1}: {str(e)}")
                    # Continue with other chunks
            
            # Process and organize entities
            if all_entities:
                # Extract organizations, locations, and people
                organizations = []
                locations = []
                people = []
                
                current_entity = ""
                current_type = None
                
                for entity_info in all_entities:
                    if entity_info.get("entity", "").startswith("B-"):
                        # If we were building an entity, save it
                        if current_entity and current_type:
                            if current_type == "ORG":
                                organizations.append(current_entity.strip())
                            elif current_type == "LOC":
                                locations.append(current_entity.strip())
                            elif current_type == "PER":
                                people.append(current_entity.strip())
                        
                        # Start a new entity
                        current_entity = entity_info.get("word", "")
                        current_type = entity_info.get("entity", "")[2:]  # Remove "B-" prefix
                    
                    elif entity_info.get("entity", "").startswith("I-"):
                        # Continue building current entity
                        if current_type == entity_info.get("entity", "")[2:]:  # Same type without "I-" prefix
                            current_entity += " " + entity_info.get("word", "")
                
                # Add the last entity if there is one
                if current_entity and current_type:
                    if current_type == "ORG":
                        organizations.append(current_entity.strip())
                    elif current_type == "LOC":
                        locations.append(current_entity.strip())
                    elif current_type == "PER":
                        people.append(current_entity.strip())
                
                # Remove duplicates and limit results
                organizations = list(set(organizations))[:15]
                locations = list(set(locations))[:15]
                people = list(set(people))[:15]
                
                return {
                    "entities": {
                        "organizations": organizations,
                        "locations": locations,
                        "people": people
                    },
                    "method": "huggingface_ner"
                }
            else:
                # If no entities were extracted, use fallback
                logger.warning("No entities were successfully extracted, using fallback")
                return {"entities": extract_basic_entities(text), "method": "fallback"}
                
        except Exception as e:
            logger.error(f"Error in HuggingFaceService.extract_entities: {str(e)}")
            # Use fallback entity extraction
            return {"entities": extract_basic_entities(text), "method": "fallback"}
    
    def analyze_risk(self, text: str) -> Dict[str, Any]:
        """
        Analyze risk factors in financial text.
        
        Args:
            text: Financial text to analyze
            
        Returns:
            Dictionary with risk analysis results
        """
        logger.info(f"Analyzing risks in text with length {len(text)}")
        
        try:
            # Use T5 model to analyze risks
            prompt = "Identify the top risk factors mentioned in this financial report: "
            
            # Break into chunks if text is long
            chunks = chunk_text(text, self.chunk_size, self.overlap_size)
            
            # Take a representative sample of the text
            sample_text = ""
            if len(chunks) > 3:
                # Use first, middle, and last chunk
                sample_text = chunks[0] + "\n...\n" + chunks[len(chunks)//2] + "\n...\n" + chunks[-1]
            else:
                sample_text = "\n".join(chunks)
            
            # Call the T5 API
            input_text = prompt + sample_text[:4000]  # Limit size for API call
            try:
                result = self._call_api(self.t5_model_url, input_text)
                
                # Process results
                risk_text = result[0].get("generated_text", "")
                
                # Parse risk factors (assuming they're returned as a list or separated by newlines)
                risk_factors = [r.strip() for r in risk_text.split("\n") if r.strip()]
                if not risk_factors:
                    risk_factors = [risk_text]
                
                return {
                    "risks": risk_factors,
                    "risk_score": self._calculate_risk_score(risk_factors),
                    "method": "t5"
                }
                
            except Exception as e:
                logger.error(f"Error analyzing risks with T5: {str(e)}")
                
                # Use regex-based fallback
                from services.nlp_utils import extract_risk_factors_with_regex
                risk_factors = extract_risk_factors_with_regex(text)
                
                return {
                    "risks": risk_factors,
                    "risk_score": len(risk_factors) / 10,  # Simple score based on number of factors
                    "method": "fallback_regex"
                }
                
        except Exception as e:
            logger.error(f"Error in HuggingFaceService.analyze_risk: {str(e)}")
            
            # Use regex-based fallback
            from services.nlp_utils import extract_risk_factors_with_regex
            risk_factors = extract_risk_factors_with_regex(text)
            
            return {
                "risks": risk_factors,
                "risk_score": len(risk_factors) / 10,  # Simple score based on number of factors
                "method": "fallback_regex"
            }
    
    def _calculate_risk_score(self, risk_factors: List[str]) -> float:
        """
        Calculate a risk score based on identified risk factors.
        
        Args:
            risk_factors: List of identified risk factors
            
        Returns:
            Risk score between 0 and 1
        """
        # Define risk keywords with severity weights
        risk_keywords = {
            "high": 1.0,
            "significant": 0.9,
            "substantial": 0.9,
            "major": 0.8,
            "critical": 1.0,
            "severe": 1.0,
            "moderate": 0.6,
            "potential": 0.5,
            "possible": 0.4,
            "minor": 0.3,
            "limited": 0.2,
            "unlikely": 0.1,
            "rare": 0.1
        }
        
        # Count risk factors and calculate weighted severity
        total_score = 0
        for risk in risk_factors:
            risk_lower = risk.lower()
            factor_score = 0.5  # Default score
            
            # Check for severity keywords
            for keyword, weight in risk_keywords.items():
                if keyword in risk_lower:
                    factor_score = max(factor_score, weight)
            
            total_score += factor_score
        
        # Normalize score between 0 and 1
        if not risk_factors:
            return 0
        
        normalized_score = min(total_score / (len(risk_factors) * 2), 1.0)
        return normalized_score
    
    def generate_summary(self, text: str, metrics_dict: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a summary using Hugging Face's free inference API endpoints.
        
        Args:
            text (str): The text content of the annual report
            metrics_dict (dict): Optional dictionary of metrics from database
            
        Returns:
            Dict[str, Any]: A structured summary of the annual report with metrics
        """
        try:
            logger.info(f"Generating summary for text of length {len(text)} using free Hugging Face model")
            
            # Use a smaller, free model on Hugging Face
            free_model_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
            
            # Chunk the text to handle large reports
            chunks = chunk_text(text, self.chunk_size, self.overlap_size)
            logger.info(f"Split text into {len(chunks)} chunks for summary generation")
            
            # Create metrics text if provided
            metrics_text = ""
            if metrics_dict and isinstance(metrics_dict, dict):
                metrics_text = "Key financial metrics from the report:\n"
                for key, value in metrics_dict.items():
                    if isinstance(value, (int, float, str)):
                        metrics_text += f"- {key.replace('_', ' ').title()}: {value}\n"
                metrics_text += "\n"
            
            # Process each chunk and combine results
            summaries = []
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)} for summary")
                
                # Create a prompt that includes metrics if available
                if i == 0 and metrics_text:  # Only include metrics for first chunk
                    prompt = f"{metrics_text}Summarize the following text: {chunk}"
                else:
                    prompt = f"Summarize the following text: {chunk}"
                
                try:
                    # Call the BART model API
                    result = self._call_api(free_model_url, prompt)
                    
                    # Extract summary text
                    summary_text = result[0]["summary_text"]
                    summaries.append(summary_text)
                    
                except Exception as e:
                    logger.error(f"Error generating summary for chunk {i+1}: {str(e)}")
                    # Continue with other chunks
            
            # Combine summaries
            if summaries:
                combined_summary = " ".join(summaries)
                
                # Generate executive summary with key points
                return {
                    "summary": combined_summary,
                    "method": "bart"
                }
            else:
                # Fallback if no summaries were generated
                logger.warning("No summaries were successfully generated, using fallback")
                return self._fallback_summary_generation(text, metrics_dict)
                
        except Exception as e:
            logger.error(f"Error in HuggingFaceService.generate_summary: {str(e)}")
            # Use fallback summary generation
            return self._fallback_summary_generation(text, metrics_dict)
    
    def _fallback_summary_generation(self, text: str, metrics_dict: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate a summary using fallback methods when API calls fail.
        
        Args:
            text: Text to summarize
            metrics_dict: Optional dictionary of metrics
            
        Returns:
            Dictionary with summary
        """
        logger.info("Using fallback method for summary generation")
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Extract important sentences
        important_sentences = []
        
        # Keywords to look for
        important_keywords = [
            "key", "important", "significant", "highlight", "report", "financial",
            "revenue", "profit", "loss", "growth", "decline", "increase", "decrease",
            "billion", "million", "percent", "quarterly", "annual", "fiscal", "year"
        ]
        
        # Go through sentences and score them based on keywords
        sentence_scores = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10 or len(sentence) > 200:
                continue
                
            score = 0
            for keyword in important_keywords:
                if keyword in sentence.lower():
                    score += 1
            
            sentence_scores.append((sentence, score))
        
        # Sort by score and take top sentences
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [s[0] for s in sentence_scores[:10]]
        
        # Add metrics information if available
        if metrics_dict and isinstance(metrics_dict, dict):
            metrics_summary = "Key financial metrics: "
            for key, value in metrics_dict.items():
                if isinstance(value, (int, float, str)):
                    metrics_summary += f"{key.replace('_', ' ').title()}: {value}, "
            
            top_sentences.insert(0, metrics_summary.rstrip(", "))
        
        # Combine into summary
        summary = " ".join(top_sentences)
        
        return {
            "summary": summary,
            "method": "fallback_extraction"
        } 