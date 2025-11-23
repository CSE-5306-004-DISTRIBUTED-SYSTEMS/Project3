# Demo Walkthrough Guide
## Distributed Systems Phase 3: Consensus Algorithms

This guide will help you understand the implementation, demonstrate all features, and explain technical details to others.

---

## Table of Contents

1. [What We Built](#what-we-built)
2. [Where Changes Were Made](#where-changes-were-made)
3. [Demo Script](#demo-script)
4. [Technical Explanations](#technical-explanations)
5. [Common Questions and Answers](#common-questions-and-answers)

---

## What We Built

### High-Level Overview

We took an existing **distributed auction platform** (from Phase 2) and added two consensus algorithms **on top of it** without modifying the original auction functionality:

1. **Two-Phase Commit (2PC)** - A coordinator and 4 participants that can reach consensus on committing or aborting a transaction
2. **Raft Consensus** - A 5-node cluster that elects leaders, replicates logs, and maintains consistency even when nodes fail

**Key Point**: The original auction system (both Go and Python versions) still works exactly as before. We added new services that run alongside them.

### Visual Architecture

```
┌─────────────────────────────────────────────┐
│     ORIGINAL (unchanged)                     │
│  ┌──────────────┐   ┌──────────────────┐   │
│  │ Go Auction   │   │ Python Auction   │   │
│  │ 6 services   │   │ 5 services       │   │
│  └──────────────┘   └──────────────────┘   │
└─────────────────────────────────────────────┘
                    │
                    │ We added these ↓
                    │
┌─────────────────────────────────────────────┐
│     NEW: 2PC (Q1-Q2)                        │
│  ┌──────────────┐   ┌──────────────────┐   │
│  │ Coordinator  │→→→│ 4 Participants   │   │
│  │   (coord1)   │←←←│ (p1,p2,p3,p4)    │   │
│  └──────────────┘   └──────────────────┘   │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│     NEW: Raft (Q3-Q4-Q5)                    │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐       │
│  │ n1 │ │ n2 │ │ n3 │ │ n4 │ │ n5 │       │
│  │FOL │ │LDR │ │FOL │ │FOL │ │FOL │       │
│  └────┘ └────┘ └────┘ └────┘ └────┘       │
│     5-node Raft cluster with leader         │
│     election and log replication            │
└─────────────────────────────────────────────┘
```

---

## Where Changes Were Made

### Files We Added (New)

```
Phase 3/
│
├── proto/                          # Protocol definitions
│   ├── consensus.proto             # 2PC messages (NEW)
│   └── raft.proto                  # Raft messages (NEW)
│
├── pb/                             # Generated Go code
│   ├── consensus.pb.go             # 2PC implementation (NEW)
│   └── raft.pb.go                  # Raft implementation (NEW)
│
├── services/                       # Consensus services
│   ├── 2pc_coordinator/            
│   │   └── main.go                 # Coordinator logic (NEW - 150 lines)
│   ├── 2pc_participant/
│   │   └── main.go                 # Participant logic (NEW - 120 lines)
│   └── raft_node/
│       └── main.go                 # Raft node (NEW - 392 lines)
│
├── docker-compose.yml              # Root orchestration (NEW)
├── README.md                       # Comprehensive docs (NEW)
└── DEMO_GUIDE.md                   # This file (NEW)
```

### Files We Modified

```
distributed-auction-system/
└── Distributed-Online-Auction-Platform-main/
    ├── README.md                   # Updated with 2PC/Raft sections
    └── go-architecture/
        └── RAFT_TEST_RESULTS.md    # Q5 test documentation (NEW)
```

### Files Unchanged (Original Auction)

```
distributed-auction-system/
└── Distributed-Online-Auction-Platform-main/
    ├── go-architecture/
    │   ├── services/               # Original 6 Go services
    │   │   ├── aggregator/         # (UNCHANGED)
    │   │   ├── auction/            # (UNCHANGED)
    │   │   ├── bidding/            # (UNCHANGED)
    │   │   ├── history/            # (UNCHANGED)
    │   │   ├── notifier/           # (UNCHANGED)
    │   │   └── updates/            # (UNCHANGED)
    │   └── docker-compose.yml      # (UNCHANGED)
    │
    └── python_architecture/
        ├── services/               # Original 5 Python services
        │   ├── frontend/           # (UNCHANGED)
        │   ├── gateway/            # (UNCHANGED)
        │   ├── auction_service/    # (UNCHANGED)
        │   ├── bidding_service/    # (UNCHANGED)
        │   └── history_service/    # (UNCHANGED)
        └── docker-compose.yml      # (UNCHANGED)
```

**Key Point for Demo**: We can show that the auction systems still work independently by running their docker-compose files separately.

---

## Demo Script

### Demo 1: Verify Original Systems Still Work (5 minutes)

**Purpose**: Show that we didn't break anything.

#### Go Auction System

```powershell
# Navigate to Go architecture
cd distributed-auction-system/Distributed-Online-Auction-Platform-main/go-architecture

# Start original Go services
docker compose up -d

# Wait for startup
Start-Sleep -Seconds 8

# Create an auction
Invoke-RestMethod -Method POST -Uri "http://localhost:7000/auction.AuctionGateway/Execute" `
  -ContentType "application/json" `
  -Body '{"command":"create","auction":{"name":"Demo Laptop","description":"Working!","starting_bid":100,"duration_seconds":120}}'

# List auctions
Invoke-RestMethod -Method POST -Uri "http://localhost:7000/auction.AuctionGateway/Execute" `
  -ContentType "application/json" `
  -Body '{"command":"list"}'

# Clean up
docker compose down
```

**What to explain**:
- "This is the original Go auction system from Phase 2"
- "Six microservices: catalog, validator, history, updates, notifier, gateway"
- "We can create auctions, place bids, close auctions - all original functionality intact"

#### Python Auction System

```powershell
# Navigate to Python architecture
cd distributed-auction-system/Distributed-Online-Auction-Platform-main/python_architecture

# Start Python services
docker compose up -d

# Open browser to http://localhost:8080
# (Show the GUI, create an auction, place a bid)

# Clean up
docker compose down
```

**What to explain**:
- "This is the Python layered architecture with web GUI"
- "Five services: frontend, gateway, auction, bidding, history"
- "Has real-time updates via Server-Sent Events"
- "Also completely unchanged from Phase 2"

---

### Demo 2: Two-Phase Commit (Q1-Q2) (10 minutes)

**Purpose**: Demonstrate distributed transaction commit with voting and decision phases.

```powershell
# Navigate to project root
cd "c:\Users\might\OneDrive\Desktop\School\Distributed Systems\Phase 3"

# Start 2PC services
docker compose up -d 2pc_coordinator 2pc_participant1 2pc_participant2 2pc_participant3 2pc_participant4

# Wait for startup
Start-Sleep -Seconds 5

# Open THREE terminal windows for this demo
```

**Terminal 1: Trigger a transaction**
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:7100/auction.TwoPCCoordinator/StartVoting" `
  -ContentType "application/json" `
  -Body '{"tx_id":"demo-tx-001","operation":"create-auction-consensus"}'
```

**Expected Output**:
```json
{
  "tx_id": "demo-tx-001",
  "global_commit": true
}
```

**Terminal 2: Watch coordinator logs**
```powershell
docker compose logs -f 2pc_coordinator
```

**What you'll see**:
```
Phase voting of Node coord1 sends RPC Vote to Phase voting of Node 2pc_participant1:7101
Phase voting of Node coord1 sends RPC Vote to Phase voting of Node 2pc_participant2:7102
Phase voting of Node coord1 sends RPC Vote to Phase voting of Node 2pc_participant3:7103
Phase voting of Node coord1 sends RPC Vote to Phase voting of Node 2pc_participant4:7104
Phase decision of Node coord1 sends RPC Decide to Phase decision of Node 2pc_participant1:7101
Phase decision of Node coord1 sends RPC Decide to Phase decision of Node 2pc_participant2:7102
Phase decision of Node coord1 sends RPC Decide to Phase decision of Node 2pc_participant3:7103
Phase decision of Node coord1 sends RPC Decide to Phase decision of Node 2pc_participant4:7104
```

**Terminal 3: Watch participant logs**
```powershell
docker compose logs -f 2pc_participant1 2pc_participant2
```

**What you'll see**:
```
Phase voting of Node p1 sends RPC Vote to Phase voting of Node p1
Phase decision of Node p1 sends RPC Decide to Phase decision of Node p1
Node p1 committed tx demo-tx-001
```

**What to explain**:

1. **Architecture**:
   - "One coordinator (coord1) orchestrates the transaction"
   - "Four participants (p1, p2, p3, p4) vote and execute"

2. **Voting Phase (Q1)**:
   - "Coordinator sends vote-request to all participants"
   - "Each participant responds with vote-commit or vote-abort"
   - "In our implementation, participants always vote commit for demonstration"
   - Point to logs: `Phase voting of Node coord1 sends RPC Vote to...`

3. **Decision Phase (Q2)**:
   - "Coordinator collects all votes"
   - "If ALL vote commit → global commit"
   - "If ANY vote abort → global abort"
   - "Coordinator broadcasts decision to all participants"
   - Point to logs: `Phase decision of Node coord1 sends RPC Decide to...`

4. **RPC Logging Format** (per Instructions.txt):
   - "Client side: `Phase <phase> of Node <id> sends RPC <name> to Phase <phase> of Node <id>`"
   - "Server side: same format"
   - "This is a specific requirement from the project instructions"

5. **Key Implementation Details**:
   - "Uses gRPC for communication"
   - "Each node has both voting and decision phases"
   - "Phases communicate via internal gRPC (even within same container)"
   - "Synchronous protocol - coordinator waits for all responses"

---

### Demo 3: Raft Leader Election (Q3) (10 minutes)

**Purpose**: Show how Raft elects a leader and maintains heartbeats.

```powershell
# Start all 5 Raft nodes
docker compose up -d raft_node1 raft_node2 raft_node3 raft_node4 raft_node5

# Watch election in real-time
docker compose logs -f raft_node1 raft_node2 raft_node3 raft_node4 raft_node5
```

**What you'll see (within 3 seconds)**:
```
raft_node4-1  | Raft node n4 follower term=0 listening on 7204
raft_node4-1  | Node n4 sends RPC RequestVote to Node (broadcast) term=1
raft_node4-1  | Node n4 sends RPC RequestVote to Node raft_node1:7201
raft_node4-1  | Node n4 sends RPC RequestVote to Node raft_node2:7202
raft_node4-1  | Node n4 sends RPC RequestVote to Node raft_node3:7203
raft_node4-1  | Node n4 sends RPC RequestVote to Node raft_node5:7205
raft_node4-1  | Node n4 becomes leader term=1
raft_node4-1  | Node n4 sends RPC AppendEntries to Node raft_node1:7201
raft_node4-1  | Node n4 sends RPC AppendEntries to Node raft_node2:7202
```

**Stop logs (Ctrl+C) and query for current leader**:
```powershell
docker compose logs raft_node1 raft_node2 raft_node3 raft_node4 raft_node5 | Select-String "becomes leader" | Select-Object -Last 1
```

**What to explain**:

1. **Initial State**:
   - "All 5 nodes start as FOLLOWERS"
   - "Each has randomized election timeout between 1.5 and 3 seconds"
   - "No leader exists initially"

2. **Election Process**:
   - "First node to timeout becomes CANDIDATE"
   - "Candidate increments term (0 → 1)"
   - "Candidate votes for itself"
   - "Candidate broadcasts RequestVote RPCs to all peers"
   - Point to logs: `Node n4 sends RPC RequestVote to Node (broadcast) term=1`

3. **Vote Collection**:
   - "Each node votes only ONCE per term"
   - "First-come-first-served basis"
   - "Need majority: 3 out of 5 votes"
   - "In logs, you'd see `Node n2 runs RPC RequestVote called by Node n4`"

4. **Leader Established**:
   - "Once candidate gets 3 votes → becomes LEADER"
   - Point to log: `Node n4 becomes leader term=1`
   - "Leader immediately starts sending heartbeats"

5. **Heartbeat Mechanism**:
   - "Heartbeat = AppendEntries RPC with empty log"
   - "Sent every 1 second to all followers"
   - Point to logs: `Node n4 sends RPC AppendEntries to Node raft_node2:7202`
   - "Followers reset their election timeouts when receiving heartbeat"

6. **Why Randomized Timeouts?**:
   - "Prevents split votes"
   - "Without randomization, all nodes timeout simultaneously"
   - "Multiple candidates would appear, splitting votes"
   - "Randomization (1.5-3 seconds) ensures usually only one candidate"

---

### Demo 4: Raft Log Replication (Q4) (15 minutes)

**Purpose**: Show client requests, log replication, and commit mechanism.

```powershell
# Raft nodes should still be running from Demo 3
# If not: docker compose up -d raft_node1 raft_node2 raft_node3 raft_node4 raft_node5

# Identify current leader (from Demo 3, likely n4 on port 7305)
docker compose logs raft_node1 raft_node2 raft_node3 raft_node4 raft_node5 | Select-String "becomes leader" | Select-Object -Last 1
```

#### Part A: Direct Request to Leader

```powershell
# Submit operation directly to leader (assuming n4 = port 7305)
Invoke-RestMethod -Method POST -Uri "http://localhost:7305/client_request" `
  -ContentType "application/json" `
  -Body '{"operation":"DEMO_OP_1"}'
```

**Expected Response**:
```json
{
  "accepted": true,
  "message": "queued",
  "index": 0,
  "committed_index": -1
}
```

**Watch logs**:
```powershell
docker compose logs raft_node4 | Select-String "DEMO_OP_1"
```

**What you'll see**:
```
raft_node4-1  | Node n4 queued operation 'DEMO_OP_1' at index 0
raft_node4-1  | Node n4 applies operation idx=0 op=DEMO_OP_1
```

**What to explain**:
- "Leader receives client request"
- "Leader appends to its log: `<DEMO_OP_1, term=1, index=0>`"
- "`queued` means added to log but not yet committed"
- "Leader will replicate this in next heartbeat (within 1 second)"

#### Part B: Follower Forwarding

```powershell
# Submit to a FOLLOWER (e.g., n1 on port 7301)
Invoke-RestMethod -Method POST -Uri "http://localhost:7301/client_request" `
  -ContentType "application/json" `
  -Body '{"operation":"DEMO_OP_2"}'
```

**Expected Response**:
```json
{
  "accepted": true,
  "message": "queued",
  "index": 1,
  "committed_index": 0
}
```

**Watch follower logs**:
```powershell
docker compose logs raft_node1 | Select-String "DEMO_OP_2"
```

**What you'll see**:
```
raft_node1-1  | Node n1 sends RPC ClientRequest to Node n4 (forward)
raft_node1-1  | Node n1 applies operation idx=1 op=DEMO_OP_2
```

**What to explain**:
- "Followers don't process client requests directly"
- "Follower n1 forwards to leader n4"
- Point to log: `Node n1 sends RPC ClientRequest to Node n4 (forward)`
- "Leader processes and returns response through follower"
- "This satisfies Instructions.txt requirement: 'client can connect to any process'"

#### Part C: Log Replication and Commit

```powershell
# Wait 2 seconds for heartbeat cycle
Start-Sleep -Seconds 2

# Check that ALL nodes applied both operations
docker compose logs raft_node1 raft_node2 raft_node3 raft_node4 raft_node5 | Select-String "applies operation" | Select-String "DEMO_OP"
```

**What you'll see**:
```
raft_node1-1  | Node n1 applies operation idx=0 op=DEMO_OP_1
raft_node1-1  | Node n1 applies operation idx=1 op=DEMO_OP_2
raft_node2-1  | Node n2 applies operation idx=0 op=DEMO_OP_1
raft_node2-1  | Node n2 applies operation idx=1 op=DEMO_OP_2
raft_node3-1  | Node n3 applies operation idx=0 op=DEMO_OP_1
raft_node3-1  | Node n3 applies operation idx=1 op=DEMO_OP_2
raft_node4-1  | Node n4 applies operation idx=0 op=DEMO_OP_1
raft_node4-1  | Node n4 applies operation idx=1 op=DEMO_OP_2
raft_node5-1  | Node n5 applies operation idx=0 op=DEMO_OP_1
raft_node5-1  | Node n5 applies operation idx=1 op=DEMO_OP_2
```

**What to explain**:

1. **Heartbeat Carries Log**:
   - "Leader sends AppendEntries every 1 second"
   - "Contains ENTIRE log (simplified implementation per Q4 spec)"
   - "Also includes `commit_index` (highest committed entry)"

2. **Follower Processing**:
   - "Follower receives AppendEntries"
   - "Replaces its log with leader's log (snapshot approach)"
   - "Returns ACK to leader"
   - Point to log: `Node n1 runs RPC AppendEntries called by Node n4`

3. **Commit Mechanism**:
   - "Leader tracks ACKs for each log entry"
   - "Once MAJORITY (3 of 5) ACK → entry is COMMITTED"
   - "Leader updates `commitIndex`"
   - "Leader applies entries up to `commitIndex`"
   - Point to log: `Node n4 applies operation idx=0 op=DEMO_OP_1`

4. **Follower Application**:
   - "Followers receive updated `commitIndex` in next AppendEntries"
   - "Followers apply all entries up to `commitIndex`"
   - "This ensures all nodes execute operations in same order"
   - "Consistency achieved!"

5. **Why Sequential Indices?**:
   - "Operations applied in order: idx=0, then idx=1"
   - "Index tracking ensures no gaps"
   - "`lastApplied` tracks what's been executed"
   - "`commitIndex` tracks what's safe to execute"

---

### Demo 5: Failure Scenarios (Q5) (15 minutes)

**Purpose**: Demonstrate fault tolerance and recovery.

#### Test Case 1: Leader Crash and Re-election

```powershell
# Current leader should be known (e.g., n4)
Write-Host "Current leader:" -ForegroundColor Yellow
docker compose logs raft_node1 raft_node2 raft_node3 raft_node4 raft_node5 | Select-String "becomes leader" | Select-Object -Last 1

# Submit operations before crash
Invoke-RestMethod -Method POST -Uri "http://localhost:7305/client_request" `
  -ContentType "application/json" `
  -Body '{"operation":"BEFORE_CRASH"}'

# Stop the leader
docker compose stop raft_node4

# Wait for new election (up to 3 seconds)
Write-Host "`nWaiting for new leader election..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check for new leader
docker compose logs raft_node1 raft_node2 raft_node3 raft_node5 | Select-String "becomes leader" | Select-Object -Last 1
```

**Expected Output**:
```
raft_node1-1  | Node n1 becomes leader term=2
```

**Submit to new leader**:
```powershell
# New leader n1 is on port 7301
Invoke-RestMethod -Method POST -Uri "http://localhost:7301/client_request" `
  -ContentType "application/json" `
  -Body '{"operation":"AFTER_REELECTION"}'

# Verify all remaining nodes applied both operations
docker compose logs raft_node1 raft_node2 raft_node3 raft_node5 | Select-String "applies operation" | Select-String "CRASH\|REELECTION"
```

**Restart old leader**:
```powershell
docker compose start raft_node4
Start-Sleep -Seconds 4

# Verify old leader rejoined as follower and synced log
docker compose logs raft_node4 | Select-String "AFTER_REELECTION\|AppendEntries"
```

**What to explain**:
- "Leader n4 crashed (stopped container)"
- "Followers stopped receiving heartbeats"
- "After 1.5-3 seconds, followers' election timeouts expired"
- "New election started, n1 won with majority votes"
- "n1 became leader with higher term (term=2)"
- "Operations continued on new leader"
- "Old leader restarted, received AppendEntries with higher term"
- "Old leader stepped down to follower"
- "Old leader accepted new leader's log and applied missing operations"
- "Cluster recovered automatically!"

#### Test Case 2: Network Partition

```powershell
# Identify current leader
docker compose logs raft_node1 raft_node2 raft_node3 raft_node4 raft_node5 | Select-String "becomes leader" | Select-Object -Last 1

# Submit operation before partition
Invoke-RestMethod -Method POST -Uri "http://localhost:7301/client_request" `
  -ContentType "application/json" `
  -Body '{"operation":"BEFORE_PARTITION"}'

# Pause leader (simulates network partition - container still runs but frozen)
docker compose pause raft_node1

Write-Host "`nLeader paused (network partition simulated)" -ForegroundColor Yellow
Start-Sleep -Seconds 5

# New election should occur
docker compose logs raft_node2 raft_node3 raft_node4 raft_node5 | Select-String "becomes leader" | Select-Object -Last 1

# Submit during partition (to new leader)
Invoke-RestMethod -Method POST -Uri "http://localhost:7302/client_request" `
  -ContentType "application/json" `
  -Body '{"operation":"DURING_PARTITION"}'

# Unpause (heal partition)
docker compose unpause raft_node1
Write-Host "`nPartition healed" -ForegroundColor Green
Start-Sleep -Seconds 3

# Old leader should sync with new leader
docker compose logs raft_node1 | Select-String "DURING_PARTITION\|AppendEntries" | Select-Object -Last 5
```

**What to explain**:
- "Pause simulates network partition - leader isolated"
- "Leader can't send heartbeats"
- "Remaining 4 nodes still have majority (4 > 5/2)"
- "New leader elected among remaining nodes"
- "Cluster continued operating with 4 nodes"
- "When partition healed, old leader saw higher term"
- "Old leader synchronized with new leader's log"
- "Both operations applied correctly"
- "This demonstrates Raft's partition tolerance"

---

## Technical Explanations

### How 2PC Works (Q1-Q2)

#### Data Structures

**Coordinator State**:
```go
type coordinator struct {
    nodeID       string
    participants []string           // List of participant addresses
    conns        map[string]client  // gRPC connections to participants
}
```

**Participant State**:
```go
type participant struct {
    nodeID string
    vote   string  // "commit" or "abort"
    status string  // "prepared", "committed", "aborted"
}
```

#### Voting Phase Flow

1. **Client → Coordinator**: HTTP POST with transaction ID and operation
2. **Coordinator → All Participants**: `Vote(tx_id, operation)` RPC
3. **Participant Logic**:
   ```go
   func (p *participant) Vote(txID string) string {
       // Check if can commit (always yes in our demo)
       if canCommit() {
           p.vote = "commit"
           p.status = "prepared"
           return "vote-commit"
       }
       return "vote-abort"
   }
   ```
4. **Participants → Coordinator**: "vote-commit" or "vote-abort" response
5. **Coordinator Collection**:
   ```go
   allCommit := true
   for _, participant := range participants {
       if vote := callVoteRPC(participant); vote != "vote-commit" {
           allCommit = false
           break
       }
   }
   ```

#### Decision Phase Flow

1. **Coordinator Decision**:
   ```go
   var decision string
   if allCommit {
       decision = "global-commit"
   } else {
       decision = "global-abort"
   }
   ```

2. **Coordinator → All Participants**: `Decide(tx_id, decision)` RPC
3. **Participant Logic**:
   ```go
   func (p *participant) Decide(txID string, decision string) {
       if decision == "global-commit" {
           p.status = "committed"
           // Actually commit the transaction
           log.Printf("Node %s committed tx %s", p.nodeID, txID)
       } else {
           p.status = "aborted"
           // Rollback the transaction
           log.Printf("Node %s aborted tx %s", p.nodeID, txID)
       }
   }
   ```

#### Why Two Phases?

- **Phase 1 (Voting)**: "Can you commit?" → Ensures all participants are ready
- **Phase 2 (Decision)**: "Here's the final decision" → Ensures atomicity

**Problem 2PC Solves**: Without 2PC, if coordinator crashes after telling some (but not all) participants to commit, database would be inconsistent.

**Limitation**: Coordinator is single point of failure. If it crashes during decision phase, participants are blocked.

---

### How Raft Works (Q3-Q4)

#### Data Structures

```go
type raftServer struct {
    // Identity
    mu     sync.Mutex
    id     string
    peers  []string
    conns  map[string]client
    
    // Election state
    currentTerm   int64
    votedFor      string
    state         role  // Follower, Candidate, Leader
    electionReset time.Time
    leaderAddr    string
    
    // Log replication state
    log         []*LogEntry
    commitIndex int64  // Highest log entry known to be committed
    lastApplied int64  // Highest log entry applied to state machine
    ackCounts   map[int64]int  // ACK tracking per log index
}

type LogEntry struct {
    Operation string
    Term      int64
    Index     int64
}

type role int
const (
    Follower role = iota
    Candidate
    Leader
)
```

#### Leader Election Algorithm (Q3)

**State Machine**:
```
FOLLOWER → (timeout) → CANDIDATE → (majority votes) → LEADER
             ↑                          ↓
             └────────(heartbeat)───────┘
```

**Election Timeout**:
```go
func (r *raftServer) runElectionTimer() {
    for {
        r.mu.Lock()
        timeout := randomTimeout(1500, 3000)  // 1.5-3 seconds
        r.mu.Unlock()
        
        time.Sleep(timeout)
        
        r.mu.Lock()
        if time.Since(r.electionReset) >= timeout && r.state != Leader {
            r.startElection()
        }
        r.mu.Unlock()
    }
}
```

**Start Election**:
```go
func (r *raftServer) startElection() {
    r.state = Candidate
    r.currentTerm++
    r.votedFor = r.id
    r.leaderAddr = ""
    
    // Request votes from all peers
    voteCh := make(chan bool, len(r.peers))
    for _, peer := range r.peers {
        go func(p string) {
            reply := callRequestVote(p, r.currentTerm, r.id)
            voteCh <- reply.VoteGranted
        }(peer)
    }
    
    // Count votes
    votes := 1  // Self vote
    needed := (len(r.peers)+1)/2 + 1
    for i := 0; i < len(r.peers); i++ {
        if <-voteCh {
            votes++
            if votes >= needed {
                r.becomeLeader()
                return
            }
        }
    }
}
```

**Become Leader**:
```go
func (r *raftServer) becomeLeader() {
    r.state = Leader
    r.leaderAddr = r.id
    r.ackCounts = make(map[int64]int)  // Reset ACK tracking
    
    go r.runHeartbeats()  // Start sending heartbeats
}
```

**Heartbeats**:
```go
func (r *raftServer) runHeartbeats() {
    ticker := time.NewTicker(1 * time.Second)
    for r.state == Leader {
        <-ticker.C
        
        // Send AppendEntries to all peers
        for _, peer := range r.peers {
            go func(p string) {
                // Send log snapshot and commit index
                reply := callAppendEntries(p, r.currentTerm, r.id, r.log, r.commitIndex)
                if reply.Success {
                    // Track ACKs for commit
                }
            }(peer)
        }
    }
}
```

#### Log Replication Algorithm (Q4)

**Client Request Processing**:
```go
func (r *raftServer) ClientRequest(op string) Response {
    r.mu.Lock()
    defer r.mu.Unlock()
    
    // If not leader, forward to leader
    if r.state != Leader {
        if r.leaderAddr == "" {
            return Response{Accepted: false, Message: "no leader"}
        }
        return r.connsByID[r.leaderAddr].ClientRequest(op)
    }
    
    // Leader: append to log
    index := int64(len(r.log))
    entry := &LogEntry{
        Operation: op,
        Term:      r.currentTerm,
        Index:     index,
    }
    r.log = append(r.log, entry)
    r.ackCounts[index] = 1  // Leader implicitly ACKs
    
    return Response{
        Accepted:       true,
        Message:        "queued",
        Index:          index,
        CommittedIndex: r.commitIndex,
    }
}
```

**AppendEntries RPC (Follower)**:
```go
func (r *raftServer) AppendEntries(args *AppendEntriesArgs) Reply {
    r.mu.Lock()
    defer r.mu.Unlock()
    
    // Update term if behind
    if args.Term > r.currentTerm {
        r.currentTerm = args.Term
        r.state = Follower
        r.votedFor = ""
    }
    
    // Accept leader and reset election timeout
    r.electionReset = time.Now()
    r.leaderAddr = args.LeaderId
    
    // Replace log with leader's snapshot
    r.log = cloneLog(args.Entries)
    
    // Apply committed entries
    r.applyEntries(args.CommitIndex)
    
    return Reply{Success: true, AppliedUpTo: r.lastApplied}
}
```

**Commit Mechanism (Leader)**:
```go
func (r *raftServer) handleAppendEntriesReply(reply *Reply) {
    r.mu.Lock()
    defer r.mu.Unlock()
    
    // Track ACKs
    for idx := r.commitIndex + 1; idx <= reply.AppliedUpTo; idx++ {
        r.ackCounts[idx]++
        
        // Check if majority reached
        needed := (len(r.peers)+1)/2 + 1
        if r.ackCounts[idx] >= needed {
            r.commitIndex = idx
            r.applyEntries(r.commitIndex)
        }
    }
}
```

**Apply Entries**:
```go
func (r *raftServer) applyEntries(upTo int64) {
    for r.lastApplied < upTo {
        nextIdx := r.lastApplied + 1
        
        // Find entry with this index
        var found *LogEntry
        for _, e := range r.log {
            if e.Index == nextIdx {
                found = e
                break
            }
        }
        
        if found != nil {
            // Execute the operation
            log.Printf("Node %s applies operation idx=%d op=%s",
                r.id, found.Index, found.Operation)
            r.lastApplied = nextIdx
        } else {
            break  // Gap in log
        }
    }
}
```

#### Why Raft Works

1. **Leader Election**: Ensures single source of truth (one leader per term)
2. **Randomized Timeouts**: Prevents split votes (usually one candidate wins)
3. **Majority Votes**: Ensures new leader has most up-to-date log
4. **Heartbeats**: Keeps followers informed and prevents unnecessary elections
5. **Log Replication**: Leader broadcasts all operations to followers
6. **Majority Commit**: Only commit when majority ACK (ensures durability)
7. **Term Tracking**: Detects stale leaders and triggers new elections

**Invariant**: If operation is committed on any node, it will eventually be on all nodes (even after failures and recoveries).

---

## Common Questions and Answers

### Q1: "Why didn't you use the official gRPC library?"

**A**: We used a custom embedded gRPC implementation for two reasons:

1. **Hermetic Builds**: Docker containers don't need protoc or gRPC installed on the host
2. **Simplicity**: The custom implementation is ~100 lines and handles our needs
3. **Instructions**: The assignment focused on consensus algorithms, not gRPC setup

The trade-off: Custom gRPC lacks features like auth, compression, streaming. For this project, simple request/response is sufficient.

### Q2: "What happens if a participant votes abort in 2PC?"

**A**: The coordinator would send `global-abort` to ALL participants, even those that voted commit. In our implementation, participants always vote commit for demonstration, but the decision phase logic handles both cases:

```go
if voteAbort {
    decision = "global-abort"
}
// All participants rollback
```

### Q3: "What if more than 2 nodes fail in Raft?"

**A**: With 5 nodes, we can tolerate up to 2 failures (majority is 3):

- **0-2 failures**: Cluster operational (majority exists)
- **3+ failures**: No majority → no leader election → cluster blocked

This is fundamental to consensus: You need `n/2 + 1` nodes to make progress. 5-node cluster tolerates 2 failures, 7-node tolerates 3, etc.

### Q4: "Why do you send the entire log in AppendEntries?"

**A**: Per Instructions.txt Q4 specification: "sends its entire log to all the other servers". This is a **simplified** implementation for teaching purposes.

**Standard Raft** uses incremental replication:
- Only send new entries
- Include `prevLogIndex` and `prevLogTerm` for consistency check
- Follower validates match with its log
- On mismatch, leader decrements index and retries

**Our approach** (full snapshot) is easier to implement and understand, but less efficient for large logs.

### Q5: "How do you know which node is the leader?"

**A**: Each node tracks the current leader:

1. **Leader election**: Winner becomes leader and caches `leaderAddr = self`
2. **Heartbeats**: Followers receive AppendEntries, cache `leaderAddr = args.LeaderId`
3. **Client requests**: Followers check `r.leaderAddr` and forward via `r.connsByID[leaderAddr]`

This was one of the bugs we fixed - initially we only used `votedFor`, which doesn't reliably identify the current leader.

### Q6: "Does 2PC guarantee consistency?"

**A**: 2PC guarantees **atomicity** (all-or-nothing), not full consistency:

**Guarantees**:
- All participants either commit OR all abort (no partial commits)
- If coordinator decides commit, all participants will commit

**Limitations**:
- **Blocking**: If coordinator crashes during decision phase, participants wait forever
- **Not partition-tolerant**: Network split can leave some participants uncertain
- **Coordinator SPOF**: Coordinator failure blocks the system

**Raft is better** for these reasons: No single point of failure, partition-tolerant (with majority), non-blocking (elects new leader).

### Q7: "Can I submit multiple operations at once?"

**A**: Yes! Each operation gets a unique index:

```powershell
# These go to leader as index 0, 1, 2
Invoke-RestMethod ... -Body '{"operation":"op1"}'
Invoke-RestMethod ... -Body '{"operation":"op2"}'
Invoke-RestMethod ... -Body '{"operation":"op3"}'
```

Leader queues them in order. All nodes will apply them in order (idx=0, then idx=1, then idx=2). This is the **consistency guarantee** of Raft.

### Q8: "What's the difference between commitIndex and lastApplied?"

**A**:
- **`commitIndex`**: Highest log entry that has been replicated to majority (safe to execute)
- **`lastApplied`**: Highest log entry that has been executed by this node's state machine

**Example timeline**:
```
Time 0: log=[op1(idx=0)], commitIndex=-1, lastApplied=-1
Time 1: Majority ACK op1 → commitIndex=0, lastApplied=-1 (not yet applied)
Time 2: Apply op1 → commitIndex=0, lastApplied=0 (now applied)
```

There's always: `lastApplied ≤ commitIndex ≤ last log index`

### Q9: "How do I prove this works in the demo?"

**Best Proof Strategy**:

1. **Show logs**: Terminal with `docker compose logs -f` running
2. **Explain before executing**: "I'm going to stop the leader, watch for new election"
3. **Execute command**: `docker compose stop raft_node4`
4. **Point to logs**: "See here - n1 becomes leader term=2"
5. **Submit operation**: Show it works under new leader
6. **Restart old leader**: Show it syncs without manual intervention
7. **Verify consistency**: Show ALL nodes have same operations applied

**Key phrase**: "Notice that the system recovered automatically without any manual intervention - that's the power of Raft consensus!"

### Q10: "What if someone asks about CAP theorem?"

**A**:
- **2PC**: CP (Consistency + Partition intolerance). Blocks on partition.
- **Raft**: CP (Consistency + Partition intolerance). Requires majority, which may not exist during partition. But unlike 2PC, Raft recovers automatically when partition heals.

Neither sacrifices consistency for availability. For AP (Availability + Partition tolerance), you'd use eventually consistent systems like DynamoDB or Cassandra.

---

## Tips for Effective Demo

### Preparation

1. **Test Everything First**: Run through the demo alone to catch issues
2. **Clean State**: `docker compose down` before starting to avoid stale containers
3. **Terminal Setup**: Have 3 terminals open:
   - Terminal 1: Commands (Invoke-RestMethod)
   - Terminal 2: Logs (docker compose logs -f)
   - Terminal 3: Spare for queries (grep, Select-String)
4. **Timing**: Allow 5-10 seconds after starting containers before first command
5. **Browser Ready**: Have `http://localhost:8080` bookmarked for Python GUI demo

### During Demo

1. **Narrate**: Say what you're doing before doing it
2. **Point**: Physically point at logs or output as you explain
3. **Pause**: Give audience time to read logs before moving on
4. **Ask Questions**: "Does anyone see the leader election here?" (engagement)
5. **Failures are OK**: If something doesn't work, explain what went wrong (shows understanding)

### Key Phrases

- "The original system still works exactly as before - we added consensus on top"
- "Watch the logs here - you'll see the voting phase messages"
- "Notice every node applied the same operations in the same order - that's consistency"
- "When the leader fails, a new election happens automatically within 3 seconds"
- "This is why Raft is used in production systems like etcd and Consul"

### Handling Questions

**Don't Know Answer**: "That's a great question - let me check the code" (then look it up)  
**Technical Depth**: Match questioner's level - use analogies for non-technical, code for technical  
**Off-Topic**: "That's related but beyond scope - happy to discuss after"  
**Challenge**: "Let me show you" (demo it!)  

---

## Quick Reference Commands

### Start Everything
```powershell
cd "c:\Users\might\OneDrive\Desktop\School\Distributed Systems\Phase 3"
docker compose up -d
```

### Test 2PC
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:7100/auction.TwoPCCoordinator/StartVoting" -ContentType "application/json" -Body '{"tx_id":"test-001","operation":"test"}'
docker compose logs 2pc_coordinator | Select-String "Phase"
```

### Test Raft Leader
```powershell
docker compose logs raft_node1 raft_node2 raft_node3 raft_node4 raft_node5 | Select-String "becomes leader"
```

### Test Raft Operation
```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:7301/client_request" -ContentType "application/json" -Body '{"operation":"test_op"}'
docker compose logs raft_node1 raft_node2 raft_node3 raft_node4 raft_node5 | Select-String "applies operation"
```

### Stop Everything
```powershell
docker compose down
```

---

**Good luck with your demo! You've got this! 🚀**
