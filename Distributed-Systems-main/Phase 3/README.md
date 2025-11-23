Repository: https://github.com/mgm67671/Distributed-Systems 
---
## 1. Scope

Phase 3 adds fault-tolerant coordination without altering external auction APIs:
- Q1–Q2: 2PC coordinator + 4 participants (vote → decision)
- Q3: Raft leader election (5 nodes, randomized timeouts)
- Q4: Raft log replication (full snapshot each heartbeat per spec)
- Q5: Reliability tests (crash, split vote, forwarding, rejoin, partition)

---
## 2. High-Level Architecture

```
services/
  2pc_coordinator/      # Orchestrates vote & decision
  2pc_participant/      # Four identical participants
  raft_node/            # Single binary, 5 containers
proto/                  # consensus.proto, raft.proto
pb/                     # Manually maintained *.pb.go stubs
distributed-auction-system/Distributed-Online-Auction-Platform-main/
  go-architecture/      # Original auction microservices (unchanged)
  python_architecture/  # Original layered variant (unchanged)
```

Separation: Consensus code is additive; auction logic continues in existing directories; no storage or RPC contracts modified for core auction features.

---
## 3. Consensus Features Summary

2PC:
- Coordinator broadcasts Vote RPC to each participant.
- All participants deterministically return commit (demo simplification).
- Coordinator issues Decide (global commit) if all votes commit; otherwise would abort.
- Logging format: `Phase <phase> of Node <id> sends RPC <rpc> to Phase <phase> of Node <id>`.

Raft:
- Roles: follower → candidate → leader.
- Election timeout randomized 1.5–3.0s; heartbeat interval 1s.
- Full log snapshot sent on every AppendEntries (instruction-driven simplification).
- Majority (≥3) ACKs commit entries; applied in order.
- Follower forwards client requests to leader (HTTP shim) if not leader.

Reliability Tests (Q5):
- Leader crash & re-election.
- Split vote resolved by timeout randomness.
- Forwarding correctness from follower to leader.
- Node offline during operations then rejoins and syncs log.
- Partition & recovery with stale leader reconciliation.

---
## 4. Running the Stack

Prerequisites: Docker Desktop + Compose;

Build & start all (auction + 2PC + Raft):
```powershell
docker compose build; docker compose up -d
```
Follow logs:
```powershell
docker compose logs -f
```
Shutdown:
```powershell
docker compose down
```

Start just consensus services:
```powershell
docker compose up -d 2pc_coordinator 2pc_participant1 2pc_participant2 2pc_participant3 2pc_participant4 \
                   raft_node1 raft_node2 raft_node3 raft_node4 raft_node5
```

Submit Raft client request (any node; forwarding occurs if follower):
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:7301/client_request" -ContentType "application/json" -Body '{"operation":"TEST_OP"}'
```

Trigger 2PC transaction:
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:7100/auction.TwoPCCoordinator/StartVoting" -ContentType "application/json" -Body '{"tx_id":"tx-1","operation":"create-auction"}'
```

Ports in use:
- Go auction gateway: 7000
- Python gateway/frontend: 8000 / 8080
- 2PC: 7100 (coord) + 7101–7104 (participants)
- Raft gRPC: 7201–7205; Raft HTTP shim: 7301–7305

---
## 5. Key Implementation Choices

Manual Protobuf Stubs:
- `pb/consensus.pb.go`, `pb/raft.pb.go` authored by hand (no host `protoc` dependency).

Embedded Minimal gRPC:
- Custom lightweight HTTP/JSON-based gRPC-like layer in `google.golang.org/grpc/grpc.go` to avoid external libs.

Simplified Raft Replication:
- Sends entire log each heartbeat (trade performance for clarity & alignment with assignment spec).

In-Memory State Only:
- No persistence for Raft term, votedFor, or logs; fresh election after container restart.

Follower Forwarding:
- Non-leader node caches leader ID via incoming AppendEntries; forwards HTTP client requests automatically.

Thread-Safety Fixes (during debugging):
- Channel-based vote counting; index-based log apply; ACK map reset on term change; snapshot cloning before goroutines; leader address caching.

---
## 6. Testing Overview

Primary detailed evidence lives in `RAFT_TEST_RESULTS.md` and screenshots referenced in `REPORT.md` (URL-encoded paths). Each scenario confirms resilience assumptions:
- Election stability under crashes & partitions.
- Deterministic transaction commit in 2PC demo.
- Log convergence on late-joining Raft node.

Quick verification snippet:
```powershell
docker compose up -d raft_node1 raft_node2 raft_node3 raft_node4 raft_node5; Start-Sleep -Seconds 6
Invoke-RestMethod -Method POST -Uri "http://localhost:7302/client_request" -ContentType "application/json" -Body '{"operation":"X"}'
docker compose logs raft_node1 raft_node2 raft_node3 raft_node4 raft_node5 | Select-String "applies operation"
```

---

| Name          | ID         | Role       |
|---------------|------------|-----------|
| Matthew Moran | 1001900489 | All work  |