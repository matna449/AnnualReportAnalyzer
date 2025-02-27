#!/bin/bash

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Run the frontend server
echo "Starting frontend server..."
npx next dev 