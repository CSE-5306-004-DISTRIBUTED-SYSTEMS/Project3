# Distributed Online Auction Platform

This repository implements a distributed online auction platform using two contrasting system architectures:

1. **Go-based microservices with a lightweight gRPC-inspired communication layer** (`go-architecture`)
2. **Python layered architecture communicating over HTTP** (`python_architecture`)

Each architecture satisfies the functional requirements of creating auctions, bidding, broadcasting updates, closing auctions, and viewing history across at least five containerized nodes. A simple web GUI is provided in the Python stack.

## Prerequisites

* Docker and Docker Compose
* (Optional) Go 1.21 and Python 3.11 for running services directly during development

## Running the Go microservice architecture

```bash
cd go-architecture
# build and start all six services
docker compose up --build
```

The gateway listens on `localhost:7000`. Example interaction:

```bash
curl -X POST http://localhost:7000/auction.AuctionGateway/Execute \
  -H 'Content-Type: application/json' \
  -d '{"command":"create","auction":{"name":"Laptop","description":"Lightly used","starting_bid":50,"duration_seconds":120}}'
```

Use the same endpoint with different `command` payloads (`place_bid`, `close`, `list`) to exercise the API.

## Running the Python layered architecture with GUI

```bash
cd python_architecture
# launch five HTTP services (frontend, gateway, auction, bidding, history)
docker compose up --build
```

Only the gateway (`8000`) and frontend (`8080`) publish host ports, so the supporting services no longer conflict with other local apps that might already use `8001-8003`.

Open [http://localhost:8080](http://localhost:8080) to access the dashboard, create auctions, queue multiple bids for a single auction, close auctions, and review historical activity. The interface now consumes a server-sent events (SSE) stream for real-time updates—new bids, closures, and history entries appear instantly without manual refresh or polling. Auction durations default to 60 seconds and automatically expire with a "Bid time ended" status.

## Benchmarking throughput and latency

After either architecture is running, execute the lightweight benchmark script to gather baseline latency and throughput metrics:

```bash
# replace BASE_URL with http://localhost:7000 for Go or http://localhost:8000 for Python
python evaluation/benchmark.py http://localhost:8000
```

> Tip: you can also export an environment variable (e.g. `export BASE_URL=http://localhost:8000`) and run `python evaluation/benchmark.py BASE_URL`. The script resolves placeholders to environment variables and prints friendly error details if a request fails.

The script performs a series of create/bid/close operations and reports the average latency and achieved throughput.

**Sample Results (Python Architecture, 100 requests, 10 concurrent users)**:
- Total Successful Requests: 94
- Average Latency: 20.1 ms
- Min Latency: 12.2 ms
- Max Latency: 32.5 ms
- Throughput: 463.24 requests/second

## Leveraging AI tools

The implementation was produced with the assistance of AI coding tools. Comments and documentation capture design decisions and trade-offs between the two architectural styles.

