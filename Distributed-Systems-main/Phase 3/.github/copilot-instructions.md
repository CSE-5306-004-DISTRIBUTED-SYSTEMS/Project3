# AI Coding Agent Instructions for Distributed-Systems Repository

> Purpose: Quickly onboard an AI assistant to extend or modify the distributed auction & Pokemon Nexus systems, and to implement consensus features (2PC / Raft) without breaking existing service contracts.

## Architectural Overview
- Two distinct auction implementations under `distributed-auction-system/Distributed-Online-Auction-Platform-main/`:
  - `go-architecture/`: Six gRPC microservices + gateway (auction catalog, bid validator, history recorder, update broadcaster, winner notifier, gateway orchestrator). In‑memory state; synchronous unary RPC calls; Docker‑network service discovery via env vars.
  - `python_architecture/`: Layered HTTP services (frontend, gateway, auction, bidding, history) using a custom lightweight routing layer built on `http.server` (`JSONRequestHandler` + `@route` decorator). All state kept in memory.
- A separate `Pokemon-Nexus/` project with layered vs microservices variants and load‑test harnesses. Keep changes scoped; do not mix auction consensus code into Pokemon directories.

## Go Microservice Patterns (`go-architecture`)
- Proto file: `proto/auction.proto` defines messages + service RPCs. Command pattern: most services expose a single `Execute` RPC switching on `AuctionCommand.command` (e.g. `create`, `get`, `update_bid`, `close`, `list`, `validate`, `record`, `notify`). Broadcasters have explicit `Publish` + `List`.
- Generated code lives in `pb/auction.pb.go`; keep `option go_package` stable. When adding RPCs: append to existing `service` blocks; preserve field numbers; never reuse removed tags.
- Orchestration lives in `services/aggregator/main.go`:
  - Resolves downstream addresses from env (`CATALOG_ADDR`, `VALIDATOR_ADDR`, etc.).
  - Performs validation → state mutation → side effects (history + updates + notifier).
  - History + updates are fire‑and‑forget; errors logged only.
- Service main files follow consistent pattern: read port env var (`*_PORT`), `net.Listen`, `grpc.NewServer`, register server, log startup. Maintain this shape for new consensus/coordination services.
- State storage: per service struct with `map[string]*pb.Auction` guarded by `sync.Mutex`; clone objects before returning. Preserve cloning & expiry helpers when extending catalog behavior.
- Expiration: `ClosingTime` checked on read/update; status changed to `CLOSED`. Respect this logic when adding transactional or consensus flows.

## Python Layered Patterns (`python_architecture`)
- Entrypoint: `service_runner.py` selects service via `SERVICE` env and runs `<service>.server.run()`.
- HTTP layer: `common/http.py` provides `JSONRequestHandler` and `@Class.route(method, path)` decorator populating `routes`. Handlers must return `(status:int, dict)` or a `StreamingResponse` (used by SSE in frontend/gateway).
- Auction service logic in `services/auction_service/server.py`: in‑memory dict, cloned responses, expiration managed by `_expire_if_needed` altering `status` + `status_reason`. Follow same pattern (lock + copy) for new resources.

## Containerization & Runtime
- Each architecture has a dedicated `docker-compose.yml`; services are built from a single `Dockerfile` whose `SERVICE` build arg selects code path. Extend compose with new consensus nodes by following existing service stanza naming + env convention.
- Environment variable conventions:
  - Go: `<SERVICE>_ADDR` for downstream host:port; `<SERVICE>_PORT` for listener ports.
  - Python: `<SERVICE_NAME>_PORT` for listener; only gateway/frontend ports exposed to host.

## Cross‑Cutting Conventions
- Logging: Go uses `log.Printf`; Python prints simple startup messages; maintain minimal, structured (prefix with service name) logging when adding coordination phases.
- Error handling: Return `{Ok:false, Message:...}` in Go RPC responses; never panic on user input. In Python return HTTP `4xx` with `{"error": ...}`.
- Cloning: Before returning mutable state, copy (Go: `cloneAuction`; Python: `_clone_auction`). Always update clones—not originals—in response payloads.

## Adding 2PC / Raft Features
- Prefer adding new proto file (e.g. `proto/consensus.proto`) for Raft & 2PC rather than overloading `auction.proto`; keep auction business RPCs separate from control plane.
- 2PC (vote + decision phases): Implement a coordinator service (Go recommended) that wraps auction mutations (e.g. create or close). Participants can be the existing catalog/validator/history services or newly added lightweight participant stubs. Use deterministic logging: `Phase <phase_name> of Node <node_id> sends RPC <rpc_name> to Phase <phase_name> of Node <node_id>`.
- Raft: Create N identical node containers with a unified service binary; roles tracked in memory (state enum + term + log slice). Heartbeats every 1s; randomized election timeout in [1.5s, 3s]. Place proto + implementation under `go-architecture/consensus/` (new dir) to avoid polluting auction files.
- Log replication: Reuse pattern of cloning + apply; maintain committed index `c`; send full log on heartbeat (simplified spec) until optimization required.

## Development & Verification
- Benchmarks: Use `evaluation/benchmark.py` in auction root for latency/throughput after changes. Provide `BASE_URL` (7000 Go gateway / 8000 Python gateway).
- Proto regeneration (example):
  ```bash
  cd go-architecture
  protoc --go_out=. --go-grpc_out=. proto/auction.proto
  ```
  Adjust include path if `protoc` not on PATH.
- Keep new code minimal; avoid refactors across unrelated services when adding consensus.

## Safe Extension Checklist
1. Identify target architecture (Go preferred for consensus additions).
2. Add new proto file; regenerate stubs.
3. Create new service dir mirroring existing main.go template.
4. Wire into docker-compose with distinct port + env names.
5. Implement in‑memory state guarded by `sync.Mutex` (Go) or lock (Python).
6. Return cloned state; preserve response shapes.
7. Update README with new run instructions only after validation.

---
Feedback welcome: Which sections need more depth (e.g. Raft log format, 2PC messaging) or examples? Specify and I will refine.
