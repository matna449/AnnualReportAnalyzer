#!/usr/bin/env python3
"""
Script to set up API keys for the Annual Report Analyzer.
This script will update the .env file with your API keys.
"""

import os
import sys
from dotenv import load_dotenv

def setup_api_keys():
    """Set up API keys for the Annual Report Analyzer."""
    # Check if .env file exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_file):
        print("Error: .env file not found. Please make sure you have a .env file in the backend directory.")
        print("You can copy the .env.example file to .env and then run this script.")
        return False
    
    # Load current environment variables
    load_dotenv(env_file)
    
    # Get Hugging Face API key
    huggingface_api_key = input("Enter your Hugging Face API key (press Enter to skip): ").strip()
    
    # Get Claude API key (optional)
    claude_api_key = input("Enter your Claude API key (press Enter to skip): ").strip()
    
    # Read the current .env file
    with open(env_file, 'r') as f:
        env_content = f.read()
    
    # Update the API keys
    if huggingface_api_key:
        env_content = env_content.replace(
            "HUGGINGFACE_API_KEY=your_huggingface_api_key_here", 
            f "HUGGINGFACE_API_KEY={huggingface_api_key}"
        )
        print("Hugging Face API key updated.")
    
    if claude_api_key:
        env_content = env_content.replace(
            "CLAUDE_API_KEY=your_claude_api_key_here", 
            f"CLAUDE_API_KEY={claude_api_key}"
        )
        print("Claude API key updated.")
    
    # Write the updated content back to the .env file
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print("\nAPI keys have been updated in the .env file.")
    print("You can now start the backend server with: python -m backend.main")
    return True

if __name__ == "__main__":
    print("Annual Report Analyzer - API Key Setup")
    print("======================================")
    print("This script will help you set up your API keys for the Annual Report Analyzer.")
    print("You'll need a Hugging Face API key to use the AI features.")
    print("The Claude API key is optional but recommended for better analysis results.")
    print("\nYou can get a Hugging Face API key at: https://huggingface.co/settings/tokens")
    print("You can get a Claude API key at: https://console.anthropic.com/settings/keys")
    print("\n")
    
    setup_api_keys() 