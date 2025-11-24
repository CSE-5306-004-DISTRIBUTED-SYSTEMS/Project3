# Project Assignment 3 Report

2258-CSE-5306-004  
Name:

- John Song - 10023064679
- Adam Emerson - 1000773509

Github link: https://github.com/CSE-5306-004-DISTRIBUTED-SYSTEMS/Project3.git


## Projects 
Here are project to implement for assignment 3: 
- Group 15 Distributed music Queue System: https://github.com/mgm67671/Distributed-Systems
- Group 1 Distributed picture sharing system : https://github.com/J1anXu/Distributed-picture-sharing-system





## 2PC

### Overview of Group 1 Distributed picture sharing system  

A distributed system for sharing pictures with HTTP and gRPC implementations.

#### Functions
- Upload pictures - Automatically distributed across nodes
- Search pictures - Find which node stores your picture
- Download pictures - Retrieve from any node
- Delete pictures - Remove from the system
- Like pictures - Increment like counter

#### Structures

- 3 HTTP nodes (ports 5001-5003) - Layered architecture
- 3 gRPC nodes (ports 50051-50053) - Microservices architecture
- 1 Web interface (port 8000) - User interface

### Requiremnts 

#### 1. voting phase 
- The coordinator sends a vote-request message to all participants.
- When a participant receives a vote-request message, it returns either a vote-commit message to the coordinator, telling the coordinator that it is prepared to locally commit its part of the transaction, or otherwise, a vote-abort message.

#### 2. decision phase 
- The coordinator collects all votes from the participants. If all participants have voted to commit the transaction, then so will the coordinator. In that case, it sends a global-commit message to all participants. However, if one participant had voted to abort the transaction, the coordinator will also decide to abort the transaction and multicasts a global-abort message.

- Each participant that voted for a commit waits for the final reaction by the coordinator. If a participant receives a global-commit message, it locally commits the transaction. Otherwise, when receiving a global-abort message, the transaction is locally aborted as well.


### Implementation

- Using gRPC for any programming languages. `(./grpc_nodes/picture.proto)`
- Add 2 phase commit code to gRPC node as participants  `(./grpc_nodes/node.py)`
- add 2 phase commit code to http node as coordinator `(./http_nodes/node.py)`




### Test out 

#### 1. Delete Sucessfully 
`curl -X DELETE http://localhost:5001/delete-2pc/demo.png `

gRPC node as participants
```
Phase Voting of Node grpc-node1 received RPC VoteRequest from Phase Voting of Node http-node1

Phase Voting of Node grpc-node1 sends RPC VoteCommit to Phase Voting of Node http-node1

Phase Decision of Node grpc-node1 received RPC GlobalCommit from Phase Decision of Node http-node1

Phase Decision of Node grpc-node1 sends RPC Ack to Phase Decision of Node http-node1

```

http node as coordinator 

```
--- Starting 2PC Transaction 2894e6fd-267d-42d8-9b3e-8c383bed93ce for demo.png ---
Node http-node1 sends RPC VoteRequest to Node grpc-node1
Node http-node1 sends RPC VoteRequest to Node grpc-node2
Node http-node1 sends RPC VoteRequest to Node grpc-node3
Node http-node1 sends RPC GlobalCommit to Node grpc-node1
Node http-node1 sends RPC GlobalCommit to Node grpc-node2
Node http-node1 sends RPC GlobalCommit to Node grpc-node3
```

Overall you will get `{"details":["ACK","ACK","ACK"],"status":"COMMITTED","transaction_id":"2894e6fd-267d-42d8-9b3e-8c383bed93ce"}`


#### 2. Delete Aborted

gRPC node as participants

```
Phase Voting of Node grpc-node1 received RPC VoteRequest from Phase Voting of Node http-node1

Phase Voting of Node grpc-node1 sends RPC VoteAbort to Phase Voting of Node http-node1

Phase Decision of Node grpc-node1 received RPC GlobalAbort from Phase Decision of Node http-node1

Phase Decision of Node grpc-node1 sends RPC Ack to Phase Decision of Node http-node1
```

http node as coordinator 

```
--- Starting 2PC Transaction 2d066ce6-509f-4119-951b-5a58e7549274 for demo1.png ---
Node http-node1 sends RPC VoteRequest to Node grpc-node1
Node http-node1 sends RPC VoteRequest to Node grpc-node2
Node http-node1 sends RPC VoteRequest to Node grpc-node3
Node http-node1 sends RPC GlobalAbort to Node grpc-node1
Node http-node1 sends RPC GlobalAbort to Node grpc-node2
Node http-node1 sends RPC GlobalAbort to Node grpc-node3
```

## Raft 

### Overview of Group 15 Distributed music Queue System 
This project implements a distributed music queue system.

