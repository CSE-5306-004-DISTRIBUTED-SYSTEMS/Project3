# Distributed Picture Sharing System

A distributed system for sharing pictures with HTTP and gRPC implementations.

## Features

- **Upload pictures** - Automatically distributed across nodes
- **Search pictures** - Find which node stores your picture
- **Download pictures** - Retrieve from any node
- **Delete pictures** - Remove from the system
- **Like pictures** - Increment like counter

## Quick Start

### Prerequisites
- Docker
- Docker Compose

### Installation

1. **Create a directory and download the docker-compose file:**
```bash
mkdir pic-share-system
cd pic-share-system
wget https://raw.githubusercontent.com/YOUR_GITHUB/distributed-picture-system/main/docker-compose-public.yml -O docker-compose.yml
```

2. **Start the system:**
```bash
docker-compose up -d
```

3. **Access the web interface:**
Open your browser and go to: `http://localhost:8000`

### Usage

1. Select strategy (HTTP or gRPC)
2. Upload pictures using the file input
3. View all pictures in the list
4. Search, download, like, or delete pictures
5. View real-time logs

### Stop the System

```bash
docker-compose down
```

### View Logs

```bash
docker-compose logs -f
```

## Architecture

- **3 HTTP nodes** (ports 5001-5003) - Layered architecture
- **3 gRPC nodes** (ports 50051-50053) - Microservices architecture
- **1 Web interface** (port 8000) - User interface

## Docker Images

- `YOUR_USERNAME/pic-share-http-node:latest` - HTTP node
- `YOUR_USERNAME/pic-share-grpc-node:latest` - gRPC node
- `YOUR_USERNAME/pic-share-web:latest` - Web interface

## Benchmarking

Run performance tests:
```bash
docker exec -it pic-share-system_web_1 python /app/benchmark.py
```

## Ports Used

- 5001-5003: HTTP nodes
- 50051-50053: gRPC nodes
- 8000: Web interface

## Support

For issues and questions, please visit the GitHub repository.
"""
"""
#!/bin/bash

echo "Stopping Distributed Picture Sharing System..."

# Stop and remove all containers
docker-compose down -v

# Kill processes on ports (Linux/Mac)
echo "Killing processes on ports..."
for port in 5001 5002 5003 50051 50052 50053 8000; do
    pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        echo "Killing process on port $port (PID: $pid)"
        kill -9 $pid 2>/dev/null
    fi
done

# Alternative for systems without lsof
# fuser -k 5001/tcp 5002/tcp 5003/tcp 50051/tcp 50052/tcp 50053/tcp 8000/tcp 2>/dev/null

echo "System stopped. All containers and processes killed."