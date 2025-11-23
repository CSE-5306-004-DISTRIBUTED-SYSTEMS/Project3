#!/bin/bash

# Build and push Docker images to Docker Hub
# Usage: ./build_and_push.sh <your-dockerhub-username>

if [ -z "$1" ]; then
    echo "Usage: ./build_and_push.sh <your-dockerhub-username>"
    echo "Example: ./build_and_push.sh myusername"
    exit 1
fi

DOCKER_USERNAME=$1
VERSION="1.0"

echo "Building and pushing images for user: $DOCKER_USERNAME"
echo "Version: $VERSION"
echo ""

# Login to Docker Hub
echo "Logging in to Docker Hub..."
docker login

# Generate gRPC code first
echo ""
echo "Generating gRPC code..."
cd grpc_nodes
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. picture.proto
cp picture_pb2.py picture_pb2_grpc.py ../web/
cd ..

# Build and push HTTP node
echo ""
echo "Building HTTP node image..."
docker build -t $DOCKER_USERNAME/pic-share-http-node:$VERSION ./http_nodes
docker tag $DOCKER_USERNAME/pic-share-http-node:$VERSION $DOCKER_USERNAME/pic-share-http-node:latest
echo "Pushing HTTP node image..."
docker push $DOCKER_USERNAME/pic-share-http-node:$VERSION
docker push $DOCKER_USERNAME/pic-share-http-node:latest

# Build and push gRPC node
echo ""
echo "Building gRPC node image..."
docker build -t $DOCKER_USERNAME/pic-share-grpc-node:$VERSION ./grpc_nodes
docker tag $DOCKER_USERNAME/pic-share-grpc-node:$VERSION $DOCKER_USERNAME/pic-share-grpc-node:latest
echo "Pushing gRPC node image..."
docker push $DOCKER_USERNAME/pic-share-grpc-node:$VERSION
docker push $DOCKER_USERNAME/pic-share-grpc-node:latest

# Build and push web interface
echo ""
echo "Building web interface image..."
docker build -t $DOCKER_USERNAME/pic-share-web:$VERSION ./web
docker tag $DOCKER_USERNAME/pic-share-web:$VERSION $DOCKER_USERNAME/pic-share-web:latest
echo "Pushing web interface image..."
docker push $DOCKER_USERNAME/pic-share-web:$VERSION
docker push $DOCKER_USERNAME/pic-share-web:latest

echo ""
echo "=========================================="
echo "All images pushed successfully!"
echo "=========================================="
echo ""
echo "Images published:"
echo "  - $DOCKER_USERNAME/pic-share-http-node:$VERSION"
echo "  - $DOCKER_USERNAME/pic-share-grpc-node:$VERSION"
echo "  - $DOCKER_USERNAME/pic-share-web:$VERSION"
echo ""
echo "To use these images, update docker-compose.yml with your username"
echo "Then others can run: docker-compose up -d"