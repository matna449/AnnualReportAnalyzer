#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the tests
echo "Running backend tests..."
cd backend
python -m pytest tests/ -v

# Return to the original directory
cd .. 