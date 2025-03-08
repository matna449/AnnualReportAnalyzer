import os
import logging
import re
import json
import time
import random
from typing import List, Dict, Any, Optional, Tuple
import requests
from dotenv import load_dotenv
from huggingface_hub import InferenceClient, InferenceTimeoutError
from huggingface_hub.errors import HTTPError

# Import shared utilities
from services.nlp_utils import (
    chunk_text, 
    fallback_sentiment_analysis,
    extract_basic_entities,
    estimate_tokens,
    extract_risk_factors_with_regex
)

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class HuggingFaceService:
    """Service for interacting with HuggingFace models using InferenceClient."""
    
    def __init__(self):
        """Initialize the HuggingFace service with API keys and models."""
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        
        # Define model URLs - updated models for better performance
        self.finbert_model = "ProsusAI/finbert"
        
        # Use BART-large-CNN for better news summarization
        self.bart_model = "facebook/bart-large-cnn"
        
        # Use a model better suited for long-form summarization
        self.summarization_model = os.getenv(
            "SUMMARIZATION_MODEL", 
            "facebook/bart-large-xsum"
        )
        
        # Smaller model for fallback - will use less tokens, be faster
        self.fallback_summarization_model = "facebook/bart-base"
        
        # Flan-T5-XL is good for detailed tasks, but can timeout - use smaller version for fallback
        self.t5_model = "google/flan-t5-xl" 
        self.fallback_t5_model = "google/flan-t5-base"
        
        # Standard NER model
        self.ner_model = "dslim/bert-base-NER"
        
        # Create InferenceClient with API key (more robust handling than direct calls)
        self.inference_client = InferenceClient(provider = "hf-inference", api_key=self.api_key)
        
        # Validate API key
        self.is_api_key_valid = self._validate_api_key()
        
        # Configure chunking parameters - reduced from default for reliability
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "1600"))  # Reduced from 2000/4000
        self.overlap_size = int(os.getenv("OVERLAP_SIZE", "200"))
        
        # Configure token limits for different models
        self.max_input_tokens = int(os.getenv("MAX_INPUT_TOKENS", "1024"))
        self.max_output_tokens = int(os.getenv("MAX_OUTPUT_TOKENS", "512"))
        
        # Configure timeout parameters (in seconds) - used for direct requests, not InferenceClient
        self.request_timeout = float(os.getenv("HF_REQUEST_TIMEOUT", "15.0"))  # 15 seconds default timeout
        self.generation_timeout = float(os.getenv("HF_GENERATION_TIMEOUT", "30.0"))  # 30 seconds for generation
        
        # Configure retry parameters
        self.max_retries = int(os.getenv("MAX_API_RETRIES", "3"))
        self.max_chunk_retries = int(os.getenv("MAX_CHUNK_RETRIES", "2"))
        
        logger.info(f"HuggingFaceService initialized with chunk_size={self.chunk_size}, timeout={self.request_timeout}s")
    
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
            # Test API call to validate the key using InferenceClient
            # Note: InferenceClient methods don't support timeout parameter
            response = self.inference_client.text_classification(
                text="The company reported strong financial results.",
                model=self.finbert_model
            )
            
            logger.info("HuggingFace API key validated successfully")
            return True
                
        except Exception as e:
            logger.error(f"Error validating HuggingFace API key: {str(e)}")
            return False
    
    def _call_inference_api(
        self, 
        model_name: str, 
        task: str, 
        inputs: str, 
        max_retries: int = None, 
        **kwargs
    ) -> Any:
        """
        Call the HuggingFace API using InferenceClient with proper error handling.
        
        Args:
            model_name: Name of the model to use
            task: Task type ('text-classification', 'summarization', 'text-generation', etc.)
            inputs: Text to process
            max_retries: Maximum number of retries
            **kwargs: Additional parameters for the task
            
        Returns:
            API response based on task type
            
        Raises:
            ValueError: If the API key is invalid
            TimeoutError: If the API call times out
            Exception: For other errors
        """
        # If API key is not valid, use mock responses
        if not self.is_api_key_valid:
            logger.warning(f"API key is not valid. Using mock response for {task}.")
            return self._get_mock_response(model_name, task, inputs)
        
        # Use class-level max_retries if none specified
        if max_retries is None:
            max_retries = self.max_retries
        
        # Add estimated token count
        estimated_tokens = estimate_tokens(inputs)
        logger.info(f"Calling HuggingFace API for {task} with {estimated_tokens} estimated tokens")
        
        attempts = 0
        last_error = None
        base_wait_time = 2
        
        while attempts < max_retries:
            attempts += 1
            try:
                # Call the appropriate InferenceClient method based on task
                if task == "text-classification":
                    response = self.inference_client.text_classification(
                        inputs,  # Changed from text=inputs
                        model=model_name
                    )
                    return response
                    
                elif task == "summarization":
                    # For summarization tasks, pass parameters directly
                    max_length = kwargs.get("max_length", self.max_output_tokens)
                    min_length = kwargs.get("min_length", 30)
                    do_sample = kwargs.get("do_sample", False)
                    
                    response = self.inference_client.summarization(
                        inputs,  # Changed from text=inputs
                        model=model_name,
                        max_length=max_length,  # Direct parameters instead of parameters dict
                        min_length=min_length,
                        do_sample=do_sample
                    )
                    return {"summary_text": response}
                    
                elif task == "text-generation":
                    # For text generation tasks, pass parameters directly
                    max_new_tokens = kwargs.get("max_length", self.max_output_tokens)
                    temperature = kwargs.get("temperature", 0.7)
                    do_sample = kwargs.get("do_sample", True)
                    
                    response = self.inference_client.text_generation(
                        inputs,  # Changed from text=inputs
                        model=model_name,
                        max_new_tokens=max_new_tokens,  # Direct parameters instead of parameters dict
                        temperature=temperature,
                        do_sample=do_sample
                    )
                    return {"generated_text": response}
                    
                elif task == "token-classification":
                    response = self.inference_client.token_classification(
                        inputs,  # Changed from text=inputs
                        model=model_name
                    )
                    return response
                    
                else:
                    raise ValueError(f"Unsupported task type: {task}")
                    
            except InferenceTimeoutError as e:
                logger.warning(f"API timeout on attempt {attempts}: {str(e)}")
                last_error = e
                
                # If fallback is available and this is the last attempt, try fallback model
                if attempts == max_retries - 1:
                    try:
                        if task == "summarization" and model_name != self.fallback_summarization_model:
                            logger.info(f"Trying fallback summarization model: {self.fallback_summarization_model}")
                            return self._call_inference_api(
                                model_name=self.fallback_summarization_model,
                                task=task,
                                inputs=inputs,
                                max_retries=1,
                                **kwargs
                            )
                        elif task == "text-generation" and "t5" in model_name and model_name != self.fallback_t5_model:
                            logger.info(f"Trying fallback T5 model: {self.fallback_t5_model}")
                            return self._call_inference_api(
                                model_name=self.fallback_t5_model,
                                task=task,
                                inputs=inputs,
                                max_retries=1,
                                **kwargs
                            )
                    except Exception as fallback_error:
                        logger.error(f"Fallback model also failed: {str(fallback_error)}")
                
            except HTTPError as e:
                status_code = getattr(e.response, 'status_code', None)
                
                # Handle 503 Service Unavailable errors specifically
                if status_code == 503:
                    logger.warning(f"Service unavailable (503) for model {model_name} on attempt {attempts}: {str(e)}")
                    last_error = e
                    
                    # If this is the last attempt, try fallback mechanisms
                    if attempts == max_retries - 1:
                        try:
                            logger.info(f"Service unavailable for {model_name}, trying fallback...")
                            if task == "token-classification" and model_name == self.ner_model:
                                # For NER, use basic entity extraction as fallback
                                logger.info("Using basic entity extraction as fallback for NER")
                                from services.nlp_utils import extract_basic_entities
                                entities = extract_basic_entities(inputs)
                                return [
                                    {"entity_group": entity_type, "score": 0.8, "word": entity}
                                    for entity_type, entity_list in entities.items()
                                    for entity in entity_list
                                ]
                            # Add other fallbacks for different tasks as needed
                        except Exception as fallback_error:
                            logger.error(f"Fallback mechanism also failed: {str(fallback_error)}")
                
                elif "INDEX_OUT_OF_BOUNDS" in str(e) or "out of DATA bounds" in str(e):
                    logger.error(f"Index out of bounds error on attempt {attempts}: {str(e)}")
                    last_error = e
                    
                    # If this is not the last attempt, reduce the input
                    if attempts < max_retries:
                        # Try with shorter input
                        if len(inputs) > 500:
                            cut_ratio = 0.7  # Cut 30% of the input
                            logger.info(f"Reducing input length from {len(inputs)} to {int(len(inputs) * cut_ratio)}")
                            
                            # For first cut, try to cut from the end
                            if attempts == 1:
                                inputs = inputs[:int(len(inputs) * cut_ratio)]
                            # For second cut, try to cut from both ends
                            else:
                                start_cut = int(len(inputs) * 0.15)
                                end_cut = int(len(inputs) * 0.85)
                                inputs = inputs[start_cut:end_cut]
                    else:
                        raise Exception(f"Index bounds error after {attempts} attempts: {str(e)}")
                else:
                    logger.error(f"API error on attempt {attempts}: {str(e)}")
                    last_error = e
                    
            except Exception as e:
                logger.error(f"API call error on attempt {attempts}: {str(e)}")
                last_error = e
                
            # Wait before retry if not the last attempt
            if attempts < max_retries:
                # Exponential backoff with jitter
                jitter = random.uniform(0, 0.5)  # Add random jitter between 0-0.5
                wait_time = (base_wait_time * (2 ** (attempts - 1))) * (1 + jitter)
                logger.info(f"Waiting {wait_time:.2f}s before retry {attempts+1}/{max_retries}")
                time.sleep(wait_time)
            else:
                # All attempts failed
                logger.error(f"All {max_retries} API call attempts failed for model {model_name}, task {task}")
                
                # Return mock response as last resort fallback
                logger.info("Using mock response as final fallback")
                return self._get_mock_response(model_name, task, inputs)
    
    def _get_mock_response(self, model_name: str, task: str, inputs: str) -> Any:
        """
        Generate mock responses for testing or when API is unavailable.
        
        Args:
            model_name: Name of the model that would be called
            task: Task type
            inputs: Text that would be processed
            
        Returns:
            Mock response based on task type
        """
        logger.info(f"Generating mock response for model {model_name} and task {task}")
        
        # Generate appropriate mock response based on the task
        if task == "text-classification" and "finbert" in model_name:
            # Mock sentiment analysis response
            return [
                {"label": "positive", "score": 0.75},
                {"label": "neutral", "score": 0.20},
                {"label": "negative", "score": 0.05}
            ]
        elif task == "summarization":
            # Mock summarization response
            return {"summary_text": f"Mock summary of the text: {inputs[:100]}..."}
        elif task == "text-generation":
            # Mock text generation response
            return {"generated_text": f"Mock generated text based on: {inputs[:50]}..."}
        elif task == "token-classification" and "NER" in model_name:
            # Mock named entity recognition response
            return [
                {"entity_group": "ORG", "score": 0.95, "word": "Company"},
                {"entity_group": "ORG", "score": 0.90, "word": "Inc"},
                {"entity_group": "LOC", "score": 0.85, "word": "New"},
                {"entity_group": "LOC", "score": 0.80, "word": "York"}
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
            chunks = chunk_text(text, self.chunk_size, self.overlap_size, self.max_input_tokens)
            
            # Process each chunk
            chunk_results = []
            for i, chunk in enumerate(chunks[:5]):  # Limit to first 5 chunks for efficiency
                logger.info(f"Processing chunk {i+1}/{min(len(chunks), 5)} for sentiment analysis")
                
                try:
                    # Call the FinBERT API
                    result = self._call_inference_api(
                        model_name=self.finbert_model,
                        task="text-classification",
                        inputs=chunk
                    )
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
                    for label_info in result:
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
            chunks = chunk_text(text, self.chunk_size, self.overlap_size, self.max_input_tokens)
            
            # Process each chunk
            all_entities = []
            for i, chunk in enumerate(chunks[:3]):  # Limit to first 3 chunks for efficiency
                logger.info(f"Processing chunk {i+1}/{min(len(chunks), 3)} for entity extraction")
                
                try:
                    # Call the NER API
                    result = self._call_inference_api(
                        model_name=self.ner_model,
                        task="token-classification",
                        inputs=chunk
                    )
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
                    entity_group = entity_info.get("entity_group", "")  # Changed from "entity" to "entity_group"
                    word = entity_info.get("word", "")
                    
                    # Handle B- prefix (begin entity)
                    if entity_group.startswith("B-"):
                        # If we were building an entity, save it
                        if current_entity and current_type:
                            if current_type == "ORG":
                                organizations.append(current_entity.strip())
                            elif current_type == "LOC":
                                locations.append(current_entity.strip())
                            elif current_type == "PER":
                                people.append(current_entity.strip())
                        
                        # Start a new entity
                        current_entity = word
                        current_type = entity_group[2:]  # Remove "B-" prefix
                    
                    # Handle I- prefix (inside entity)
                    elif entity_group.startswith("I-"):
                        # Continue building current entity
                        if current_type == entity_group[2:]:  # Same type without "I-" prefix
                            current_entity += " " + word
                    
                    # Handle entities without B-/I- prefix (single token entities)
                    elif entity_group in ["ORG", "LOC", "PER"]:
                        if entity_group == "ORG":
                            organizations.append(word.strip())
                        elif entity_group == "LOC":
                            locations.append(word.strip())
                        elif entity_group == "PER":
                            people.append(word.strip())
                
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
            chunks = chunk_text(text, self.chunk_size, self.overlap_size, self.max_input_tokens)
            
            # Take a representative sample of the text
            sample_text = ""
            if len(chunks) > 3:
                # Use first, middle, and last chunk
                sample_text = chunks[0] + "\n...\n" + chunks[len(chunks)//2] + "\n...\n" + chunks[-1]
            else:
                sample_text = "\n".join(chunks)
            
            # Call the T5 API
            input_text = prompt + sample_text[:3000]  # Reduced from 4000 to improve reliability
            try:
                result = self._call_inference_api(
                    model_name=self.t5_model,
                    task="text-generation",
                    inputs=input_text,
                    max_length=self.max_output_tokens
                )
                
                # Process results
                risk_text = result.get("generated_text", "")
                
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
                risk_factors = extract_risk_factors_with_regex(text)
                
                return {
                    "risks": risk_factors,
                    "risk_score": len(risk_factors) / 10,  # Simple score based on number of factors
                    "method": "fallback_regex"
                }
                
        except Exception as e:
            logger.error(f"Error in HuggingFaceService.analyze_risk: {str(e)}")
            
            # Use regex-based fallback
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
        Generate a summary using Hugging Face models.
        
        Args:
            text (str): The text content of the annual report
            metrics_dict (dict): Optional dictionary of metrics from database
            
        Returns:
            Dict[str, Any]: A structured summary of the annual report with metrics
        """
        try:
            logger.info(f"Generating summary for text of length {len(text)} using HuggingFace models")
            
            # Use the configured summarization model
            model_name = self.summarization_model
            
            # Chunk the text to handle large reports - using updated token limit
            chunks = chunk_text(
                text, 
                chunk_size=self.chunk_size, 
                overlap_size=self.overlap_size,
                max_tokens=self.max_input_tokens
            )
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
            failed_chunks = []
            
            for i, chunk in enumerate(chunks[:5]):  # Limit to first 5 chunks for efficiency
                logger.info(f"Processing chunk {i+1}/{min(len(chunks), 5)} for summary")
                
                # Create a prompt that includes metrics if available
                if i == 0 and metrics_text:  # Only include metrics for first chunk
                    prompt = f"{metrics_text}Summarize the following text: {chunk}"
                else:
                    prompt = f"Summarize the following text: {chunk}"
                
                # Try to process this chunk with multiple retries
                chunk_success = False
                chunk_attempts = 0
                
                while not chunk_success and chunk_attempts < self.max_chunk_retries:
                    chunk_attempts += 1
                    try:
                        # Call the model API with explicit max_length
                        result = self._call_inference_api(
                            model_name=model_name,
                            task="summarization",
                            inputs=prompt,
                            max_length=self.max_output_tokens
                        )
                        
                        # Extract summary text
                        summary_text = result.get("summary_text", "")
                        if summary_text:
                            summaries.append(summary_text)
                            chunk_success = True
                            logger.info(f"Successfully processed chunk {i+1}/{min(len(chunks), 5)}")
                        else:
                            raise Exception("Empty summary text returned")
                        
                    except Exception as e:
                        logger.error(f"Error generating summary for chunk {i+1} (attempt {chunk_attempts}): {str(e)}")
                        
                        # If this is the last retry with primary model, try fallback model
                        if chunk_attempts >= self.max_chunk_retries - 1 and model_name != self.fallback_summarization_model:
                            try:
                                logger.info(f"Trying fallback summarization model for chunk {i+1}")
                                result = self._call_inference_api(
                                    model_name=self.fallback_summarization_model,
                                    task="summarization",
                                    inputs=prompt,
                                    max_length=self.max_output_tokens // 2,  # Shorter summary from fallback
                                )
                                
                                summary_text = result.get("summary_text", "")
                                if summary_text:
                                    summaries.append(summary_text)
                                    chunk_success = True
                                    logger.info(f"Successfully processed chunk {i+1} with fallback model")
                                else:
                                    raise Exception("Empty summary text returned from fallback model")
                                    
                            except Exception as fallback_error:
                                logger.error(f"Fallback model also failed for chunk {i+1}: {str(fallback_error)}")
                                # Add to failed chunks and continue
                                failed_chunks.append(i)
                        
                        # If not yet at retry limit, wait before retrying
                        elif chunk_attempts < self.max_chunk_retries:
                            # Wait before retry
                            wait_time = 2 ** chunk_attempts  # Exponential backoff
                            logger.info(f"Waiting {wait_time}s before retrying chunk {i+1}")
                            time.sleep(wait_time)
                        else:
                            # Add to failed chunks and continue
                            failed_chunks.append(i)
            
            # Check if there are any summaries
            if summaries:
                combined_summary = " ".join(summaries)
                
                # Log information about failed chunks
                if failed_chunks:
                    logger.warning(f"{len(failed_chunks)} chunks failed to process: {failed_chunks}")
                
                # Return the combined summary
                return {
                    "summary": combined_summary,
                    "method": "bart",
                    "chunks_processed": len(chunks) - len(failed_chunks),
                    "chunks_failed": len(failed_chunks)
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