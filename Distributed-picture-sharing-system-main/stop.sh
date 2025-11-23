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