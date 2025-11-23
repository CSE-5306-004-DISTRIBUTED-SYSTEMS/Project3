
# Distributed Music Queue System

This project implements a distributed music queue system using **two distinct system architectures**: a Layered/Resource-Based (REST/HTTP) design and a Microservices (gRPC) design. Both architectures support distributed queue management, voting, metadata, simulated playing, and playback history, and are fully containerized for easy scaling and testing.

---

## System Architecture Summary

- **Layered/Resource-Based (REST/HTTP):**
   - FastAPI stateless nodes, Nginx load balancer, Redis backend, HTTP/REST communication.
- **Microservices (gRPC):**
   - Python gRPC services, Redis backend, gRPC communication, Nginx load balancer for gRPC.
- **Redis Backend:**
   - Shared by all nodes for queue, history, and metadata.
- **Docker Compose:**
   - Orchestrates all services, healthchecks, and dependencies.
- **Automated Test Runner:**
   - Runs all tests in a container, using Compose DNS for service discovery.

---

## Quick Start

**All commands are run from the project root.**

### 1. Build and Start Either System

- **REST/HTTP:**
   ```powershell
   docker compose -f layered-rest/docker-compose.yml up --build --scale node=5 -d
   ```
- **gRPC Microservices:**
   ```powershell
   docker compose -f microservices-grpc/docker-compose.yml up --build --scale queue-service=5 -d
   ```

### 2. Run Automated Test Suite

- **REST/HTTP:**
   ```powershell
   docker compose -f layered-rest/docker-compose.yml run --rm test-runner
   ```
- **gRPC Microservices:**
   ```powershell
   docker compose -f microservices-grpc/docker-compose.yml run --rm test-runner
   ```

### 3. Manual API/CLI Usage

- **REST/HTTP:**
   - Web GUI: [http://localhost:8080/](http://localhost:8080/) → `/docs` (Swagger UI)
   - Command-line: Use `curl` or PowerShell's `Invoke-WebRequest` (see below for examples)
- **gRPC:**
   - Use the provided Python CLI inside a running queue-service container. All gRPC requests are routed through the Nginx load balancer (`nginx-grpc:50051`) for proper load balancing (see below for all commands).

### 4. Stop the System

```powershell
docker compose -f layered-rest/docker-compose.yml down
docker compose -f microservices-grpc/docker-compose.yml down
```

---


## REST/HTTP API Examples

You can use the web GUI at [http://localhost:8080/](http://localhost:8080/) or the following command-line examples:

Add a track to the queue:
```sh
# curl:
curl -X POST "http://localhost:8080/add_track" -H "Content-Type: application/json" -d '{"id": 123, "title": "Song Title", "artist": "Artist Name", "duration": 200}'
# PowerShell:
Invoke-WebRequest -Uri "http://localhost:8080/add_track" -Method POST -Headers @{ "Content-Type" = "application/json" } -Body '{"id": 123, "title": "Song Title", "artist": "Artist Name", "duration": 200}'
```

Remove a track from the queue:
```sh
# curl:
curl -X POST "http://localhost:8080/remove_track" -H "Content-Type: application/json" -d '{"id": 123}'
# PowerShell:
Invoke-WebRequest -Uri "http://localhost:8080/remove_track" -Method POST -Headers @{ "Content-Type" = "application/json" } -Body '{"id": 123}'
```

Vote for a track:
```sh
# curl:
curl -X POST "http://localhost:8080/vote?id=123&up=true" -H "Content-Type: application/json" -d '{"id": 123}'
# PowerShell:
Invoke-WebRequest -Uri "http://localhost:8080/vote?id=123&up=true" -Method POST -Headers @{ "Content-Type" = "application/json" } -Body '{"id": 123}'
```

Get the current queue:
```sh
curl http://localhost:8080/queue
Invoke-WebRequest -Uri "http://localhost:8080/queue" -Method GET
```

Get track metadata:
```sh
curl http://localhost:8080/metadata/123
Invoke-WebRequest -Uri "http://localhost:8080/metadata/123" -Method GET
```

Get play history:
```sh
curl http://localhost:8080/history
Invoke-WebRequest -Uri "http://localhost:8080/history" -Method GET
```

Play the next song:
```sh
curl -X POST http://localhost:8080/play_next
Invoke-WebRequest -Uri "http://localhost:8080/play_next" -Method POST
```

**Run the REST Automated Test Suite:**

```powershell
docker compose -f layered-rest/docker-compose.yml run --rm test-runner
```

This executes all REST test scripts inside a container, using Compose DNS to reach the API via Nginx. All tests should pass if the system is running.

**Stop the REST System:**

```powershell
docker compose -f layered-rest/docker-compose.yml down
```

---


## gRPC Microservices: Manual CLI Usage

**First-Time Setup (for local runs, not Docker, is only needed for running the test scripts):**

If you do not see `queue_pb2.py` and `queue_pb2_grpc.py` in `microservices-grpc/queue-service/` and `microservices-grpc/tests/`, generate them from `queue.proto`:

```powershell
cd microservices-grpc/queue-service
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. queue.proto
```
You need `grpcio` and `grpcio-tools` installed:
```powershell
pip install grpcio grpcio-tools
```

**Example CLI Commands (run from project root):**

All gRPC CLI commands below will automatically connect to the load balancer (`nginx-grpc:50051`). Example usage (from project root):

1. **Add a track:**
   ```powershell
   docker compose -f microservices-grpc/docker-compose.yml exec queue-service python client.py add --id 123 --title "Song Title" --artist "Artist Name" --duration 200
   ```
2. **Play the next track:**
   ```powershell
   docker compose -f microservices-grpc/docker-compose.yml exec queue-service python client.py play
   ```
3. **View play history:**
   ```powershell
   docker compose -f microservices-grpc/docker-compose.yml exec queue-service python client.py history
   ```
4. **Get the current queue:**
   ```powershell
   docker compose -f microservices-grpc/docker-compose.yml exec queue-service python client.py queue
   ```
5. **Get track metadata:**
   ```powershell
   docker compose -f microservices-grpc/docker-compose.yml exec queue-service python client.py metadata --id 123
   ```
6. **Vote for a track:**
   ###### Upvote
   ```powershell
   docker compose -f microservices-grpc/docker-compose.yml exec queue-service python client.py vote --id 123 --up true
   ```
   ###### Downvote
   ```powershell
   docker compose -f microservices-grpc/docker-compose.yml exec queue-service python client.py vote --id 123 --up false
   ```
7. **Remove a track:**
   ```powershell
   docker compose -f microservices-grpc/docker-compose.yml exec queue-service python client.py remove --id 123
   ```