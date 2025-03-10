import os
import sys
import logging
import time
import unittest
from unittest.mock import patch, MagicMock
import random
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import the services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the HuggingFaceService
from services.huggingface_service import HuggingFaceService
from huggingface_hub import InferenceTimeoutError
from requests.exceptions import HTTPError

class TestHuggingFaceService(unittest.TestCase):
    """Test class for HuggingFaceService with both real and mock tests."""
    
    def setUp(self):
        """Set up test environment before each test."""
        # Sample test text for all tests
        self.test_text = """
        The company reported strong financial results for the fiscal year 2023. 
        Revenue increased by 15% to $1.2 billion, while net income grew by 20% to $300 million.
        The board of directors approved a dividend increase of 10% and authorized a new share repurchase program.
        Despite challenges in the global supply chain, the company maintained its market leadership position.
        """
        
        # Create a flag to determine if we should use mocks or real API
        self.use_mock = os.getenv("USE_MOCK_API", "true").lower() == "true"
        
        if self.use_mock:
            logger.info("Using mock API for tests")
            # Create a patched version of the service for testing
            self.patcher = patch('services.huggingface_service.InferenceClient')
            self.mock_client = self.patcher.start()
            
            # Configure the mock client
            self.mock_instance = self.mock_client.return_value
            
            # Set up mock responses
            self.mock_instance.text_classification.return_value = [
                {"label": "positive", "score": 0.75},
                {"label": "neutral", "score": 0.20},
                {"label": "negative", "score": 0.05}
            ]
            
            self.mock_instance.summarization.return_value = "This is a mock summary of the financial results."
            
            self.mock_instance.text_generation.return_value = "Generated analysis of the financial performance."
            
            self.mock_instance.token_classification.return_value = [
                {"entity_group": "ORG", "score": 0.95, "word": "company"},
                {"entity_group": "MONEY", "score": 0.90, "word": "$1.2 billion"},
                {"entity_group": "MONEY", "score": 0.85, "word": "$300 million"},
                {"entity_group": "PERCENT", "score": 0.80, "word": "15%"}
            ]
            
            # Initialize service with mocked client
            with patch.object(HuggingFaceService, '_validate_api_key', return_value=True):
                self.hf_service = HuggingFaceService()
        else:
            logger.info("Using real API for tests")
            # Initialize real service
            self.hf_service = HuggingFaceService()
            
    def tearDown(self):
        """Clean up after each test."""
        if self.use_mock:
            self.patcher.stop()
    
    def test_api_key_validation(self):
        """Test API key validation."""
        logger.info("Testing API key validation...")
        self.assertIsInstance(self.hf_service.is_api_key_valid, bool)
        logger.info(f"API key valid: {self.hf_service.is_api_key_valid}")
    
    def test_sentiment_analysis(self):
        """Test sentiment analysis functionality."""
        logger.info("Testing sentiment analysis...")
        sentiment_result = self.hf_service.analyze_sentiment(self.test_text)
        
        # Verify the result structure
        self.assertIn('sentiment', sentiment_result)
        self.assertIn('score', sentiment_result)
        self.assertIn('method', sentiment_result)
        
        logger.info(f"Sentiment: {sentiment_result['sentiment']}, Score: {sentiment_result['score']:.2f}")
        logger.info(f"Method used: {sentiment_result.get('method', 'unknown')}")
    
    def test_entity_extraction(self):
        """Test entity extraction functionality."""
        logger.info("Testing entity extraction...")
        entities_result = self.hf_service.extract_entities(self.test_text)
        
        # Verify the result structure
        self.assertIn('method', entities_result)
        self.assertIn('entities', entities_result)
        
        logger.info(f"Entities method: {entities_result.get('method', 'unknown')}")
        if 'entities' in entities_result:
            for entity_type, entities in entities_result['entities'].items():
                logger.info(f"  {entity_type}: {entities}")
    
    def test_risk_analysis(self):
        """Test risk analysis functionality."""
        logger.info("Testing risk analysis...")
        risk_result = self.hf_service.analyze_risk(self.test_text)
        
        # Verify the result structure
        self.assertIn('method', risk_result)
        self.assertIn('risk_score', risk_result)
        self.assertIn('risks', risk_result)
        
        logger.info(f"Risk method: {risk_result.get('method', 'unknown')}")
        logger.info(f"Risk score: {risk_result.get('risk_score', 0):.2f}")
        if 'risks' in risk_result:
            for i, risk in enumerate(risk_result['risks'][:3]):  # Show first 3 risks
                logger.info(f"  Risk {i+1}: {risk}")
    
    def test_summary_generation(self):
        """Test summary generation functionality."""
        logger.info("Testing summary generation...")
        summary_result = self.hf_service.generate_summary(self.test_text)
        
        # Verify the result structure
        self.assertIn('method', summary_result)
        self.assertIn('summary', summary_result)
        
        logger.info(f"Summary method: {summary_result.get('method', 'unknown')}")
        logger.info(f"Summary: {summary_result.get('summary', 'No summary generated')[:200]}...")
    
    @unittest.skipIf(os.getenv("USE_MOCK_API", "true").lower() != "true", "Skipping mock-only tests")
    def test_error_handling_503(self):
        """Test handling of 503 Service Unavailable errors."""
        logger.info("Testing 503 error handling...")
        
        # Create a mock response with 503 status
        mock_response = MagicMock()
        mock_response.status_code = 503
        
        # Create a HTTPError with the mock response
        http_error = HTTPError("503 Service Unavailable")
        http_error.response = mock_response
        
        # Configure the mock to raise the error once, then succeed
        self.mock_instance.token_classification.side_effect = [
            http_error,
            [{"entity_group": "ORG", "score": 0.95, "word": "company"}]
        ]
        
        # Test that the service handles the error and retries
        result = self.hf_service.extract_entities(self.test_text)
        
        # Verify we got a result despite the error
        self.assertIn('entities', result)
        logger.info("Successfully handled 503 error")
    
    @unittest.skipIf(os.getenv("USE_MOCK_API", "true").lower() != "true", "Skipping mock-only tests")
    def test_timeout_handling(self):
        """Test handling of timeout errors."""
        logger.info("Testing timeout error handling...")
        
        # Configure the mock to raise a timeout error once, then succeed
        self.mock_instance.summarization.side_effect = [
            InferenceTimeoutError("Request timed out"),
            "This is a summary after retry."
        ]
        
        # Test that the service handles the timeout and retries
        result = self.hf_service.generate_summary(self.test_text)
        
        # Verify we got a result despite the error
        self.assertIn('summary', result)
        logger.info("Successfully handled timeout error")
    
    @unittest.skipIf(os.getenv("USE_MOCK_API", "true").lower() != "true", "Skipping mock-only tests")
    def test_fallback_mechanisms(self):
        """Test fallback mechanisms when primary models fail."""
        logger.info("Testing fallback mechanisms...")
        
        # Configure the mock to always raise errors for the primary model
        self.mock_instance.summarization.side_effect = InferenceTimeoutError("Request timed out")
        
        # Test that the service falls back to alternative methods
        result = self.hf_service.generate_summary(self.test_text)
        
        # Verify we got a result despite the errors
        self.assertIn('summary', result)
        self.assertIn('method', result)
        # The method should indicate a mock response was used
        self.assertIn('mock', result['method'].lower())
        
        logger.info(f"Fallback method used: {result['method']}")
        logger.info("Successfully tested fallback mechanisms")

