#!/bin/bash

# =============================================================================
# Distributed Picture Sharing System - One-Click Installation Script
# =============================================================================
# Author: jxx3451
# Docker Hub: https://hub.docker.com/u/jxx3451
# Usage: curl -fsSL https://YOUR_URL/install.sh | bash
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_color() {
    color=$1
    shift
    echo -e "${color}$@${NC}"
}

print_header() {
    echo ""
    print_color $BLUE "=========================================="
    print_color $BLUE "$1"
    print_color $BLUE "=========================================="
    echo ""
}

print_success() {
    print_color $GREEN "✅ $1"
}

print_error() {
    print_color $RED "❌ $1"
}

print_warning() {
    print_color $YELLOW "⚠️  $1"
}

print_info() {
    print_color $BLUE "ℹ️  $1"
}

# =============================================================================
# Check Prerequisites
# =============================================================================

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        echo ""
        echo "Please install Docker first:"
        echo "  macOS/Windows: https://www.docker.com/products/docker-desktop"
        echo "  Linux: https://docs.docker.com/engine/install/"
        echo ""
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        echo "Please start Docker and try again"
        exit 1
    fi
    
    print_success "Docker is installed and running"
}

check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        print_error "docker-compose is not installed"
        echo ""
        echo "Please install docker-compose:"
        echo "  https://docs.docker.com/compose/install/"
        echo ""
        exit 1
    fi
    print_success "docker-compose is installed"
}

check_ports() {
    local ports=(5001 5002 5003 50051 50052 50053 8000)
    local busy_ports=()
    
    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 || netstat -tuln 2>/dev/null | grep -q ":$port "; then
            busy_ports+=($port)
        fi
    done
    
    if [ ${#busy_ports[@]} -gt 0 ]; then
        print_warning "The following ports are already in use: ${busy_ports[*]}"
        echo ""
        read -p "Do you want to continue anyway? (y/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Installation cancelled"
            exit 0
        fi
    fi
}

# =============================================================================
# Installation
# =============================================================================

INSTALL_DIR="pic-share-system"

handle_existing_installation() {
    if [ -d "$INSTALL_DIR" ]; then
        print_info "Old installation detected. Removing automatically..."
        

        cd $INSTALL_DIR
        docker-compose down -v 2>/dev/null || true
        cd ..

  
        rm -rf $INSTALL_DIR
        print_success "Old installation removed"
    fi
    if [ -d "$INSTALL_DIR" ]; then
        print_warning "Directory '$INSTALL_DIR' already exists"
        echo ""
        echo "Options:"
        echo "  1) Remove and reinstall (will delete all data)"
        echo "  2) Update only (keep existing data)"
        echo "  3) Cancel installation"
        echo ""
        read -p "Enter your choice (1/2/3): " -n 1 -r
        echo ""
        
        case $REPLY in
            1)
                print_info "Removing old installation..."
                cd $INSTALL_DIR
                docker-compose down -v 2>/dev/null || true
                cd ..
                rm -rf $INSTALL_DIR
                print_success "Old installation removed"
                ;;
            2)
                print_info "Updating existing installation..."
                cd $INSTALL_DIR
                docker-compose down 2>/dev/null || true
                cd ..
                return 0
                ;;
            3)
                echo "Installation cancelled"
                exit 0
                ;;
            *)
                print_error "Invalid choice"
                exit 1
                ;;
        esac
    fi
}

