import pytest
import os
from unittest.mock import patch, MagicMock
from services.ai_service import AIService

# Sample financial text for testing
SAMPLE_FINANCIAL_TEXT = """
Annual Report 2023

Financial Highlights:
- Revenue: $10.5 billion, up 5% year-over-year
- Net Income: $2.3 billion, representing a 3% increase
- Earnings Per Share (EPS): $4.56, compared to $4.32 in the previous year
- Operating Margin: 22.5%
- Return on Equity (ROE): 15.3%

Risk Factors:
The company faces several risks that could affect future performance:
- Market volatility and economic uncertainty
- Increasing competition in key markets
- Regulatory changes affecting our industry
- Supply chain disruptions
- Cybersecurity threats

Business Outlook:
We expect continued growth in 2024, with revenue projected to increase by 4-6%. 
Our strategic investments in technology and expansion into emerging markets will 
drive long-term value for shareholders.
"""

class TestAIService:
    """Tests for the AIService class with FinBERT model."""
    
    @pytest.fixture
    def ai_service(self):
        """Create an instance of AIService for testing."""
        # Set up environment variables for testing
        os.environ["HUGGINGFACE_API_KEY"] = "test_api_key"
        os.environ["CHUNK_SIZE"] = "1000"
        os.environ["OVERLAP_SIZE"] = "100"
        
        # Create and return the service
        service = AIService()
        
        # Mock the API key validation to avoid actual API calls
        service.is_api_key_valid = True
        
        return service
    
    @patch('services.ai_service.requests.post')
    def test_call_finbert_api(self, mock_post, ai_service):
        """Test the _call_finbert_api method."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"label": "positive", "score": 0.95}]
        mock_post.return_value = mock_response
        
        # Call the method
        result = ai_service._call_finbert_api("Test financial text")
        
        # Verify the result
        assert result == [{"label": "positive", "score": 0.95}]
        
        # Verify the API was called correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer test_api_key"
        assert kwargs["json"]["inputs"] == "Test financial text"
    
    def test_chunk_text(self, ai_service):
        """Test the _chunk_text method."""
        # Create a long text
        long_text = "This is a test. " * 100
        
        # Call the method
        chunks = ai_service._chunk_text(long_text)
        
        # Verify the result
        assert len(chunks) > 1
        assert chunks[0].startswith("This is a test.")
        
        # Check for overlap
        assert chunks[0][-50:] in chunks[1]
    
    @patch('services.ai_service.AIService._call_finbert_api')
    def test_analyze_sentiment(self, mock_api_call, ai_service):
        """Test the analyze_sentiment method."""
        # Mock the API response
        mock_api_call.return_value = [{"label": "positive", "score": 0.85}]
        
        # Call the method
        result = ai_service.analyze_sentiment(SAMPLE_FINANCIAL_TEXT)
        
        # Verify the result
        assert result["sentiment"] == "positive"
        assert "explanation" in result
        assert result["score"] > 0.8
        
        # Test fallback when API fails
        mock_api_call.side_effect = Exception("API error")
        result = ai_service.analyze_sentiment(SAMPLE_FINANCIAL_TEXT)
        
        # Verify fallback result
        assert "sentiment" in result
        assert "explanation" in result
    
    def test_extract_financial_metrics_with_regex(self, ai_service):
        """Test the _extract_metrics_with_regex method."""
        # Call the method
        metrics = ai_service._extract_metrics_with_regex(SAMPLE_FINANCIAL_TEXT)
        
        # Verify the result
        assert len(metrics) >= 5  # Should find at least 5 metrics
        
        # Check for specific metrics
        metric_names = [m["name"].lower() for m in metrics]
        assert any("revenue" in name for name in metric_names)
        assert any("income" in name for name in metric_names)
        assert any("eps" in name or "earnings per share" in name for name in metric_names)
        assert any("margin" in name for name in metric_names)
        assert any("return" in name or "roe" in name for name in metric_names)
    
    @patch('services.ai_service.AIService._call_finbert_api')
    def test_extract_risk_factors(self, mock_api_call, ai_service):
        """Test the extract_risk_factors method."""
        # Mock the API response
        mock_api_call.return_value = [{"label": "negative", "score": 0.75}]
        
        # Call the method
        risks = ai_service.extract_risk_factors(SAMPLE_FINANCIAL_TEXT)
        
        # Verify the result
        assert len(risks) > 0
        assert any("competition" in risk.lower() for risk in risks)
        
        # Test fallback when API fails
        mock_api_call.side_effect = Exception("API error")
        risks = ai_service.extract_risk_factors(SAMPLE_FINANCIAL_TEXT)
        
        # Verify fallback result
        assert len(risks) > 0
    
    @patch('services.ai_service.AIService.extract_financial_metrics')
    @patch('services.ai_service.AIService.extract_risk_factors')
    @patch('services.ai_service.AIService.generate_summary')
    @patch('services.ai_service.AIService.analyze_sentiment')
    def test_analyze_report_text(self, mock_sentiment, mock_summary, mock_risks, mock_metrics, ai_service):
        """Test the analyze_report_text method."""
        # Mock the component methods
        mock_metrics.return_value = [{"name": "Revenue", "value": "10.5", "unit": "billion"}]
        mock_risks.return_value = ["Market volatility", "Competition"]
        mock_summary.side_effect = ["Executive summary", "Business outlook"]
        mock_sentiment.return_value = {"sentiment": "positive", "explanation": "Good results", "score": 0.8}
        
        # Call the method
        result = ai_service.analyze_report_text(SAMPLE_FINANCIAL_TEXT)
        
        # Verify the result
        assert result["status"] == "success"
        assert len(result["metrics"]) == 1
        assert len(result["risks"]) == 2
        assert result["executive_summary"] == "Executive summary"
        assert result["business_outlook"] == "Business outlook"
        assert result["sentiment"]["sentiment"] == "positive"
        
        # Test error handling
        mock_metrics.side_effect = Exception("Metrics error")
        mock_risks.side_effect = Exception("Risks error")
        mock_summary.side_effect = Exception("Summary error")
        mock_sentiment.side_effect = Exception("Sentiment error")
        
        result = ai_service.analyze_report_text(SAMPLE_FINANCIAL_TEXT)
        
        # Verify error handling
        assert result["status"] == "error"
        assert "message" in result 