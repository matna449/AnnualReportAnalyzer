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

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.model_name = os.getenv("MODEL_NAME", "google/flan-t5-large")
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "4000"))
        self.overlap_size = int(os.getenv("OVERLAP_SIZE", "200"))
        self.hf_api_url = "https://api-inference.huggingface.co/models/"
        
        # Check if API key is available
        if not self.huggingface_api_key:
            logger.warning("No Hugging Face API key provided. Using fallback methods.")
        else:
            logger.info(f"Hugging Face API key configured. Will use model: {self.model_name}")
        
        # Initialize Hugging Face models
        try:
            if self.huggingface_api_key:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
                self.summarizer = pipeline("summarization", model=self.model, tokenizer=self.tokenizer)
                self.qa_pipeline = pipeline("question-answering", model=self.model, tokenizer=self.tokenizer)
                self.text_generation = pipeline("text2text-generation", model=self.model, tokenizer=self.tokenizer)
                logger.info(f"Initialized Hugging Face model: {self.model_name}")
            else:
                logger.warning("No Hugging Face API key provided. Using fallback methods.")
                self.tokenizer = None
                self.model = None
                self.summarizer = None
                self.qa_pipeline = None
                self.text_generation = None
        except Exception as e:
            logger.error(f"Error initializing Hugging Face model: {str(e)}")
            self.tokenizer = None
            self.model = None
            self.summarizer = None
            self.qa_pipeline = None
            self.text_generation = None
    
    def _call_huggingface_api(self, model: str, payload: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """Make a call to the Hugging Face Inference API."""
        if not self.huggingface_api_key:
            raise ValueError("Hugging Face API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.huggingface_api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.hf_api_url}{model}"
        logger.info(f"Calling Hugging Face API: {url}")
        logger.debug(f"Payload size: {len(str(payload))} characters")
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload)
                
                # Check if the model is still loading
                if response.status_code == 503 and "Model is loading" in response.text:
                    wait_time = min(2 ** attempt, 10)  # Exponential backoff
                    logger.info(f"Model is loading. Waiting {wait_time} seconds before retry.")
                    sleep(wait_time)
                    continue
                
                # Check for service unavailability
                if response.status_code == 503:
                    logger.error(f"Hugging Face API service unavailable (503). Attempt {attempt+1}/{max_retries}")
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
                    logger.error(f"API request failed with 400 error: {error_text}")
                    
                    if "token" in error_text.lower() and "limit" in error_text.lower():
                        # If it's a token limit issue, try to reduce the input size
                        if "inputs" in payload and isinstance(payload["inputs"], str):
                            # Reduce input size by half for the next attempt
                            payload["inputs"] = payload["inputs"][:len(payload["inputs"])//2]
                            logger.info(f"Reduced input size to {len(payload['inputs'])} characters for next attempt")
                            continue
                
                # Raise exception for other errors
                response.raise_for_status()
                
                # Log successful response
                logger.info(f"Hugging Face API call successful")
                return response.json()
            
            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed (attempt {attempt+1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    raise
                sleep(1)  # Wait before retrying
        
        raise Exception("Failed to get response from Hugging Face API after multiple attempts")
    
    def summarize_text(self, text: str, max_length: int = 150, min_length: int = 50) -> str:
        """Summarize text using Hugging Face model or fallback method."""
        try:
            if self.summarizer:
                # Ensure text is within token limits
                if len(text) > self.chunk_size:
                    text = text[:self.chunk_size]
                
                summary = self.summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
                return summary[0]['summary_text']
            else:
                # Fallback method: simple extractive summarization
                return self._fallback_summarize(text, max_length)
        except Exception as e:
            logger.error(f"Error summarizing text: {str(e)}")
            return self._fallback_summarize(text, max_length)
    
    def _fallback_summarize(self, text: str, max_length: int = 150) -> str:
        """Simple extractive summarization as fallback."""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) <= 3:
            return text
        
        # Take first sentence, a middle sentence, and last sentence
        summary = sentences[0] + " " + sentences[len(sentences)//2] + " " + sentences[-1]
        return summary[:max_length] + "..." if len(summary) > max_length else summary
    
    def extract_financial_metrics(self, text: str) -> List[Dict[str, Any]]:
        """Extract financial metrics from text using Hugging Face API or regex patterns."""
        try:
            if self.huggingface_api_key:
                # Use a more appropriate model for financial extraction
                financial_extraction_model = "google/flan-t5-large"
                
                # Limit text length to avoid token limit issues (T5-large has 512 token limit)
                # Only use the first 1500 characters (roughly 300-400 tokens) for the prompt
                limited_text = text[:1500]
                
                # Use a more appropriate prompt format for T5 models
                prompt = f"extract financial metrics: {limited_text}"
                
                payload = {
                    "inputs": prompt,
                    "parameters": {
                        "max_length": 256,
                        "temperature": 0.3
                    }
                }
                
                try:
                    response = self._call_huggingface_api(financial_extraction_model, payload)
                    
                    if isinstance(response, list) and len(response) > 0:
                        generated_text = response[0].get("generated_text", "")
                        logger.info(f"Hugging Face API response: {generated_text[:100]}...")
                        
                        # Parse the response to extract metrics
                        metrics = self._parse_metrics_from_text(generated_text)
                        if metrics:
                            logger.info(f"Successfully extracted {len(metrics)} metrics using Hugging Face API")
                            return metrics
                        
                        # If no metrics found, try with a different chunk of text
                        if len(text) > 1500:
                            logger.info("No metrics found in first chunk, trying with next chunk")
                            limited_text = text[1500:3000]
                            prompt = f"extract financial metrics: {limited_text}"
                            payload["inputs"] = prompt
                            
                            response = self._call_huggingface_api(financial_extraction_model, payload)
                            if isinstance(response, list) and len(response) > 0:
                                generated_text = response[0].get("generated_text", "")
                                metrics = self._parse_metrics_from_text(generated_text)
                                if metrics:
                                    logger.info(f"Successfully extracted {len(metrics)} metrics from second chunk")
                                    return metrics
                except Exception as api_error:
                    logger.error(f"Error calling Hugging Face API for metrics extraction: {str(api_error)}")
            
            # Fallback to regex pattern matching
            logger.info("Falling back to regex pattern matching for metrics extraction")
            return self._extract_metrics_with_regex(text)
                
        except Exception as e:
            logger.error(f"Error extracting financial metrics: {str(e)}")
            return self._extract_metrics_with_regex(text)
    
    def _parse_metrics_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse metrics from generated text."""
        metrics = []
        
        # Look for structured format like "Revenue: $10.5 billion"
        metric_patterns = [
            r'(Revenue|Sales|Income|Profit|Loss|EPS|EBITDA|Assets|Liabilities|Equity|Margin|Growth|ROI|ROE|ROA)[\s:]+\$?([\d\.,]+)[\s]*(million|billion|trillion|M|B|T|USD|EUR|GBP|%)?',
            r'(Net Income|Operating Income|Gross Profit|Total Revenue|Net Sales)[\s:]+\$?([\d\.,]+)[\s]*(million|billion|trillion|M|B|T|USD|EUR|GBP|%)?',
            r'(Total Assets|Total Liabilities|Total Equity|Cash Flow)[\s:]+\$?([\d\.,]+)[\s]*(million|billion|trillion|M|B|T|USD|EUR|GBP|%)?'
        ]
        
        # Try to find metrics in the text
        for pattern in metric_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.group(1).strip()
                value = match.group(2).strip()
                unit = match.group(3).strip() if match.group(3) else ""
                
                metrics.append({
                    "name": name,
                    "value": value,
                    "unit": unit,
                    "category": "financial"
                })
        
        # If no structured metrics found, try to parse line by line
        if not metrics:
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Try to extract metric name and value from each line
                parts = re.split(r'[:\-]', line, 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    value_part = parts[1].strip()
                    
                    # Extract numeric value and unit
                    value_match = re.search(r'([\d\.,]+)\s*([a-zA-Z%]+)?', value_part)
                    if value_match:
                        value = value_match.group(1)
                        unit = value_match.group(2) if value_match.group(2) else ""
                        
                        metrics.append({
                            "name": name,
                            "value": value,
                            "unit": unit,
                            "category": "financial"
                        })
        
        # Log the extracted metrics
        if metrics:
            logger.info(f"Parsed {len(metrics)} metrics from text: {metrics}")
        else:
            logger.warning(f"No metrics parsed from text: {text[:100]}...")
            
        return metrics
    
    def _extract_metrics_with_regex(self, text: str) -> List[Dict[str, Any]]:
        """Extract financial metrics using regex patterns."""
        metrics = []
        
        # Common financial metrics patterns
        patterns = [
            # Revenue/Sales patterns
            r'(Revenue|Sales)[\s:]+\$?([\d\.,]+)[\s]*(million|billion|trillion|M|B|T|USD|EUR|GBP)?',
            r'(Net Income|Operating Income|Gross Profit)[\s:]+\$?([\d\.,]+)[\s]*(million|billion|trillion|M|B|T|USD|EUR|GBP)?',
            r'(EPS|Earnings Per Share)[\s:]+\$?([\d\.,]+)',
            r'(EBITDA)[\s:]+\$?([\d\.,]+)[\s]*(million|billion|trillion|M|B|T|USD|EUR|GBP)?',
            r'(Operating Margin|Profit Margin|Gross Margin)[\s:]+\$?([\d\.,]+)[\s]*(%)?',
            r'(ROI|ROE|ROA|Return on Investment|Return on Equity|Return on Assets)[\s:]+\$?([\d\.,]+)[\s]*(%)?',
            r'(Total Assets|Total Liabilities|Total Equity)[\s:]+\$?([\d\.,]+)[\s]*(million|billion|trillion|M|B|T|USD|EUR|GBP)?',
            r'(Cash Flow|Free Cash Flow|Operating Cash Flow)[\s:]+\$?([\d\.,]+)[\s]*(million|billion|trillion|M|B|T|USD|EUR|GBP)?',
            r'(Dividend|Dividend Per Share)[\s:]+\$?([\d\.,]+)',
            r'(Market Cap|Market Capitalization)[\s:]+\$?([\d\.,]+)[\s]*(million|billion|trillion|M|B|T|USD|EUR|GBP)?'
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.group(1).strip()
                value = match.group(2).strip()
                unit = match.group(3).strip() if len(match.groups()) > 2 and match.group(3) else ""
                
                metrics.append({
                    "name": name,
                    "value": value,
                    "unit": unit,
                    "category": "financial"
                })
        
        return metrics
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment in text using Hugging Face or fallback method."""
        try:
            if self.text_generation:
                prompt = f"Analyze the sentiment of this text and classify it as positive, negative, or neutral: {text[:1000]}"
                
                result = self.text_generation(prompt, max_length=50, do_sample=False)[0]['generated_text']
                
                # Extract sentiment from result
                sentiment = "neutral"
                if "positive" in result.lower():
                    sentiment = "positive"
                elif "negative" in result.lower():
                    sentiment = "negative"
                
                return {
                    "sentiment": sentiment,
                    "explanation": result
                }
            else:
                # Fallback to simple keyword-based sentiment analysis
                return self._fallback_sentiment_analysis(text)
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
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
            explanation = "The text contains more positive keywords than negative ones."
        elif negative_count > positive_count:
            sentiment = "negative"
            explanation = "The text contains more negative keywords than positive ones."
        else:
            sentiment = "neutral"
            explanation = "The text contains a balanced mix of positive and negative keywords."
        
        return {
            "sentiment": sentiment,
            "explanation": explanation
        }
    
    def extract_risk_factors(self, text: str) -> List[str]:
        """Extract risk factors from text using Hugging Face or pattern matching."""
        try:
            if self.text_generation:
                prompt = f"Extract the key risk factors mentioned in this text: {text[:1000]}"
                
                response = self.text_generation(prompt, max_length=512, do_sample=False)[0]['generated_text']
                
                # Parse the response to extract risk factors
                risks = self._parse_risks_from_text(response)
                if risks:
                    return risks
            
            # Fallback to pattern matching
            return self._extract_risks_with_patterns(text)
                
        except Exception as e:
            logger.error(f"Error extracting risk factors: {str(e)}")
            return self._extract_risks_with_patterns(text)
    
    def _parse_risks_from_text(self, text: str) -> List[str]:
        """Parse risk factors from generated text."""
        risks = []
        
        # Split by common list markers
        lines = re.split(r'\n+|\d+\.\s+|\-\s+|\*\s+', text)
        
        for line in lines:
            line = line.strip()
            if len(line) > 20 and any(word in line.lower() for word in ['risk', 'challenge', 'threat', 'concern', 'uncertainty']):
                risks.append(line)
        
        return risks
    
    def _extract_risks_with_patterns(self, text: str) -> List[str]:
        """Extract risk factors using pattern matching."""
        risks = []
        
        # Look for risk section
        risk_section_pattern = r'(?i)(Risk Factors|Risks and Uncertainties|Principal Risks|Key Risks).*?(?=\n\s*\n|$)'
        risk_section_match = re.search(risk_section_pattern, text, re.DOTALL)
        
        if risk_section_match:
            risk_section = risk_section_match.group(0)
            
            # Extract bullet points or numbered items
            risk_items = re.findall(r'(?:\n\s*[\•\-\*]|\n\s*\d+\.)\s*(.*?)(?=\n\s*[\•\-\*]|\n\s*\d+\.|\n\s*\n|$)', risk_section, re.DOTALL)
            
            for item in risk_items:
                item = item.strip()
                if len(item) > 20:
                    risks.append(item)
        
        # If no structured risks found, look for risk-related sentences
        if not risks:
            sentences = re.split(r'(?<=[.!?])\s+', text)
            for sentence in sentences:
                if len(sentence) > 30 and any(word in sentence.lower() for word in ['risk', 'challenge', 'threat', 'concern', 'uncertainty']):
                    risks.append(sentence.strip())
        
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
    
    def analyze_report(self, text: str) -> Dict[str, Any]:
        """Perform comprehensive analysis of an annual report."""
        try:
            # Chunk the text to handle large reports
            chunks = self._chunk_text(text)
            
            # Extract financial metrics from the first few chunks (likely to contain financial data)
            metrics = []
            
            # Try to extract metrics using Hugging Face API first
            if self.huggingface_api_key:
                try:
                    # Use first chunk for financial metrics (usually in executive summary)
                    first_chunk_metrics = self.extract_financial_metrics(chunks[0])
                    metrics.extend(first_chunk_metrics)
                    
                    # If no metrics found, try with second chunk
                    if not metrics and len(chunks) > 1:
                        second_chunk_metrics = self.extract_financial_metrics(chunks[1])
                        metrics.extend(second_chunk_metrics)
                        
                    logger.info(f"Extracted {len(metrics)} metrics using Hugging Face API")
                except Exception as e:
                    logger.error(f"Error extracting metrics with Hugging Face API: {str(e)}")
            
            # If no metrics found with API, try regex on multiple chunks
            if not metrics:
                logger.info("No metrics found with API, using regex pattern matching")
                for chunk in chunks[:3]:
                    chunk_metrics = self._extract_metrics_with_regex(chunk)
                    metrics.extend(chunk_metrics)
            
            # If still no metrics, try more chunks with regex
            if not metrics and len(chunks) > 3:
                logger.info("No metrics found in first 3 chunks, searching in more chunks")
                for chunk in chunks[3:6]:
                    chunk_metrics = self._extract_metrics_with_regex(chunk)
                    metrics.extend(chunk_metrics)
            
            # Remove duplicates based on metric name
            unique_metrics = []
            metric_names = set()
            for metric in metrics:
                if metric["name"].lower() not in metric_names:
                    unique_metrics.append(metric)
                    metric_names.add(metric["name"].lower())
            
            # Extract risk factors from middle chunks (likely to contain risk section)
            risks = []
            for chunk in chunks[1:4]:
                chunk_risks = self.extract_risk_factors(chunk)
                risks.extend(chunk_risks)
            
            # Remove duplicates and limit to top 10
            unique_risks = list(dict.fromkeys([risk for risk in risks if risk]))[:10]
            
            # Generate summaries from first and last chunks
            executive_summary = self.summarize_text(chunks[0], max_length=200)
            
            # Get business outlook from last chunks (likely to contain forward-looking statements)
            outlook = self.generate_business_outlook(chunks[-2] if len(chunks) > 1 else chunks[0])
            
            # Analyze sentiment from executive summary
            sentiment = self.analyze_sentiment(executive_summary)
            
            logger.info(f"Analysis complete: {len(unique_metrics)} metrics, {len(unique_risks)} risks")
            
            return {
                "metrics": unique_metrics,
                "risks": unique_risks,
                "summaries": {
                    "executive": executive_summary,
                    "outlook": outlook
                },
                "sentiment": sentiment
            }
        except Exception as e:
            logger.error(f"Error analyzing report: {str(e)}")
            return {
                "metrics": [],
                "risks": [],
                "summaries": {
                    "executive": "Error generating executive summary.",
                    "outlook": "Error generating business outlook."
                },
                "sentiment": {
                    "sentiment": "neutral",
                    "explanation": "Error analyzing sentiment."
                }
            }
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks for processing."""
        if not text:
            return []
        
        # Simple chunking by character count with overlap
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            
            # If not at the end, try to break at a sentence boundary
            if end < len(text):
                # Look for sentence boundary within the last 20% of the chunk
                boundary_search_start = max(start + int(self.chunk_size * 0.8), start)
                sentence_boundary = text.rfind('. ', boundary_search_start, end)
                if sentence_boundary != -1:
                    end = sentence_boundary + 1  # Include the period
            
            chunks.append(text[start:end])
            start = end - self.overlap_size if end - self.overlap_size > start else end
        
        return chunks 