A Microservices (gRPC) design. Both architectures support distributed queue management, voting, metadata, simulated playing, and playback history, and are fully containerized for easy scaling and testing.

#### Functions
- Add a track 
- Play the next track 
- view play history 
- Current queue 
- Get track metadata 
- Vote for a track 
- Remove a track

#### Structures
- Python gRPC services (5 nodes)
- Redis backend (1 node)
- gRPC communication, 
- Nginx load balancer for gRPC (1 node)

### Requiremnts  

#### 1. Role: Each node must operate in one of three states:

- Leader: Handles client requests and manages log replication.

- Follower: Passive state; responds to RPCs and expects heartbeats.

- Candidate: Temporary state active only during elections.

#### 2. Leader Election 
- Timers:
    - Heartbeat Timeout: Fixed at 1.0 second.
    - Election Timeout: Randomized per node between 1.5 and 3.0 seconds to prevent split votes.

- Election Logic:
    - If a Follower receives no heartbeat within the election timeout, it transitions to Candidate.
    - The Candidate increments its Term, votes for itself, and broadcasts RequestVote RPCs.
    - A Leader is elected immediately upon receiving a majority of votes (3 out of 5).
    - If a higher term is detected in any incoming message, the node reverts to Follower.

#### 3. Log Replication & Consistency 
- Client: 
    - Client will access through nginx entry gate 
    - If a client connects to a follower, the request must be forwarded to the Leader.

- Replication:
    1. Leader appends the operation (e.g., AddTrack) to its local Log.
    2. Leader sends its entire log (simplified requirement) via AppendEntries RPC to all Followers.
    3. Followers replace their log with the Leader's log and return an ACK.
    4. Once a majority of ACKs are received, the Leader Commits the entry (executes the operation).
    5. Followers execute operations up to the Leader’s commit index (c).


### Implementation
- `raft.proto` has been created `queue-service/raft.proto`
-  server logic `queue-service/raft_server.py`
- docker implementation `microservice-grpc/docker-compose.yml`


### Test out 

#### Question 3
##### Test Case 1: heartbeat timeout & Test Case 2: election timeout.

```
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:21,514 INFO: Raft Node 5 started on port 50051
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:23,397 INFO: runs RPC RequestVote called by Node 2
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:23,397 INFO: Transition to FOLLOWER term=1
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:23,402 INFO: runs RPC AppendEntries called by Node 2
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:23,890 INFO: runs RPC RequestVote called by Node 3
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:23,929 INFO: Election timeout -> start election
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:23,929 INFO: Became CANDIDATE for term 1
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:23,929 INFO: sends RPC RequestVote to Node 1
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:23,929 INFO: sends RPC RequestVote to Node 2
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:23,930 INFO: sends RPC RequestVote to Node 3
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:23,930 INFO: sends RPC RequestVote to Node 4
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:24,442 INFO: runs RPC RequestVote called by Node 4
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:24,452 INFO: runs RPC AppendEntries called by Node 2
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:24,575 INFO: runs RPC RequestVote called by Node 1
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:25,468 INFO: runs RPC AppendEntries called by Node 2
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:25,849 INFO: Election timeout -> start election
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:25,849 INFO: Became CANDIDATE for term 2
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:25,849 INFO: sends RPC RequestVote to Node 1
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:25,850 INFO: sends RPC RequestVote to Node 2
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:25,850 INFO: sends RPC RequestVote to Node 3
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:25,852 INFO: sends RPC RequestVote to Node 4
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:25,857 INFO: Won election and became LEADER for term 2

```

```
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:25,857 INFO: Won election and became LEADER for term 2
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:25,857 INFO: sends RPC AppendEntries to Node 1
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:25,858 INFO: sends RPC AppendEntries to Node 2
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:25,860 INFO: sends RPC AppendEntries to Node 3
microservices-grpc-raft-node5-1  | [Node 5] 2025-11-24 02:09:25,861 INFO: sends RPC AppendEntries to Node 4


```


**1.Heartbeat Timeout (The Trigger)**

In a healthy Raft cluster, the Leader must send periodic heartbeats (`AppendEntries`) to reset the election timers on all Followers. If these heartbeats arrive too slowly (exceeding the timeout threshold), the Follower assumes the Leader has failed.

* **Evidence:**
    * At `02:09:23,402`, Node 5 receives a heartbeat (`RPC AppendEntries`) from **Node 2** (the current leader of Term 1).
    * However, by `02:09:23,929` (approx. 527ms later), Node 5 has not received a sufficient follow-up or valid leadership confirmation.
* **Result:** `[Node 5] ... Election timeout -> start election`.
* **Analysis:** This demonstrates that Node 5’s internal timer expired because the Leader (Node 2) failed to assert its authority within the randomized window. This automatic failure detection is the core of Raft's fault tolerance.

**2.Election Timeout (The "Split Vote" Resolution)**

