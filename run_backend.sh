#!/bin/bash

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r backend/requirements.txt

# Set up API keys if needed
if [ ! -f "backend/.env" ]; then
    echo "Creating .env file from example..."
    cp backend/.env.example backend/.env
fi

if grep -q "your_huggingface_api_key_here" backend/.env; then
    echo "Setting up API keys..."
    python backend/setup_api_keys.py
fi

# Ask if user wants to generate sample data
read -p "Do you want to generate sample data for testing? (y/n): " generate_data
if [[ $generate_data == "y" || $generate_data == "Y" ]]; then
    echo "Generating sample data..."
    python backend/utils/generate_sample_data.py
fi

# Run the backend server
echo "Starting backend server..."
python -m backend.main 