create_docker_compose() {
    print_info "Creating docker-compose.yml..."
    
    cat > docker-compose.yml <<'EOF'
version: '3.8'

services:
  # HTTP Nodes (Layered Architecture)
  http-node1:
    image: jxx3451/pic-share-http-node:latest
    container_name: pic-share-http-node1
    environment:
      - NODE_NAME=http-node1
    volumes:
      - http1-data:/data
    ports:
      - "5001:5000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  http-node2:
    image: jxx3451/pic-share-http-node:latest
    container_name: pic-share-http-node2
    environment:
      - NODE_NAME=http-node2
    volumes:
      - http2-data:/data
    ports:
      - "5002:5000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  http-node3:
    image: jxx3451/pic-share-http-node:latest
    container_name: pic-share-http-node3
    environment:
      - NODE_NAME=http-node3
    volumes:
      - http3-data:/data
    ports:
      - "5003:5000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # gRPC Nodes (Microservices Architecture)
  grpc-node1:
    image: jxx3451/pic-share-grpc-node:latest
    container_name: pic-share-grpc-node1
    environment:
      - NODE_NAME=grpc-node1
    volumes:
      - grpc1-data:/data
    ports:
      - "50051:50051"
    restart: unless-stopped

  grpc-node2:
    image: jxx3451/pic-share-grpc-node:latest
    container_name: pic-share-grpc-node2
    environment:
      - NODE_NAME=grpc-node2
    volumes:
      - grpc2-data:/data
    ports:
      - "50052:50051"
    restart: unless-stopped

  grpc-node3:
    image: jxx3451/pic-share-grpc-node:latest
    container_name: pic-share-grpc-node3
    environment:
      - NODE_NAME=grpc-node3
    volumes:
      - grpc3-data:/data
    ports:
      - "50053:50051"
    restart: unless-stopped

  # Web Interface
  web:
    image: jxx3451/pic-share-web:latest
    container_name: pic-share-web
    ports:
      - "8000:8000"
    depends_on:
      - http-node1
      - http-node2
      - http-node3
      - grpc-node1
      - grpc-node2
      - grpc-node3
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/logs"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  http1-data:
  http2-data:
  http3-data:
  grpc1-data:
  grpc2-data:
  grpc3-data:
EOF

    print_success "docker-compose.yml created"
}

create_helper_scripts() {
    print_info "Creating helper scripts..."
    
    # Stop script
    cat > stop.sh <<'STOP_EOF'
#!/bin/bash
echo "🛑 Stopping Distributed Picture Sharing System..."
docker-compose down
echo "✅ System stopped"
echo ""
echo "Note: Data is preserved. Use './start.sh' to restart"
STOP_EOF

    # Start script
    cat > start.sh <<'START_EOF'
#!/bin/bash
echo "🚀 Starting Distributed Picture Sharing System..."
docker-compose up -d
echo ""
echo "⏳ Waiting for services to start..."
sleep 10
echo ""
echo "✅ System started!"
echo "🌐 Web Interface: http://localhost:8000"
START_EOF

    # Restart script
    cat > restart.sh <<'RESTART_EOF'
#!/bin/bash
echo "🔄 Restarting Distributed Picture Sharing System..."
docker-compose restart
echo ""
echo "⏳ Waiting for services to restart..."
sleep 10
echo ""
echo "✅ System restarted!"
echo "🌐 Web Interface: http://localhost:8000"
RESTART_EOF

    # Status script
    cat > status.sh <<'STATUS_EOF'
#!/bin/bash
echo "📊 System Status:"
echo ""
docker-compose ps
echo ""
echo "📝 To view logs: docker-compose logs -f"
echo "🌐 Web Interface: http://localhost:8000"
STATUS_EOF

    # Logs script
    cat > logs.sh <<'LOGS_EOF'
#!/bin/bash
echo "📝 Viewing system logs (Ctrl+C to exit)..."
echo ""
docker-compose logs -f
LOGS_EOF

    # Uninstall script
    cat > uninstall.sh <<'UNINSTALL_EOF'
#!/bin/bash
echo "⚠️  WARNING: This will remove all containers, images, and data!"
echo ""
read -p "Are you sure you want to uninstall? (yes/no) " -r
echo ""

if [[ $REPLY == "yes" ]]; then
    echo "🗑️  Removing system..."
    docker-compose down -v
    docker rmi jxx3451/pic-share-http-node:latest 2>/dev/null || true
    docker rmi jxx3451/pic-share-grpc-node:latest 2>/dev/null || true
    docker rmi jxx3451/pic-share-web:latest 2>/dev/null || true
    cd ..
    rm -rf pic-share-system
    echo "✅ System completely removed"
else
    echo "Uninstallation cancelled"
fi
UNINSTALL_EOF

    # Update script
    cat > update.sh <<'UPDATE_EOF'
#!/bin/bash
echo "🔄 Updating to latest version..."
docker-compose pull
docker-compose up -d
echo ""
echo "✅ System updated!"

UPDATE_EOF

    chmod +x stop.sh start.sh restart.sh status.sh logs.sh uninstall.sh update.sh
    
    print_success "Helper scripts created"
}