Raft uses randomized election timeouts to prevent nodes from becoming candidates simultaneously (which causes split votes where no one wins).

**The First Attempt (Term 1 Failure):**
* At `02:09:23,929`, Node 5 becomes a **CANDIDATE for Term 1** and requests votes.
* At `02:09:24,452`, Node 5 receives `RPC AppendEntries` from Node 2. This indicates a conflict: Node 2 still thinks it is the leader of Term 1.
* Because of this conflict and potential split votes from other nodes (Node 3 and 4 are also active in the logs), Node 5 fails to gather a majority for Term 1.

**The Second Attempt (Term 2 Success):**
* At `02:09:25,849`, Node 5 experiences a *second* **Election Timeout**.
* **Action:** It increments the logical clock: `Became CANDIDATE for term 2`.
* **Resolution:** Because Node 5 transitioned to Term 2, it now holds a higher authority than the old Leader (Node 2, Term 1).
* At `02:09:25,857`, Node 5 logs: `Won election and became LEADER for term 2`.




#### Question 4

##### Test Case 3 Fowarding 

`python client.py add --id 8 --title "Forwarding Test" --artist "Test Case 3-2" --duration 180`


```
AddTrack response: message: "Queued"
queue {
  id: "8"
  title: "Forwarding Test"
  artist: "Test Case 2-2"
  duration: 180
}
```

Leader log Node 1 (Node Unkown: is the client node)
```
[Node 1] 2025-11-24 02:52:53,978 INFO: Node 1 runs RPC AddTrack called by Node unknown
[Node 1] 2025-11-24 02:52:53,978 INFO: Leader appended log[1]
[Node 1] 2025-11-24 02:52:53,981 INFO: Advanced commit_index -> 1
[Node 1] 2025-11-24 02:52:53,981 INFO: Applying log[1] cmd=ADD
[Node 1] 2025-11-24 02:52:53,982 INFO: AddTrack committed
```

Follower log Node 4
```
[Node 4] 2025-11-24 02:49:38,368 INFO: Voted for 1
[Node 4] 2025-11-24 02:51:29,801 INFO: Applying log[0] cmd=ADD
[Node 4] 2025-11-24 02:52:54,165 INFO: Applying log[1] cmd=ADD
[Node 4] 2025-11-24 02:53:05,411 INFO: Applying log[2] cmd=ADD

```

##### Test Case 4 Deleting Node

After stop leader node, it election restarts 

```
[Node 5] 2025-11-24 02:57:08,553 INFO: RequestVote from 3 (term 2)
[Node 5] 2025-11-24 02:57:08,554 INFO: Transition to FOLLOWER term=2, leader=None
[Node 5] 2025-11-24 02:57:08,554 INFO: Voted for 3


[Node 4] 2025-11-24 02:57:08,553 INFO: RequestVote from 3 (term 2)
[Node 4] 2025-11-24 02:57:08,554 INFO: Transition to FOLLOWER term=2, leader=None
[Node 4] 2025-11-24 02:57:08,554 INFO: Voted for 3

```

Leader Node 3 

```
[Node 3] 2025-11-24 02:57:08,532 INFO: Election timeout -> start election
[Node 3] 2025-11-24 02:57:08,532 INFO: Became CANDIDATE for term 2
[Node 3] 2025-11-24 02:57:08,554 INFO: Won election and became LEADER for term 2
```



##### Test Case 5 Add New Node

Add one new one 

```
[Node 1] 2025-11-24 02:59:25,018 INFO: RaftServer initialized
[Node 1] 2025-11-24 02:59:25,018 INFO: Starting gRPC server on [::]:50051
[Node 1] 2025-11-24 02:59:28,027 INFO: Election timeout -> start election
[Node 1] 2025-11-24 02:59:28,028 INFO: Became CANDIDATE for term 1
[Node 1] 2025-11-24 02:59:28,046 INFO: Observed higher term 2 from 2; becoming follower
[Node 1] 2025-11-24 02:59:28,046 INFO: Transition to FOLLOWER term=2, leader=None
[Node 1] 2025-11-24 02:59:29,592 INFO: Election timeout -> start election
[Node 1] 2025-11-24 02:59:29,592 INFO: Became CANDIDATE for term 3
[Node 1] 2025-11-24 02:59:31,580 INFO: RequestVote from 5 (term 4)
[Node 1] 2025-11-24 02:59:31,580 INFO: Transition to FOLLOWER term=4, leader=None
[Node 1] 2025-11-24 02:59:31,580 INFO: Voted for 5
[Node 1] 2025-11-24 02:59:32,490 INFO: Applying log[0] cmd=ADD
[Node 1] 2025-11-24 02:59:32,490 INFO: Applying log[1] cmd=ADD
[Node 1] 2025-11-24 02:59:32,490 INFO: Applying log[2] cmd=ADD

```