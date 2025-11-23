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

## Two-Phase Commit (2PC) Cluster (Instructions.txt Q1/Q2)

Root-level `docker-compose.yml` now includes a 2PC coordinator (`2pc_coordinator`) and four participant nodes (`2pc_participant1`..`4`). Consensus stubs (`pb/consensus.pb.go`) are checked in so no local `protoc` installation is required for dockerized runs.

Start everything (Go + Python stacks + 2PC) from repository root (fully dockerized, no host toolchain prerequisites beyond Docker):

```bash
docker compose up --build
```

Trigger a voting round (example curl against coordinator once stubs compiled):

```bash
curl -X POST http://localhost:7100/auction.TwoPCCoordinator/StartVoting \
  -H 'Content-Type: application/json' \
  -d '{"tx_id":"tx-123","operation":"create-auction"}'
```

Logs will show required phase messages per Instructions.txt for both voting and decision phases.

## Raft Leader Election (Instructions.txt Q3)

Five Raft nodes (`raft_node1`..`raft_node5`) are included in the root compose. Each starts as follower with a randomized election timeout (1.5s–3s). If a node times out without heartbeats it becomes candidate, increments term, and requests votes. Majority grants leadership; leader sends 1s heartbeats (`AppendEntries`).

Run (with existing stacks) from project root:
```bash
docker compose up -d
```

Inspect leader election logs:
```bash
docker compose logs -f raft_node1 raft_node2 raft_node3
```

Trigger manual vote request (optional) using `Invoke-RestMethod` (PowerShell) or curl:
```bash
curl -X POST http://localhost:7201/auction.RaftNode/RequestVote \
  -H 'Content-Type: application/json' \
  -d '{"candidate_id":"n1","term":1}'
```

Expected log patterns per Instructions.txt:
- Client side: `Node <node_id> sends RPC RequestVote to Node <peer_id>` / `Node <leader_id> sends RPC AppendEntries to Node <peer_id>`
- Server side: `Node <node_id> runs RPC RequestVote called by Node <candidate_id>` / `Node <node_id> runs RPC AppendEntries called by Node <leader_id>`

## Raft Log Replication (Instructions.txt Q4)

Log replication has been added (simplified snapshot model). Each heartbeat (`AppendEntries`) from the leader now carries the full log plus the current commit index `c`.

### Client Request Flow
Submit an operation to any raft node via the gRPC `ClientRequest` RPC. For manual testing without gRPC tooling, an HTTP shim is exposed on ports `7301-7305`:

```bash
curl -X POST http://localhost:7301/client_request \
  -H 'Content-Type: application/json' \
  -d '{"operation":"op1"}'
```

If the target node is the leader it appends `<op1, term, k>` to its log (where `k` is the next index). If it is a follower it forwards the request transparently to the leader and returns the leader's reply.

### Heartbeat Replication
Each second the leader sends `AppendEntries` containing:
- `entries`: full log snapshot (simplified—no incremental diff yet)
- `commit_index`: leader's committed index `c`

Followers replace their local log with the snapshot and apply all entries up to `commit_index` (executing operations). Logs show:

```
Node n3 sends RPC AppendEntries to Node raft_node1:7201
Node n1 runs RPC AppendEntries called by Node n3
Node n1 applies operation idx=0 op=op1
```

### Commitment
Leader counts ACKs per last log index. When majority (>=3 of 5) acknowledge an index, `commitIndex` advances and pending entries are applied locally (log line: `Node n3 applies operation idx=0 op=op1`). Subsequent heartbeats propagate the updated `commit_index` so followers apply.

### Forwarding Example (send to follower HTTP shim port 7302)
```bash
curl -X POST http://localhost:7302/client_request \
  -H 'Content-Type: application/json' \
  -d '{"operation":"op2"}'
```
Follower prints forwarding log; leader appends and returns queue confirmation.

### Observing Replication
Tail logs while submitting multiple operations:
```bash
docker compose logs -f raft_node1 raft_node2 raft_node3
```

### Notes / Future Work
- Snapshot approach trades efficiency for clarity; an incremental diff optimization could follow.
- A joining node (future Q5 test) will receive full log on first heartbeat and apply immediately.
- Conflict resolution for divergent logs (crash recovery) is not yet implemented; leader overwrites follower state wholesale.

## Leveraging AI tools

The implementation was produced with the assistance of AI coding tools. Comments and documentation capture design decisions and trade-offs between the two architectural styles.