create_readme() {
    cat > README.md <<'README_EOF'
# Distributed Picture Sharing System

## Quick Commands

```bash
./start.sh      # Start the system
./stop.sh       # Stop the system
./restart.sh    # Restart the system
./status.sh     # Check system status
./logs.sh       # View system logs
./update.sh     # Update to latest version
./uninstall.sh  # Complete removal
```

## Access

- **Web Interface**: http://localhost:8000
- **HTTP Nodes**: http://localhost:5001, 5002, 5003
- **gRPC Nodes**: localhost:50051, 50052, 50053

## Features

- ✅ Upload pictures (distributed across nodes)
- ✅ Search pictures (find which node)
- ✅ Download pictures
- ✅ Delete pictures
- ✅ Like pictures
- ✅ Real-time logs
- ✅ Benchmark testing

## Architecture

- **3 HTTP Nodes** - Layered architecture implementation
- **3 gRPC Nodes** - Microservices architecture implementation
- **1 Web Interface** - Unified control panel

## Docker Commands

```bash
# View all containers
docker-compose ps

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Remove all data
docker-compose down -v

# Restart specific service
docker-compose restart web
```

## Troubleshooting

**Services won't start:**
```bash
docker-compose logs
```

**Port conflicts:**
- Check if ports 5001-5003, 50051-50053, 8000 are available
- Modify ports in docker-compose.yml if needed

**Update images:**
```bash
docker-compose pull
docker-compose up -d
```

## Support

- Docker Hub: https://hub.docker.com/u/jxx3451
- Report issues: Check Docker Hub repository links

---

Installed on: $(date)
README_EOF

    print_success "README.md created"
}

pull_images() {
    print_info "Pulling Docker images (this may take a few minutes on first run)..."
    echo ""
    
    docker-compose pull
    
    print_success "All images downloaded"
}

start_services() {
    print_info "Starting services..."
    echo ""
    
    docker-compose up -d
    
    print_success "Services started"
}

wait_for_services() {
    print_info "Waiting for services to be ready..."
    echo ""
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:8000/logs &>/dev/null; then
            print_success "Web interface is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo ""
    print_warning "Services took longer than expected to start"
    print_info "Check status with: docker-compose ps"
}

print_final_info() {
    print_header "Installation Complete! 🎉"
    
    print_success "System is running!"
    echo ""
    
    print_color $GREEN "🌐 Web Interface:"
    echo "   http://localhost:8000"
    echo ""
    
    print_color $BLUE "📂 Installation Directory:"
    echo "   $(pwd)"
    echo ""
    
    print_color $BLUE "🛠️  Quick Commands:"
    echo "   ./start.sh      - Start the system"
    echo "   ./stop.sh       - Stop the system"
    echo "   ./restart.sh    - Restart the system"
    echo "   ./status.sh     - Check system status"
    echo "   ./logs.sh       - View system logs"
    echo "   ./update.sh     - Update to latest version"
    echo "   ./uninstall.sh  - Complete removal"
    echo ""
    
    print_color $BLUE "📊 Service Status:"
    docker-compose ps
    echo ""
    
    print_color $YELLOW "💡 Tip:"
    echo "   Run './logs.sh' to see real-time system logs"
    echo "   Run './status.sh' to check if all services are running"
    echo ""
    
    print_color $GREEN "📖 See README.md for more information"
    echo ""
}

# =============================================================================
# Main Installation Flow
# =============================================================================

main() {
    print_header "Distributed Picture Sharing System - Installation"
    
    # Check prerequisites
    print_info "Checking prerequisites..."
    check_docker
    check_docker_compose
    check_ports
    print_success "All prerequisites met"
    echo ""
    
    # Handle existing installation
    handle_existing_installation
    
    # Create directory
    mkdir -p $INSTALL_DIR
    cd $INSTALL_DIR
    
    # Create configuration files
    create_docker_compose
    create_helper_scripts
    create_readme
    echo ""
    
    # Pull images and start
    pull_images
    echo ""
    start_services
    echo ""
    wait_for_services
    echo ""
    
    # Show final information
    print_final_info

    echo "🌐 Web Page: http://localhost:8000"
}

# Run main function
main