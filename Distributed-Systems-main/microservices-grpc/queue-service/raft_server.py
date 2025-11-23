import grpc
from concurrent import futures
import time
import random
import threading
import os
import sys

# Import generated code
import queue_pb2
import queue_pb2_grpc
import raft_pb2
import raft_pb2_grpc

# --- Configuration ---
NODE_ID = int(os.environ.get('NODE_ID', 1))
PEERS_MAP = os.environ.get('PEERS', '') # Format: "1=host:port,2=host:port"
PEERS = {}
if PEERS_MAP:
    for p in PEERS_MAP.split(','):
        if '=' in p:
            pid, addr = p.split('=')
            if int(pid) != NODE_ID:
                PEERS[int(pid)] = addr

# Timers (Requirements: Heartbeat=1s, Election=1.5-3s)
HEARTBEAT_INT = 1.0
ELECTION_MIN = 1.5
ELECTION_MAX = 3.0

class RaftServer(queue_pb2_grpc.QueueServiceServicer, raft_pb2_grpc.RaftServiceServicer):
    def __init__(self):
        self.lock = threading.RLock()
        
        # --- Raft State ---
        self.term = 0
        self.voted_for = None
        self.log = [] # List of raft_pb2.LogEntry
        self.commit_index = -1
        self.last_applied = -1
        
        self.state = "FOLLOWER" # FOLLOWER, CANDIDATE, LEADER
        self.leader_id = None
        self.last_heartbeat = time.time()
        self.election_timeout = random.uniform(ELECTION_MIN, ELECTION_MAX)
        
        # --- Application State (In-Memory Music Queue) ---
        # We use in-memory state to verify Raft replication is working 
        # (Redis would hide replication issues by sharing state)
        self.music_queue = [] 
        
        # --- Background Timer ---
        threading.Thread(target=self._timer_loop, daemon=True).start()

    # =========================================================
    #  RAFT CORE: TIMERS & ELECTION
    # =========================================================
    def _timer_loop(self):
        while True:
            with self.lock:
                now = time.time()
                if self.state == "LEADER":
                    if now - self.last_heartbeat >= HEARTBEAT_INT:
                        self._send_heartbeats()
                        self.last_heartbeat = now
                else:
                    if now - self.last_heartbeat >= self.election_timeout:
                        print(f"Node {NODE_ID} Election Timeout. Becoming CANDIDATE.")
                        self._start_election()
            time.sleep(0.1)

    def _start_election(self):
        self.state = "CANDIDATE"
        self.term += 1
        self.voted_for = NODE_ID
        self.last_heartbeat = time.time()
        self.election_timeout = random.uniform(ELECTION_MIN, ELECTION_MAX)
        
        # Prepare VoteArgs
        last_idx = len(self.log) - 1
        last_term = self.log[last_idx].term if last_idx >= 0 else 0
        
        args = raft_pb2.VoteArgs(
            term=self.term, candidate_id=NODE_ID,
            last_log_index=last_idx, last_log_term=last_term
        )
        
        self.votes_received = 1 # Vote for self
        
        # Async send to peers
        for pid, addr in PEERS.items():
            threading.Thread(target=self._send_vote_request, args=(pid, addr, args)).start()

    def _send_vote_request(self, pid, addr, args):
        # LOG REQUIREMENT
        print(f"Node {NODE_ID} sends RPC RequestVote to Node {pid}")
        try:
            channel = grpc.insecure_channel(addr)
            stub = raft_pb2_grpc.RaftServiceStub(channel)
            resp = stub.RequestVote(args, timeout=0.5)
            
            with self.lock:
                if resp.term > self.term:
                    self._become_follower(resp.term)
                    return
                if self.state == "CANDIDATE" and resp.vote_granted:
                    self.votes_received += 1
                    # Majority Check
                    if self.votes_received > (len(PEERS) + 1) / 2:
                        self._become_leader()
        except: pass

    def _become_leader(self):
        if self.state != "LEADER":
            print(f"Node {NODE_ID} won election! Becoming LEADER.")
            self.state = "LEADER"
            self.leader_id = NODE_ID
            self._send_heartbeats()

    def _become_follower(self, term):
        self.state = "FOLLOWER"
        self.term = term
        self.voted_for = None
        self.last_heartbeat = time.time()

    # =========================================================
    #  RAFT CORE: LOG REPLICATION & HEARTBEAT
    # =========================================================
    def _send_heartbeats(self):
        # Requirement: "sends its entire log... on next heartbeat"
        entries = list(self.log)
        
        args = raft_pb2.AppendArgs(
            term=self.term, leader_id=NODE_ID,
            prev_log_index=-1, prev_log_term=0, # Simplified for "entire log"
            entries=entries, leader_commit=self.commit_index
        )
        
        for pid, addr in PEERS.items():
            threading.Thread(target=self._send_append, args=(pid, addr, args)).start()

    def _send_append(self, pid, addr, args):
        # LOG REQUIREMENT
        print(f"Node {NODE_ID} sends RPC AppendEntries to Node {pid}")
        try:
            channel = grpc.insecure_channel(addr)
            stub = raft_pb2_grpc.RaftServiceStub(channel)
            resp = stub.AppendEntries(args, timeout=0.5)
            
            with self.lock:
                if resp.term > self.term:
                    self._become_follower(resp.term)
                    return
                if self.state == "LEADER" and resp.success:
                    # Update Commit Index (Majority Check Simplification)
                    # If majority ACKed the log, we assume end of log is committed
                    if len(self.log) - 1 > self.commit_index:
                        self.commit_index = len(self.log) - 1
                        self._apply_logs()
        except: pass

    # =========================================================
    #  RAFT RPC HANDLERS (Called by Peers)
    # =========================================================
    def RequestVote(self, request, context):
        with self.lock:
            # LOG REQUIREMENT
            print(f"Node {NODE_ID} runs RPC RequestVote called by Node {request.candidate_id}")
            
            if request.term > self.term:
                self._become_follower(request.term)
            
            vote = False
            if request.term == self.term and (self.voted_for is None or self.voted_for == request.candidate_id):
                # Log Freshness Check
                last_idx = len(self.log) - 1
                last_term = self.log[last_idx].term if last_idx >= 0 else 0
                
                if (request.last_log_term > last_term) or \
                   (request.last_log_term == last_term and request.last_log_index >= last_idx):
                    vote = True
                    self.voted_for = request.candidate_id
                    self.last_heartbeat = time.time()
            
            return raft_pb2.VoteReply(term=self.term, vote_granted=vote)

    def AppendEntries(self, request, context):
        with self.lock:
            # LOG REQUIREMENT
            print(f"Node {NODE_ID} runs RPC AppendEntries called by Node {request.leader_id}")
            
            if request.term >= self.term:
                self.last_heartbeat = time.time()
                self.leader_id = request.leader_id
                if self.state != "FOLLOWER":
                    self._become_follower(request.term)
            
            if request.term < self.term:
                return raft_pb2.AppendReply(term=self.term, success=False)

            # Log Replication: Overwrite with Leader's log (Assignment Simplification)
            self.log = list(request.entries)
            
            # Commit Logic
            if request.leader_commit > self.commit_index:
                self.commit_index = min(request.leader_commit, len(self.log) - 1)
                self._apply_logs()

            return raft_pb2.AppendReply(term=self.term, success=True)

    def _apply_logs(self):
        """Executes committed commands against the State Machine (Music Queue)"""
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            print(f"Node {NODE_ID} EXECUTING: {entry.command}")
            
            if entry.command == "ADD":
                t = queue_pb2.Track()
                t.ParseFromString(entry.data)
                # Avoid duplicates in this simple list
                if not any(x.id == t.id for x in self.music_queue):
                    self.music_queue.append(t)
            elif entry.command == "REMOVE":
                tid = queue_pb2.TrackId()
                tid.ParseFromString(entry.data)
                self.music_queue = [x for x in self.music_queue if x.id != tid.id]

    # =========================================================
    #  QUEUE SERVICE (Called by Client)
    # =========================================================
    def _forward(self, request, method_name):
        """Helper to forward client requests to Leader"""
        if self.leader_id and self.leader_id in PEERS:
            # LOG REQUIREMENT
            print(f"Node {NODE_ID} sends RPC {method_name} (Forwarding) to Node {self.leader_id}")
            try:
                channel = grpc.insecure_channel(PEERS[self.leader_id])
                stub = queue_pb2_grpc.QueueServiceStub(channel)
                method = getattr(stub, method_name)
                return method(request)
            except grpc.RpcError as e:
                return queue_pb2.QueueResponse(message=f"Forwarding Failed: {e.code()}")
        else:
            return queue_pb2.QueueResponse(message="No Leader Elected Yet")

    def AddTrack(self, request, context):
        with self.lock:
            # LOG REQUIREMENT
            print(f"Node {NODE_ID} runs RPC AddTrack called by Client")
            
            if self.state == "LEADER":
                # Append to Log
                entry = raft_pb2.LogEntry(
                    term=self.term,
                    command="ADD",
                    data=request.SerializeToString()
                )
                self.log.append(entry)
                # Note: In strict Raft we wait for commit. Here we return optimistic success
                # so the client doesn't block forever waiting for the heartbeat interval.
                return queue_pb2.QueueResponse(message="Queued by Leader", queue=self.music_queue)
            else:
                return self._forward(request, "AddTrack")

    def RemoveTrack(self, request, context):
        with self.lock:
            print(f"Node {NODE_ID} runs RPC RemoveTrack called by Client")
            
            if self.state == "LEADER":
                entry = raft_pb2.LogEntry(
                    term=self.term,
                    command="REMOVE",
                    data=request.SerializeToString()
                )
                self.log.append(entry)
                return queue_pb2.QueueResponse(message="Queued by Leader", queue=self.music_queue)
            else:
                return self._forward(request, "RemoveTrack")

    def GetQueue(self, request, context):
        # Return local state (Read-Your-Writes eventual consistency)
        return queue_pb2.QueueList(queue=self.music_queue)

    # --- Stubs for other methods to ensure Interface Compliance ---
    def VoteTrack(self, r, c): return queue_pb2.QueueResponse()
    def GetMetadata(self, r, c): return queue_pb2.Track()
    def PlayNext(self, r, c): return queue_pb2.Track()
    def GetHistory(self, r, c): return queue_pb2.QueueList()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    # Register BOTH services on the same server
    queue_pb2_grpc.add_QueueServiceServicer_to_server(RaftServer(), server)
    raft_pb2_grpc.add_RaftServiceServicer_to_server(RaftServer(), server)
    
    server.add_insecure_port('[::]:50051')
    print(f"Raft Node {NODE_ID} started on port 50051")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()