# Project Report: Phase 3 – 2PC & Raft Consensus Implementation

GitHub Repository: https://github.com/mgm67671/Distributed-Systems

## 1. Team & Contributions
| Student Name | Student ID | Contribution |
|--------------|------------|--------------|
| Matthew Moran | 1001900489 | Everything |
| Github Copilot | NULL | Everything Too |

## 2. Selected Base Implementation (Q0)
The existing distributed online auction platform (Go microservices + Python layered services) was used as the extension target for consensus features. Original business functionality remained untouched. 

## 3. Overview
This project implements:
- Two-Phase Commit (2PC): Voting + Decision phases across 1 coordinator and 4 participants.
- Raft (Simplified): Leader election with randomized timeouts and full-log heartbeats for replication.
- Forwarding: Any node receiving a client request forwards to current leader.
- Five custom Raft test scenarios (Q5) validating fault-tolerance and recovery semantics.
All consensus state is in memory (no persistence) and exposed via a lightweight embedded gRPC layer plus an HTTP shim for simplified manual testing.

## 4. Two-Phase Commit (Q1 & Q2)
- Proto: Custom messages for VoteRequest, VoteReply, Decision (Commit/Abort).
- Voting Phase: Coordinator broadcasts vote-request; participants reply commit or abort.
- Decision Phase: Coordinator aggregates all votes; unanimity -> global-commit else global-abort.
- Logging Format:
  - Client side: `Phase <phase_name> of Node <node_id> sends RPC <rpc_name> to Phase <phase_name> of Node <node_id>`
  - Server side mirrors format.
- Containerization: 1 coordinator + 4 participants communicating over internal Docker network.

## 5. Raft Implementation (Q3 & Q4)
### 5.1 Leader Election
- States: Follower (initial), Candidate, Leader.
- Timeouts: Heartbeat = 1s; Election timeout randomized in [1.5s, 3s].
- Election: Candidate increments term, votes for self, requests votes. Majority => Leader.
- RPC Logging:
  - Client: `Node <id> sends RPC <rpc_name> to Node <id>`
  - Server: `Node <id> runs RPC <rpc_name> called by Node <caller_id>`

### 5.2 Log Replication
- Each client operation appended to leader log with (operation, term, index).
- Heartbeats send entire log + committed index `c` (simplified full snapshot approach).
- Followers replace local pending state with leader snapshot; ACK appended entries.
- Leader commits operations after majority ACK, increments `c`, applies locally, followers apply up to `c`.
- Forwarding: Non-leader node calls leader via stored connection map; returns leader response.

### 5.3 Unusual Simplifications
- Full-log broadcast each heartbeat (not incremental diff) to reduce complexity.
- In-memory only; no stable storage or log truncation.
- Direct index majority counting for commit rather than per-follower match indices.

## 6. Test Cases (Q5)
Five scenarios were designed, executed, and screenshotted. Replace filenames below with actual captured images placed in `Screenshots/`.

| Test | Objective | Method | Result Evidence |
|------|-----------|--------|-----------------|
| 1 | Leader crash & re-election | Stop active leader container | New leader elected quickly | 
| 2 | Split vote resolution | Restart multiple nodes simultaneously | Competing candidates; eventual single leader | 
| 3 | Follower forwarding | Send client request to non-leader HTTP shim | Forward log line + leader commit | 
| 4 | Node rejoin & catch-up | Stop follower; issue ops; restart | Rejoined node applies missed ops | 
| 5 | Partition & recovery | Pause leader; observe new election; unpause | Old leader reverts; consistent log maintained |

### 6.1 Screenshots
All screenshot files are stored under `Screenshots/`. Ensure filenames below match the actual PNGs before PDF export.

#### Test 1 – Leader Crash & Re-election
![Test 1 – Leader Crash & Re-election](Screenshots/Test%201.png)  
Caption: Original leader log line and subsequent new leader election after crash.

#### Test 2 – Split Vote Resolution
![Test 2 – Split Vote Resolution](Screenshots/Test%202.png)  
Caption: Concurrent candidacies followed by eventual single leader stabilization.

#### Test 3 – Follower Forwarding
![Test 3 – Command Submission](Screenshots/Test%203%20Command.png)  
![Test 3 – Follower Logs](Screenshots/Test%203%20Follower%20Logs.png)  
![Test 3 – Leader Logs](Screenshots/Test%203%20Leader%20Logs.png)  
Caption: Request sent to follower, forwarding RPC logged, leader appends and applies operation cluster-wide.

#### Test 4 – Node Rejoin & Log Sync
![Test 4 – Commands While Node Down](Screenshots/Test%204%20Commands.png)  
![Test 4 – Rejoin & Sync Logs](Screenshots/Test%204%20Logs.png)  
Caption: Operations issued while node offline; upon restart node receives snapshot and applies missed entries.

#### Test 5 – Partition & Recovery
![Test 5 – Partition & Recovery](Screenshots/Test%205.png)  
Caption: Leader paused causing re-election; on resume original leader reconciles via AppendEntries and remains follower until next legitimate election.

## 7. How to Run
Refer to `README.md` for full build and run instructions. High-level:
```bash
# (Example) From Phase 3 Folder
# Build & start consensus + auction stack
docker compose build
docker compose up -d

# Submit a Raft client request (adjust leader HTTP port)
curl -X POST http://localhost:7301/client_request -H 'Content-Type: application/json' -d '{"operation":"DEMO_OP"}'
```
PowerShell alternative:
```powershell
Invoke-RestMethod -Uri "http://localhost:7301/client_request" -Method Post -Body '{"operation":"DEMO_OP"}' -ContentType 'application/json'
```