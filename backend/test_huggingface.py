import os
import logging
import requests
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("huggingface_test")

def read_api_key_from_env_file():
    """Read the Hugging Face API key directly from the .env file."""
    env_file_path = os.path.join(os.path.dirname(__file__), '.env')
    
    if not os.path.exists(env_file_path):
        logger.error(f"No .env file found at {env_file_path}")
        return None
    
    try:
        with open(env_file_path, 'r') as f:
            env_content = f.read()
            
        # Extract the API key using regex
        match = re.search(r'HUGGINGFACE_API_KEY=([^\s]+)', env_content)
        if match:
            return match.group(1)
        else:
            logger.error("No HUGGINGFACE_API_KEY found in .env file")
            return None
    except Exception as e:
        logger.error(f"Error reading .env file: {str(e)}")
        return None

def test_huggingface_api():
    """Test the Hugging Face API connection and token limits."""
    api_key = read_api_key_from_env_file()
    
    if not api_key:
        logger.error("No Hugging Face API key found in .env file")
        return False
    
    logger.info(f"Using Hugging Face API key: {api_key[:5]}...{api_key[-5:]}")
    
    # Test with different models
    models = [
        "google/flan-t5-large",
        "google/flan-t5-base"
    ]
    
    # Test with different prompt lengths
    test_prompts = [
        "extract financial metrics: Revenue: $10.5 billion, Net Income: $2.3 billion",
        "extract financial metrics: " + "Revenue: $10.5 billion, Net Income: $2.3 billion " * 10,  # Longer prompt
    ]
    
    success = True
    
    for model in models:
        logger.info(f"Testing model: {model}")
        
        for i, prompt in enumerate(test_prompts):
            logger.info(f"Testing prompt {i+1} with length {len(prompt)} characters")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_length": 256,
                    "temperature": 0.3
                }
            }
            
            url = f"https://api-inference.huggingface.co/models/{model}"
            
            try:
                logger.info(f"Sending request to {url}")
                response = requests.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Success! Response: {result}")
                else:
                    logger.error(f"Error: {response.status_code} - {response.text}")
                    success = False
                    
            except Exception as e:
                logger.error(f"Exception: {str(e)}")
                success = False
    
    return success

if __name__ == "__main__":
    logger.info("Starting Hugging Face API test")
    result = test_huggingface_api()
    if result:
        logger.info("All tests passed successfully!")
    else:
        logger.error("Some tests failed. Check the logs for details.") 