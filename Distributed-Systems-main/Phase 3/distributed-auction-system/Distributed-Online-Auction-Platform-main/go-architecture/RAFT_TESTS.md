# Raft Q5 Test Case Skeleton

This document outlines five test scenarios to validate the simplified Raft implementation (leader election + log replication).

## 1. Leader Crash and Re-Election
- Start full cluster: `docker compose up -d raft_node1 raft_node2 raft_node3 raft_node4 raft_node5`.
- Submit two operations to current leader (observe leader via logs).
- Stop leader container: `docker compose stop raft_node3` (replace with actual leader ID).
- Expect: remaining followers trigger election after their randomized timeouts; new leader elected; heartbeats resume.
- Restart old leader: `docker compose start raft_node3`.
- Verify it becomes follower and receives full log snapshot with committed entries applied.

## 2. Split Vote Scenario
- Temporarily reduce election timeout range for all nodes (manual code tweak or environment override) so multiple candidates emerge simultaneously.
- Observe logs showing multiple `RequestVote` broadcasts in same term and failed majority.
- Confirm new term starts and one candidate eventually wins.

## 3. Forwarded Client Request from Follower
- Identify leader (e.g., `n3`).
- Send `ClientRequest` to a follower (e.g., port 7202):
  ```bash
  curl -X POST http://localhost:7202/auction.RaftNode/ClientRequest -H 'Content-Type: application/json' -d '{"operation":"opX"}'
  ```
- Expect follower logs forwarding message; leader appends log entry; majority ACK commits.
- Verify follower applies operation after commit index advances.

## 4. New Node Join
- Launch existing cluster (4 nodes) without node5.
- Submit operations; commit several entries.
- Start node5: `docker compose up -d raft_node5`.
- Expect initial heartbeats deliver full log snapshot and node5 applies all committed operations.
- Confirm node5 does not trigger election due to timely heartbeat.

## 5. Heartbeat Loss / Network Partition
- Simulate partition: `docker compose pause raft_node3` (leader) to freeze heartbeats.
- Followers elect new leader after timeouts.
- Resume original leader: `docker compose unpause raft_node3`.
- Expect original leader steps down (receives higher term) and overwrites its stale log with current leader snapshot.

## Evidence Capture
For each scenario record:
- Relevant `docker compose logs -f` excerpts (leader election, append entries, apply lines).
- ClientRequest responses (accepted index, committed index changes).
- Screenshots of terminal logs and curl outputs.

## Future Enhancements (Optional)
- Implement incremental AppendEntries (prevLogIndex/prevLogTerm + entries) instead of full snapshot.
- Add persistent storage (recover term & votedFor across restarts).
- Conflict resolution for divergent logs after partition.
