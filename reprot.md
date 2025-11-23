# Project Assignment 3 Report

2258-CSE-5306-004  
Name:

- John Song - 10023064679
- Adam Emerson - 1000773509


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



