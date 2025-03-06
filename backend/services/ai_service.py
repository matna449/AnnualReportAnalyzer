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

# Import shared utilities
from services.nlp_utils import (
    chunk_text,
    extract_metrics_with_regex,
    extract_risk_factors_with_regex,
    fallback_sentiment_analysis,
    extract_basic_entities
)

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class AIService:
    """
    High-level service for AI analysis of financial reports.
    Acts as an orchestrator using HuggingFaceService for model interactions.
    """
    
    def __init__(self):
        """Initialize the AI service with dependencies and configuration."""
        self.huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")
        
        # Import and initialize HuggingFaceService
        from services.huggingface_service import HuggingFaceService
        self.huggingface_service = HuggingFaceService()
        
        # Configure chunking parameters
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "4000"))
        self.overlap_size = int(os.getenv("OVERLAP_SIZE", "200"))
        
        # Validate API key
        self.is_api_key_valid = self._validate_api_key()
        
        logger.info("AIService initialized")
    
    def _validate_api_key(self):
        """
        Validate the Hugging Face API key.
        
        Returns:
            bool: True if the API key is valid, False otherwise
        """
        self.is_api_key_valid = False
        
        if not self.huggingface_api_key:
            logger.warning("No Hugging Face API key provided in environment variables.")
            return False
            
        if len(self.huggingface_api_key) < 8:  # Basic length check
            logger.warning("Hugging Face API key appears to be invalid (too short).")
            return False
            
        # Test API key with a simple request to the FinBERT model
        try:
            headers = {"Authorization": f"Bearer {self.huggingface_api_key}"}
            # Use a simple test request to validate the API key
            response = requests.post(
                "https://api-inference.huggingface.co/models/ProsusAI/finbert",
                headers=headers,
                json={"inputs": "The company reported strong financial results."},
                timeout=5
            )
            
            # Log response details for debugging
            logger.debug(f"FinBERT API validation - Status code: {response.status_code}")
            
            if response.status_code == 200:
                self.is_api_key_valid = True
                logger.info("Hugging Face API key validated successfully for FinBERT model.")
            elif response.status_code == 401:
                logger.error("Hugging Face API key is invalid for FinBERT model (401 Unauthorized).")
            else:
                logger.warning(f"FinBERT API key validation returned status code: {response.status_code}")
            
            return self.is_api_key_valid
                
        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}")
            return False
    
    def extract_financial_metrics(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract financial metrics from text using regex patterns.
        
        Args:
            text: Financial text to analyze
            
        Returns:
            List of dictionaries containing extracted metrics
        """
        logger.info(f"Extracting financial metrics from text of length {len(text)}")
        
        # Use the shared utility function to extract metrics
        metrics = extract_metrics_with_regex(text)
        
        # Post-process metrics for consistency
        processed_metrics = []
        for metric in metrics:
            # Standardize metric name and category
            metric["name"] = self._determine_metric_name(metric["name"], metric.get("context", ""))
            metric["category"] = self._determine_category(metric["category"])
            metric["unit"] = self._standardize_unit(metric["unit"])
            
            processed_metrics.append(metric)
        
        logger.info(f"Extracted {len(processed_metrics)} financial metrics")
        return processed_metrics
    
    def _determine_metric_name(self, name: str, context: str) -> str:
        """
        Determine the standardized name for a financial metric.
        
        Args:
            name: Original metric name
            context: Context in which the metric appears
            
        Returns:
            Standardized metric name
        """
        name_lower = name.lower()
        
        # Revenue-related metrics
        if "revenue" in name_lower:
            if "total" in name_lower or "net" in name_lower:
                return "Total Revenue"
            return "Revenue"
            
        # Income-related metrics
        if "net income" in name_lower:
            return "Net Income"
        if "income" in name_lower:
            return "Income"
            
        # Profit-related metrics
        if "gross profit" in name_lower:
            return "Gross Profit"
        if "operating profit" in name_lower:
            return "Operating Profit"
        if "profit" in name_lower:
            return "Profit"
            
        # EPS-related metrics
        if "earnings per share" in name_lower or "eps" in name_lower:
            return "EPS"
            
        # Context-based determination
        context_lower = context.lower()
        if "revenue" in context_lower and name_lower in ["increase", "decrease"]:
            return "Revenue Growth"
        if "income" in context_lower and name_lower in ["increase", "decrease"]:
            return "Income Growth"
        
        # Return the original name with proper capitalization
        return name.title()
    
    def _standardize_unit(self, unit: str) -> str:
        """
        Standardize the unit for a financial metric.
        
        Args:
            unit: Original unit string
            
        Returns:
            Standardized unit string
        """
        if not unit:
            return ""
            
        unit_lower = unit.lower().strip()
        
        # Standardize abbreviations
        if unit_lower in ["m", "mil", "million"]:
            return "million"
        if unit_lower in ["b", "bil", "billion"]:
            return "billion"
        if unit_lower in ["k", "thousand"]:
            return "thousand"
        if unit_lower in ["t", "trillion"]:
            return "trillion"
            
        # Currency symbols
        if unit_lower in ["$", "usd"]:
            return "USD"
        if unit_lower in ["€", "eur"]:
            return "EUR"
        if unit_lower in ["£", "gbp"]:
            return "GBP"
        if unit_lower in ["¥", "jpy", "cny"]:
            return "JPY"
            
        # Percentages
        if unit_lower in ["%", "percent", "percentage"]:
            return "%"
            
        # Return the original unit if not recognized
        return unit
    
    def _determine_category(self, category: str) -> str:
        """
        Determine the standardized category for a financial metric.
        
        Args:
            category: Original category string
            
        Returns:
            Standardized category string
        """
        if not category:
            return "Other"
            
        category_lower = category.lower()
        
        # Standardize common categories
        if "income" in category_lower or "revenue" in category_lower:
            return "Income Statement"
        if "balance" in category_lower or "asset" in category_lower:
            return "Balance Sheet"
        if "cash" in category_lower or "flow" in category_lower:
            return "Cash Flow"
        if "ratio" in category_lower:
            return "Financial Ratios"
            
        # Return the original category with proper capitalization
        return category.title()
    
    def extract_risk_factors(self, text: str) -> List[str]:
        """
        Extract risk factors from financial text.
        
        Args:
            text: Financial text to analyze
            
        Returns:
            List of extracted risk factors
        """
        logger.info(f"Extracting risk factors from text of length {len(text)}")
        
        try:
            # Delegate to HuggingFaceService for risk analysis
            if self.is_api_key_valid:
                risk_analysis = self.huggingface_service.analyze_risk(text)
                risks = risk_analysis.get("risks", [])
                logger.info(f"Extracted {len(risks)} risk factors using HuggingFace models")
                return risks
        except Exception as e:
            logger.error(f"Error using HuggingFace for risk factor extraction: {str(e)}")
        
        # Fallback to regex-based extraction
        risks = extract_risk_factors_with_regex(text)
        logger.info(f"Extracted {len(risks)} risk factors using fallback regex method")
        return risks
    
    def generate_business_outlook(self, text: str) -> str:
        """
        Generate a business outlook summary from financial text.
        
        Args:
            text: Financial text to analyze
            
        Returns:
            Business outlook summary
        """
        logger.info(f"Generating business outlook from text of length {len(text)}")
        
        # Extract outlook statements using regex patterns
        outlook = self._extract_outlook_statements(text)
        
        if not outlook:
            # Use HuggingFaceService if available
            try:
                summary = self.huggingface_service.generate_summary(text)
                outlook = summary.get("summary", "")
                if outlook:
                    logger.info(f"Generated business outlook using HuggingFace models")
                    return outlook
            except Exception as e:
                logger.error(f"Error generating business outlook with HuggingFace: {str(e)}")
        
        logger.info(f"Generated business outlook of length {len(outlook)}")
        return outlook
    
    def _extract_outlook_statements(self, text: str) -> str:
        """
        Extract outlook statements from financial text using regex patterns.
        
        Args:
            text: Financial text to analyze
            
        Returns:
            Extracted outlook statements as a string
        """
        # Look for outlook section headers
        outlook_headers = [
            r'business outlook',
            r'future outlook',
            r'outlook',
            r'forward[ -]looking statements',
            r'future prospects',
            r'guidance'
        ]
        
        # Extract text after outlook headers
        outlook_statements = []
        for header in outlook_headers:
            pattern = re.compile(f'(?i){header}[:\\s]+(.*?)(?=\\n\\n|\\.$)', re.DOTALL)
            matches = pattern.findall(text)
            outlook_statements.extend(matches)
        
        # If no headers found, look for outlook keywords in sentences
        if not outlook_statements:
            outlook_keywords = [
                r'expect[s]? to',
                r'anticipate[s]?',
                r'project[s]?',
                r'forecast[s]?',
                r'guidance',
                r'outlook',
                r'future',
                r'coming year',
                r'next year'
            ]
            
            sentences = re.split(r'(?<=[.!?])\s+', text)
            for sentence in sentences:
                if any(re.search(f'(?i){keyword}', sentence) for keyword in outlook_keywords):
                    outlook_statements.append(sentence)
        
        # Combine all outlook statements
        outlook = " ".join(outlook_statements)
        return outlook
    
    def generate_summary(self, text: str, summary_type: str = "executive") -> str:
        """
        Generate a summary of financial text.
        
        Args:
            text: Financial text to summarize
            summary_type: Type of summary to generate ("executive", "brief", etc.)
            
        Returns:
            Generated summary as a string
        """
        logger.info(f"Generating {summary_type} summary for text of length {len(text)}")
        
        try:
            # Extract metrics to include in the summary
            metrics = self.extract_financial_metrics(text)
            
            # Use HuggingFaceService to generate the summary
            summary_result = self.huggingface_service.generate_summary(text, metrics)
            summary = summary_result.get("summary", "")
            
            if summary:
                logger.info(f"Generated {summary_type} summary of length {len(summary)} using HuggingFace")
                return summary
        except Exception as e:
            logger.error(f"Error generating summary with HuggingFace: {str(e)}")
        
        # Fallback to extractive summarization
        summary = self._fallback_summary(text, summary_type)
        logger.info(f"Generated {summary_type} summary of length {len(summary)} using fallback method")
        return summary
    
    def _fallback_summary(self, text: str, summary_type: str) -> str:
        """
        Generate a fallback summary when model-based summarization fails.
        
        Args:
            text: Text to summarize
            summary_type: Type of summary to generate
            
        Returns:
            Extractive summary
        """
        logger.info(f"Using fallback method for {summary_type} summary generation")
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Define important keywords based on summary type
        if summary_type == "executive":
            important_keywords = [
                "key", "important", "significant", "highlight", "executive", "summary",
                "revenue", "profit", "growth", "increase", "decrease", "performance",
                "fiscal year", "quarter", "annual", "financial", "earnings"
            ]
        elif summary_type == "brief":
            important_keywords = [
                "summary", "overview", "brief", "highlight",
                "report", "financial", "statement"
            ]
        else:
            important_keywords = [
                "key", "important", "significant", "highlight", "summary", "report", "financial"
            ]
        
        # Score sentences based on importance
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
        num_sentences = 10 if summary_type == "executive" else 5
        top_sentences = [s[0] for s in sentence_scores[:num_sentences]]
        
        # Combine into summary
        summary = " ".join(top_sentences)
        return summary
    
    def analyze_financial_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze financial text to extract insights, metrics, and summaries.
        
        Args:
            text: Financial text to analyze
            
        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Analyzing financial text of length {len(text)}")
        
        # Track component errors
        component_errors = {
            "metrics": False,
            "executive_summary": False,
            "business_outlook": False,
            "sentiment": False,
            "entities": False,
            "risk_analysis": False
        }
        
        # Extract financial metrics
        metrics = {}
        try:
            metrics = self.extract_financial_metrics(text)
            logger.info(f"Extracted {len(metrics)} financial metrics")
        except Exception as e:
            logger.error(f"Error extracting financial metrics: {str(e)}")
            component_errors["metrics"] = True
        
        # Generate executive summary using HuggingFaceService
        executive_summary = {}
        try:
            executive_summary = self.huggingface_service.generate_summary(text, metrics)
            logger.info(f"Generated executive summary using HuggingFace: {len(executive_summary.get('summary', ''))} characters")
        except Exception as e:
            logger.error(f"Error generating executive summary with HuggingFace: {str(e)}")
            component_errors["executive_summary"] = True
            # Fallback to traditional method
            try:
                executive_summary = {"summary": self.generate_summary(text, "executive")}
                logger.info(f"Generated executive summary using fallback method: {len(executive_summary.get('summary', ''))} characters")
            except Exception as fallback_error:
                logger.error(f"Error generating executive summary with fallback: {str(fallback_error)}")
        
        # Generate business outlook
        business_outlook = ""
        try:
            business_outlook = self.generate_business_outlook(text)
            logger.info(f"Generated business outlook: {len(business_outlook)} characters")
        except Exception as e:
            logger.error(f"Error generating business outlook: {str(e)}")
            component_errors["business_outlook"] = True
        
        # Analyze sentiment using HuggingFaceService
        sentiment = {}
        try:
            sentiment = self.huggingface_service.analyze_sentiment(text)
            logger.info(f"Sentiment analysis completed: {sentiment.get('sentiment', 'unknown')}")
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            component_errors["sentiment"] = True
            sentiment = fallback_sentiment_analysis(text)
        
        # Extract entities using HuggingFaceService
        entities = {}
        try:
            entity_results = self.huggingface_service.extract_entities(text)
            entities = entity_results.get('entities', {})
            logger.info(f"Entity extraction completed")
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            component_errors["entities"] = True
            entities = extract_basic_entities(text)
        
        # Process risk analysis
        risk_analysis = {}
        try:
            risk_analysis = self.huggingface_service.analyze_risk(text)
            logger.info(f"Risk analysis completed")
        except Exception as e:
            logger.error(f"Error in risk analysis: {str(e)}")
            component_errors["risk_analysis"] = True
            risk_analysis = {"risks": self.extract_risk_factors(text)}
        
        # Return analysis results
        return {
            "status": "success" if not any(component_errors.values()) else "partial",
            "metrics": metrics,
            "risks": risk_analysis.get("risks", []),
            "executive_summary": executive_summary.get("summary", ""),
            "business_outlook": business_outlook,
            "sentiment": sentiment,
            "entities": entities,
            "component_errors": component_errors,
            "insights": self._generate_insights({
                "metrics": metrics,
                "sentiment": sentiment,
                "risks": risk_analysis.get("risks", []),
                "entities": entities
            })
        }
    
    def analyze_report(self, report_text: str) -> Dict[str, Any]:
        """
        Analyze a financial report and extract insights.
        
        Args:
            report_text: Text of the financial report
            
        Returns:
            Dictionary with analysis results
        """
        start_time = time.time()
        logger.info(f"Starting report analysis ({len(report_text)} characters)")
        
        try:
            # Check if API key is valid
            if not self.is_api_key_valid:
                logger.warning("No valid Hugging Face API key. Using comprehensive fallback methods.")
                analysis_result = self._comprehensive_fallback_analysis(report_text)
                
                # Calculate processing time
                processing_time = time.time() - start_time
                logger.info(f"Report analysis completed in {processing_time:.2f} seconds (using fallback methods)")
                
                # Add processing metadata
                analysis_result["processing_time"] = f"{processing_time:.2f} seconds"
                analysis_result["processing_date"] = datetime.now().isoformat()
                analysis_result["model_used"] = "fallback methods"
                
                return analysis_result
            
            # If API key is valid, proceed with normal analysis
            analysis_result = self.analyze_financial_text(report_text)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            logger.info(f"Report analysis completed in {processing_time:.2f} seconds")
            
            # Add processing metadata
            analysis_result["processing_time"] = f"{processing_time:.2f} seconds"
            analysis_result["processing_date"] = datetime.now().isoformat()
            analysis_result["model_used"] = "matna449/my-finbert"
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing report: {str(e)}")
            processing_time = time.time() - start_time
            
            # Try fallback methods if main analysis fails
            try:
                logger.info("Main analysis failed, attempting fallback analysis")
                fallback_result = self._comprehensive_fallback_analysis(report_text)
                fallback_result["status"] = "partial"
                fallback_result["error_info"] = f"Primary analysis failed: {str(e)}"
                fallback_result["processing_time"] = f"{processing_time:.2f} seconds"
                fallback_result["processing_date"] = datetime.now().isoformat()
                fallback_result["model_used"] = "fallback methods (after primary failure)"
                
                return fallback_result
            except Exception as fallback_error:
                logger.error(f"Fallback analysis also failed: {str(fallback_error)}")
                
                # Return error result with as much information as possible
                return {
                    "status": "error",
                    "message": f"Error analyzing report: {str(e)}",
                    "fallback_error": f"Fallback analysis also failed: {str(fallback_error)}",
                    "metrics": [],
                    "risks": [],
                    "executive_summary": "",
                    "business_outlook": "",
                    "sentiment": {"sentiment": "neutral", "explanation": "Analysis failed"},
                    "processing_time": f"{processing_time:.2f} seconds",
                    "processing_date": datetime.now().isoformat(),
                    "model_used": "none (all methods failed)"
                }
    
    def _comprehensive_fallback_analysis(self, text: str) -> Dict[str, Any]:
        """
        Comprehensive fallback analysis when external services are unavailable.
        
        Args:
            text: Financial text to analyze
            
        Returns:
            Dictionary with analysis results
        """
        logger.info("Using comprehensive fallback analysis as HuggingFace services are unavailable")
        
        # Start timing
        start_time = time.time()
        
        # Extract metrics with regex patterns
        metrics = self.extract_financial_metrics(text)
        
        # Extract risk factors with regex patterns
        risks = extract_risk_factors_with_regex(text)
        
        # Generate a basic summary using text extraction
        summary = self._fallback_summary(text, "executive")
        
        # Generate a basic business outlook
        outlook = self._extract_outlook_statements(text)
        
        # Analyze sentiment using fallback method
        sentiment = fallback_sentiment_analysis(text)
        
        # Extract basic entities
        entities = extract_basic_entities(text)
        
        # Generate insights
        insights = self._generate_insights({
            "metrics": metrics,
            "sentiment": sentiment,
            "risks": risks,
            "entities": entities
        })
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        return {
            "status": "success",
            "metrics": metrics,
            "risks": risks,
            "executive_summary": summary,
            "business_outlook": outlook,
            "sentiment": sentiment,
            "entities": entities,
            "insights": insights,
            "processing_time": f"{processing_time:.2f} seconds",
            "model_used": "fallback_methods"
        }
    
    def _generate_insights(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate insights based on the analyzed report data.
        
        This method processes the results of various analysis components (metrics, sentiment,
        risks, and entities) to produce high-level insights about the financial report.
        The generated insights include:
        - Key points: Important observations extracted from the analysis
        - Trends: Identified patterns or trends in the financial data
        - Recommendations: Actionable suggestions based on the analysis
        
        If any component of the analysis fails, this method will still attempt to
        generate insights from the available data, ensuring robustness in the pipeline.
        
        Args:
            analysis_data: Dictionary containing the following keys:
                - metrics: List of extracted financial metrics
                - sentiment: Dictionary with sentiment analysis results
                - risks: List of identified risk factors
                - entities: Dictionary of extracted entities (organizations, locations, etc.)
            
        Returns:
            Dictionary with the following keys:
                - key_points: List of important observations
                - trends: List of identified trends
                - recommendations: List of actionable recommendations
        
        Note:
            This method is called during the report analysis process and its output
            is included in the final analysis result returned to the frontend.
        """
        logger.info("Generating insights from analysis data")
        
        try:
            metrics = analysis_data.get("metrics", [])
            sentiment = analysis_data.get("sentiment", {})
            risks = analysis_data.get("risks", [])
            entities = analysis_data.get("entities", {})
            
            # Initialize insights dictionary
            insights = {
                "key_points": [],
                "trends": [],
                "recommendations": []
            }
            
            # Extract key points based on metrics
            if metrics:
                logger.info(f"Generating key points from {len(metrics)} metrics")
                
                # Look for year-over-year changes in key metrics
                revenue_metrics = [m for m in metrics if m.get("name", "").lower() in ["revenue", "total revenue", "net revenue"]]
                profit_metrics = [m for m in metrics if m.get("name", "").lower() in ["net income", "profit", "earnings"]]
                
                if revenue_metrics:
                    insights["key_points"].append(f"Revenue reported as {revenue_metrics[0].get('value')} {revenue_metrics[0].get('unit', '')}")
                
                if profit_metrics:
                    insights["key_points"].append(f"Net income reported as {profit_metrics[0].get('value')} {profit_metrics[0].get('unit', '')}")
            
            # Generate insights from sentiment analysis
            if sentiment and "sentiment" in sentiment:
                logger.info(f"Generating insights from sentiment: {sentiment.get('sentiment')}")
                sentiment_value = sentiment.get("sentiment", "neutral")
                explanation = sentiment.get("explanation", "")
                
                if sentiment_value == "positive":
                    insights["key_points"].append("Overall positive tone in the report, suggesting confidence in business performance")
                elif sentiment_value == "negative":
                    insights["key_points"].append("Overall negative tone in the report, suggesting challenges in business performance")
                elif sentiment_value == "mixed" or sentiment_value == "neutral":
                    insights["key_points"].append("Mixed or neutral tone in the report")
                
                if explanation:
                    insights["key_points"].append(explanation)
            
            # Extract insights from risks
            if risks:
                logger.info(f"Generating insights from {len(risks)} risk factors")
                # Limit to top 3 risks to avoid overwhelming the user
                top_risks = risks[:3]
                for risk in top_risks:
                    insights["key_points"].append(f"Risk factor identified: {risk}")
                
                insights["recommendations"].append("Monitor identified risk factors closely")
            
            # Extract insights from entity analysis
            if entities:
                logger.info(f"Generating insights from entity analysis")
                # Extract key entities like competitors, technologies, or market trends
                key_organizations = entities.get("organizations", [])[:3]
                
                for org in key_organizations:
                    insights["key_points"].append(f"Key organization mentioned: {org}")
            
            # Add general recommendations if none exist
            if not insights["recommendations"]:
                insights["recommendations"] = [
                    "Consider historical performance when evaluating current metrics",
                    "Compare with industry benchmarks for context",
                    "Review risk factors in detail for contingency planning"
                ]
            
            # Add generic trends if none identified
            if not insights["trends"]:
                insights["trends"] = [
                    "Financial data should be analyzed in the context of market conditions",
                    "Consider industry-wide trends when evaluating performance"
                ]
            
            logger.info(f"Generated {len(insights['key_points'])} key points, {len(insights['trends'])} trends, and {len(insights['recommendations'])} recommendations")
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            # Return basic fallback insights
            return {
                "key_points": ["Failed to generate detailed insights due to an error"],
                "trends": ["Unable to identify trends due to analysis error"],
                "recommendations": ["Review the full report manually to identify key insights"]
            } 