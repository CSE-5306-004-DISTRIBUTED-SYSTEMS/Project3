# Project3
Project Assignment 3: Making Your Systems Fault Tolerant via 2PC & Raft
2258-CSE-5306-004  
Name:  
- John Song - 1002306479
- Adam Emerson - 1000773509



## Projects 
Here are project to implement for assignment 3: 
- Group 15 Distributed music Queue System: https://github.com/mgm67671/Distributed-Systems
- Group 1 Distributed picture sharing system : https://github.com/J1anXu/Distributed-picture-sharing-system

## Quick Start

### 1. 2PC 

This is based on Group 1 -- dirstributed picture sharing system.  

1. `cd Distributed-picture-sharing-system-main`
2. `docker-compose up --build`
3. `docker ps` to check all nodes 
4. upload one same picture to all gRPC nodes 
5. open terminal run `curl -X DELETE http://localhost:5001/delete-2pc/demo.png `
6. check logs `docker logs -f distributed-picture-sharing-system-main-http-node1-1`


After perform delete function, you will see logs like below 
```
Node http-node1 sends RPC VoteRequest to Node grpc-node1
Node http-node1 sends RPC VoteRequest to Node grpc-node2
Node http-node1 sends RPC VoteRequest to Node grpc-node3
Node http-node1 sends RPC GlobalCommit to Node grpc-node1
Node http-node1 sends RPC GlobalCommit to Node grpc-node2
Node http-node1 sends RPC GlobalCommit to Node grpc-node3
```

If all grpc-nodes have same picture, it will return global commit to delete it. Otherwise, it will be aborted. 


### 2. Raft 

This is based on Group 15 -- Distributed music Queue System. 

#### Question 3
1. `cd Distributed-Systems-main`
2. `cd microservices-grpc`
3. `docker-compose up --build` create docker images
4. `python queue-service/client.py add --id 123 --title "Retry" --artist "Me" --duration 100` to add data point 

5. `docker compose -f docker-compose.yml logs` to check logs 


#### Question 4
1. `cd Distributed-Systems-main`
2. `cd question4`
3. `docker-compose up --build` create docker images

4. `python queue-service/client.py add --id 8 --title "Forwarding Test" --artist "Test Case 3-2" --duration 180` to add data point 

5. `docker compose -f docker-compose.yml logs` to check logs.

if `client.py` does not work.  please `cd queue-service` generate `.proto` first 
```
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. queue.proto

python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. raft.proto
```





The below should show up
```
AddTrack response: message: "Queued"
queue {
  id: "8"
  title: "Forwarding Test"
  artist: "Test Case 2-2"
  duration: 180
}

```



`docker compose -f docker-compose.yml logs` to check logs

Between node logs 
```
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:03,525 INFO: Transition to FOLLOWER term=321
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:04,036 INFO: runs RPC RequestVote called by Node 2
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:04,491 INFO: runs RPC AppendEntries called by Node 4
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:04,492 INFO: runs RPC AppendEntries called by Node 1
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:05,201 INFO: Election timeout -> start election
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:05,201 INFO: Became CANDIDATE for term 322
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:05,202 INFO: sends RPC RequestVote to Node 1
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:05,203 INFO: sends RPC RequestVote to Node 2
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:05,204 INFO: sends RPC RequestVote to Node 4
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:05,204 INFO: sends RPC RequestVote to Node 5
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:05,211 INFO: Won election and became LEADER for term 322
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:05,212 INFO: sends RPC AppendEntries to Node 1
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:05,214 INFO: sends RPC AppendEntries to Node 2
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:05,216 INFO: sends RPC AppendEntries to Node 4
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:05,217 INFO: sends RPC AppendEntries to Node 5
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:05,514 INFO: runs RPC AppendEntries called by Node 4
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:05,518 INFO: runs RPC AppendEntries called by Node 1
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:05,568 INFO: runs RPC RequestVote called by Node 5
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:06,219 INFO: sends RPC AppendEntries to Node 1
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:06,221 INFO: sends RPC AppendEntries to Node 2
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:06,222 INFO: sends RPC AppendEntries to Node 4
microservices-grpc-raft-node3-1  | [Node 3] 2025-11-24 02:22:06,224 INFO: sends RPC AppendEntries to Node 5
```



## Reference
- Gemini & ChatGPT 
- https://renjieliu.gitbooks.io/consensus-algorithms-from-2pc-to-raft/content/index.htmlLinks 
