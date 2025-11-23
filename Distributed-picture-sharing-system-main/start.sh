#!/bin/bash

# Quick start script for end users
# This downloads and runs the pre-built images from Docker Hub

echo "=========================================="
echo "Distributed Picture Sharing System"
echo "Quick Start"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed"
    echo "Please install docker-compose first"
    exit 1
fi

# Download docker-compose file if not exists
if [ ! -f "docker-compose.yml" ]; then
    echo "Downloading docker-compose.yml..."
    # In practice, users would get this file from your GitHub repo
    echo "Please ensure docker-compose.yml is in the current directory"
    exit 1
fi

echo "Starting all services..."
docker-compose up -d

echo ""
echo "Waiting for services to start..."
sleep 10

echo ""
echo "=========================================="
echo "System started successfully!"
echo "=========================================="
echo ""
echo "Access the web interface at:"
echo "  http://localhost:8000"
echo ""
echo "HTTP nodes running on:"
echo "  - http://localhost:5001"
echo "  - http://localhost:5002"
echo "  - http://localhost:5003"
echo ""
echo "gRPC nodes running on:"
echo "  - localhost:50051"
echo "  - localhost:50052"
echo "  - localhost:50053"
echo ""
echo "To stop the system, run:"
echo "  docker-compose down"
echo ""
echo "To view logs, run:"
echo "  docker-compose logs -f"