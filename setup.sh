#!/bin/bash

# Annual Report Analyzer Setup Script
echo "===== Annual Report Analyzer Setup ====="
echo "This script will help you set up the Annual Report Analyzer project."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.9+ and try again."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Please install Node.js 18+ and try again."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "npm is not installed. Please install npm and try again."
    exit 1
fi

# Create Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install backend dependencies
echo "Installing backend dependencies..."
pip install -r backend/requirements.txt

# Set up API keys
if [ ! -f "backend/.env" ]; then
    echo "Creating .env file from example..."
    cp backend/.env.example backend/.env
fi

echo "Setting up API keys..."
python backend/setup_api_keys.py

# Create uploads directory if it doesn't exist
if [ ! -d "backend/uploads" ]; then
    echo "Creating uploads directory..."
    mkdir -p backend/uploads
    touch backend/uploads/.gitkeep
fi

# Install frontend dependencies
echo "Installing frontend dependencies..."
npm install

# Generate sample data
read -p "Do you want to generate sample data for testing? (y/n): " generate_data
if [[ $generate_data == "y" || $generate_data == "Y" ]]; then
    echo "Generating sample data..."
    python backend/utils/generate_sample_data.py
fi

# Make scripts executable
echo "Making scripts executable..."
chmod +x run_backend.sh
chmod +x run_frontend.sh
chmod +x run_tests.sh

echo
echo "===== Setup Complete ====="
echo "To start the backend server, run: ./run_backend.sh"
echo "To start the frontend server, run: ./run_frontend.sh"
echo "To run tests, run: ./run_tests.sh"
echo
echo "The backend will be available at http://localhost:8000"
echo "The frontend will be available at http://localhost:3000"
echo
echo "API documentation is available at:"
echo "- Swagger UI: http://localhost:8000/docs"
echo "- ReDoc: http://localhost:8000/redoc" 