def run_tests():
    """Run the test suite."""
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

def test_huggingface_service():
    """Legacy test function that runs all tests in sequence."""
    logger.info("Initializing HuggingFaceService...")
    hf_service = HuggingFaceService()
    
    # Test API key validation
    logger.info(f"API key valid: {hf_service.is_api_key_valid}")
    
    # If API key is not valid, we'll use mock responses
    if not hf_service.is_api_key_valid:
        logger.warning("API key is not valid. Using mock responses for testing.")
    
    # Test sentiment analysis with a small text
    test_text = """
    The company reported strong financial results for the fiscal year 2023. 
    Revenue increased by 15% to $1.2 billion, while net income grew by 20% to $300 million.
    The board of directors approved a dividend increase of 10% and authorized a new share repurchase program.
    Despite challenges in the global supply chain, the company maintained its market leadership position.
    """
    
    try:
        logger.info("Testing sentiment analysis...")
        sentiment_result = hf_service.analyze_sentiment(test_text)
        logger.info(f"Sentiment: {sentiment_result['sentiment']}, Score: {sentiment_result['score']:.2f}")
        logger.info(f"Method used: {sentiment_result.get('method', 'unknown')}")
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
    
    try:
        # Test entity extraction
        logger.info("Testing entity extraction...")
        entities_result = hf_service.extract_entities(test_text)
        logger.info(f"Entities method: {entities_result.get('method', 'unknown')}")
        if 'entities' in entities_result:
            for entity_type, entities in entities_result['entities'].items():
                logger.info(f"  {entity_type}: {entities}")
    except Exception as e:
        logger.error(f"Error in entity extraction: {str(e)}")
    
    try:
        # Test risk analysis
        logger.info("Testing risk analysis...")
        risk_result = hf_service.analyze_risk(test_text)
        logger.info(f"Risk method: {risk_result.get('method', 'unknown')}")
        logger.info(f"Risk score: {risk_result.get('risk_score', 0):.2f}")
        if 'risks' in risk_result:
            for i, risk in enumerate(risk_result['risks'][:3]):  # Show first 3 risks
                logger.info(f"  Risk {i+1}: {risk}")
    except Exception as e:
        logger.error(f"Error in risk analysis: {str(e)}")
    
    try:
        # Test summary generation
        logger.info("Testing summary generation...")
        summary_result = hf_service.generate_summary(test_text)
        logger.info(f"Summary method: {summary_result.get('method', 'unknown')}")
        logger.info(f"Summary: {summary_result.get('summary', 'No summary generated')[:200]}...")
    except Exception as e:
        logger.error(f"Error in summary generation: {str(e)}")
    
    logger.info("All tests completed!")

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Check if we should run the legacy test or the unittest suite
    if os.getenv("USE_UNITTEST", "true").lower() == "true":
        logger.info("Running unittest test suite...")
        run_tests()
    else:
        logger.info("Running legacy test function...")
        test_huggingface_service() 