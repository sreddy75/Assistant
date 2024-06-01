#!/bin/bash

# Check for Docker installation
if ! command -v docker &> /dev/null
then
    echo "Docker is not installed. Please install Docker from: https://docs.docker.com/get-docker/"
    exit
fi

# Check for Docker Compose installation
if ! command -v docker-compose &> /dev/null
then
    echo "Docker Compose is not installed. Please install Docker Compose from: https://docs.docker.com/compose/install/"
    exit
fi

# Create .env file
echo "Creating .env file..."
cat <<EOT >> .env
OPENAI_API_KEY=sk-*****
OPENAI_MODEL_NAME=gpt-4o
EXA_API_KEY=****
EOT

# Build and run the Docker containers
echo "Building Docker images and starting containers..."
docker-compose up --build -d

echo "Setup complete. The Streamlit app is running on http://localhost:8501"