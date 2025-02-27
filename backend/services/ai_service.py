import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
import anthropic
import re
import json

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.claude_api_key = os.getenv("CLAUDE_API_KEY")
        self.model_name = os.getenv("MODEL_NAME", "google/flan-t5-large")
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "4000"))
        self.overlap_size = int(os.getenv("OVERLAP_SIZE", "200"))
        
        # Initialize Hugging Face model if API key is available
        if self.huggingface_api_key:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
                self.summarizer = pipeline("summarization", model=self.model, tokenizer=self.tokenizer)
                self.qa_pipeline = pipeline("question-answering", model=self.model, tokenizer=self.tokenizer)
                logger.info(f"Initialized Hugging Face model: {self.model_name}")
            except Exception as e:
                logger.error(f"Error initializing Hugging Face model: {str(e)}")
                self.tokenizer = None
                self.model = None
                self.summarizer = None
                self.qa_pipeline = None
        else:
            logger.warning("No Hugging Face API key provided. Some features may be limited.")
            self.tokenizer = None
            self.model = None
            self.summarizer = None
            self.qa_pipeline = None
        
        # Initialize Claude client if API key is available
        if self.claude_api_key:
            try:
                self.claude_client = anthropic.Anthropic(api_key=self.claude_api_key)
                logger.info("Initialized Claude API client")
            except Exception as e:
                logger.error(f"Error initializing Claude API client: {str(e)}")
                self.claude_client = None
        else:
            logger.warning("No Claude API key provided. Some features may be limited.")
            self.claude_client = None
    
    def summarize_text(self, text: str, max_length: int = 150, min_length: int = 50) -> str:
        """Summarize text using Hugging Face model."""
        if not self.summarizer:
            raise ValueError("Summarizer not initialized. Please check your Hugging Face API key.")
        
        try:
            # Ensure text is within token limits
            if len(text) > self.chunk_size:
                text = text[:self.chunk_size]
            
            summary = self.summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
            return summary[0]['summary_text']
        except Exception as e:
            logger.error(f"Error summarizing text: {str(e)}")
            return ""
    
    def extract_financial_metrics(self, text: str) -> List[Dict[str, Any]]:
        """Extract financial metrics from text using Claude API."""
        if not self.claude_client:
            raise ValueError("Claude API client not initialized. Please check your Claude API key.")
        
        try:
            prompt = f"""
            You are a financial analyst extracting key metrics from an annual report. 
            Extract all financial metrics from the following text. 
            For each metric, provide the name, value, and unit (if applicable).
            Format your response as a JSON array of objects with the following structure:
            [
                {{
                    "name": "Revenue",
                    "value": "394.3",
                    "unit": "billion USD",
                    "category": "financial"
                }},
                ...
            ]
            
            Text:
            {text}
            
            JSON Output:
            """
            
            response = self.claude_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                temperature=0,
                system="You are a financial analyst extracting structured data from annual reports. Always respond with valid JSON.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract JSON from response
            response_text = response.content[0].text
            json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                metrics = json.loads(json_str)
                return metrics
            else:
                logger.warning("No valid JSON found in Claude response")
                return []
                
        except Exception as e:
            logger.error(f"Error extracting financial metrics: {str(e)}")
            return []
    
    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment in text using Hugging Face."""
        if not self.model:
            raise ValueError("Model not initialized. Please check your Hugging Face API key.")
        
        try:
            prompt = f"Analyze the sentiment of this text and classify it as positive, negative, or neutral: {text}"
            
            inputs = self.tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True)
            outputs = self.model.generate(**inputs, max_length=50)
            result = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
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
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {"sentiment": "neutral", "explanation": "Error analyzing sentiment"}
    
    def extract_risk_factors(self, text: str) -> List[str]:
        """Extract risk factors from text using Claude API."""
        if not self.claude_client:
            raise ValueError("Claude API client not initialized. Please check your Claude API key.")
        
        try:
            prompt = f"""
            You are a financial analyst extracting risk factors from an annual report.
            Extract the key risk factors mentioned in the following text.
            Format your response as a JSON array of strings, each representing a distinct risk factor.
            
            Text:
            {text}
            
            JSON Output:
            """
            
            response = self.claude_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                temperature=0,
                system="You are a financial analyst extracting structured data from annual reports. Always respond with valid JSON.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract JSON from response
            response_text = response.content[0].text
            json_match = re.search(r'\[\s*".*"\s*\]', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                risks = json.loads(json_str)
                return risks
            else:
                logger.warning("No valid JSON found in Claude response")
                return []
                
        except Exception as e:
            logger.error(f"Error extracting risk factors: {str(e)}")
            return []
    
    def generate_business_outlook(self, text: str) -> str:
        """Generate a business outlook summary using Claude API."""
        if not self.claude_client:
            raise ValueError("Claude API client not initialized. Please check your Claude API key.")
        
        try:
            prompt = f"""
            You are a financial analyst summarizing the business outlook from an annual report.
            Based on the following text, provide a concise summary of the company's future outlook, 
            strategic plans, and growth expectations.
            
            Text:
            {text}
            
            Business Outlook Summary:
            """
            
            response = self.claude_client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=500,
                temperature=0,
                system="You are a financial analyst summarizing business outlooks from annual reports.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text.strip()
                
        except Exception as e:
            logger.error(f"Error generating business outlook: {str(e)}")
            return ""
    
    def answer_question(self, question: str, context: str) -> str:
        """Answer a specific question based on the provided context."""
        if not self.qa_pipeline:
            raise ValueError("QA pipeline not initialized. Please check your Hugging Face API key.")
        
        try:
            result = self.qa_pipeline(question=question, context=context)
            return result['answer']
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            return ""
    
    def analyze_report(self, text: str) -> Dict[str, Any]:
        """Perform comprehensive analysis of an annual report."""
        try:
            # Chunk the text to handle large reports
            chunks = self._chunk_text(text)
            
            # Extract financial metrics from the first few chunks (likely to contain financial data)
            metrics = []
            for chunk in chunks[:3]:
                chunk_metrics = self.extract_financial_metrics(chunk)
                metrics.extend(chunk_metrics)
            
            # Generate executive summary
            executive_summary = self.summarize_text(chunks[0], max_length=200, min_length=100)
            
            # Extract risk factors from later chunks (likely to contain risk section)
            risks = []
            for chunk in chunks[3:]:
                chunk_risks = self.extract_risk_factors(chunk)
                risks.extend(chunk_risks)
                if len(risks) >= 10:  # Limit to top 10 risks
                    risks = risks[:10]
                    break
            
            # Generate business outlook from the last chunks (likely to contain forward-looking statements)
            outlook = self.generate_business_outlook(chunks[-1])
            
            # Analyze sentiment of management discussion
            sentiment = self.analyze_sentiment(chunks[1])
            
            return {
                "metrics": metrics,
                "summaries": {
                    "executive": executive_summary,
                    "outlook": outlook
                },
                "risks": risks,
                "sentiment": sentiment
            }
        except Exception as e:
            logger.error(f"Error analyzing report: {str(e)}")
            return {
                "metrics": [],
                "summaries": {
                    "executive": "",
                    "outlook": ""
                },
                "risks": [],
                "sentiment": {"sentiment": "neutral", "explanation": ""}
            }
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks of appropriate size for the model."""
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            
            # If we're not at the end of the text, try to find a good breaking point
            if end < text_length:
                # Try to find a newline or period to break at
                newline_pos = text.rfind('\n', start, end)
                period_pos = text.rfind('. ', start, end)
                
                # Use the latest good breaking point
                if newline_pos > start + self.chunk_size // 2:
                    end = newline_pos + 1  # Include the newline
                elif period_pos > start + self.chunk_size // 2:
                    end = period_pos + 2  # Include the period and space
            
            # Add the chunk
            chunks.append(text[start:end])
            
            # Move the start position, accounting for overlap
            start = end - self.overlap_size if end < text_length else text_length
        
        return chunks 