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



## 1. 2PC How to run  

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


## 2. Raft how to run 

