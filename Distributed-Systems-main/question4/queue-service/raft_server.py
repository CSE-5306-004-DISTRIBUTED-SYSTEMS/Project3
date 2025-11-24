
import os
import time
import random
import threading
import logging
from concurrent import futures

import grpc

# generated protobuf modules - ensure these are generated from your .proto files
import raft_pb2
import raft_pb2_grpc
import queue_pb2
import queue_pb2_grpc

# -------------------------
# Config - tune as needed
# -------------------------
NODE_ID = int(os.environ.get("NODE_ID", "1"))
PORT = int(os.environ.get("PORT", "50051"))
PEERS_MAP = os.environ.get("PEERS", "")  # e.g. "2=raft-node2:50051,3=raft-node3:50051"
PEERS = {}
if PEERS_MAP:
    for p in PEERS_MAP.split(","):
        if "=" in p:
            pid, addr = p.split("=")
            pid = int(pid.strip())
            addr = addr.strip()
            if pid != NODE_ID:
                PEERS[pid] = addr

# Timing
HEARTBEAT_INTERVAL = float(os.environ.get("HEARTBEAT_INTERVAL", 0.3))
ELECTION_TIMEOUT_MIN = float(os.environ.get("ELECTION_TIMEOUT_MIN", 1.5))
ELECTION_TIMEOUT_MAX = float(os.environ.get("ELECTION_TIMEOUT_MAX", 3.0))
RPC_TIMEOUT = float(os.environ.get("RPC_TIMEOUT", 1.0))
CLIENT_APPLY_TIMEOUT = float(os.environ.get("CLIENT_APPLY_TIMEOUT", 5.0))

# Logging
logging.basicConfig(format=f"[Node {NODE_ID}] %(asctime)s %(levelname)s: %(message)s", level=logging.INFO)
logger = logging.getLogger()

# -------------------------
# Raft Server
# -------------------------
class RaftServer(queue_pb2_grpc.QueueServiceServicer, raft_pb2_grpc.RaftServiceServicer):
    def __init__(self):
        # concurrency
        self.lock = threading.RLock()

        # persistent state (in-memory; persist to disk for durability)
        self.current_term = 0
        self.voted_for = None
        self.log = []  # list of raft_pb2.LogEntry

        # volatile state
        self.commit_index = -1
        self.last_applied = -1
        self.state = "FOLLOWER"  # FOLLOWER, CANDIDATE, LEADER
        self.leader_id = None

        # election / heartbeat
        self.last_heartbeat = time.time()
        self._reset_election_deadline()

        # leader-only state
        self.next_index = {}   # peer_id -> next index to send
        self.match_index = {}  # peer_id -> highest replicated index

        # application state
        self.music_queue = []  # list of queue_pb2.Track

        # channel reuse
        self.peer_channels = {}  # pid -> grpc.Channel
        self.peer_raft_stubs = {}  # pid -> raft_pb2_grpc.RaftServiceStub
        self.peer_queue_stubs = {}  # pid -> queue_pb2_grpc.QueueServiceStub

        # commit condition for clients waiting for their entries to be committed
        self.commit_cond = threading.Condition(self.lock)

        # vote tracking for elections
        self.votes_received = 0

        # background control
        self._stop = threading.Event()
        threading.Thread(target=self._timer_loop, daemon=True).start()
        logger.info("RaftServer initialized")

    # -------------------------
    # Helpers
    # -------------------------
    def _reset_election_deadline(self):
        self.election_deadline = time.time() + random.uniform(ELECTION_TIMEOUT_MIN, ELECTION_TIMEOUT_MAX)

    def _total_nodes(self):
        return len(PEERS) + 1

    def _quorum_count(self):
        total = self._total_nodes()
        return total // 2 + 1

    def _get_or_create_peer_channel(self, pid, addr):
        ch = self.peer_channels.get(pid)
        if ch is None:
            ch = grpc.insecure_channel(addr)
            self.peer_channels[pid] = ch
            self.peer_raft_stubs[pid] = raft_pb2_grpc.RaftServiceStub(ch)
            self.peer_queue_stubs[pid] = queue_pb2_grpc.QueueServiceStub(ch)
        return ch

    # -------------------------
    # Timer loop
    # -------------------------
    def _timer_loop(self):
        while not self._stop.is_set():
            now = time.time()
            with self.lock:
                if self.state == "LEADER":
                    if now - self.last_heartbeat >= HEARTBEAT_INTERVAL:
                        self._send_heartbeats()
                        self.last_heartbeat = now
                else:
                    if now >= self.election_deadline:
                        logger.info("Election timeout -> start election")
                        self._start_election()
            time.sleep(0.05)

    # -------------------------
    # Elections
    # -------------------------
    def _start_election(self):
        # caller holds lock
        self.state = "CANDIDATE"
        self.current_term += 1
        self.voted_for = NODE_ID
        self.votes_received = 1
        self._reset_election_deadline()
        self.last_heartbeat = time.time()
        logger.info(f"Became CANDIDATE for term {self.current_term}")

        last_index = len(self.log) - 1
        last_term = self.log[last_index].term if last_index >= 0 else 0
        args = raft_pb2.VoteArgs(term=self.current_term, candidate_id=NODE_ID,
                                 last_log_index=last_index, last_log_term=last_term)

        for pid, addr in PEERS.items():
            threading.Thread(target=self._send_request_vote, args=(pid, addr, args), daemon=True).start()

    def _send_request_vote(self, pid, addr, args):
        try:
            self._get_or_create_peer_channel(pid, addr)
            stub = self.peer_raft_stubs[pid]
            resp = stub.RequestVote(args, timeout=RPC_TIMEOUT)
            with self.lock:
                if resp.term > self.current_term:
                    logger.info(f"Observed higher term {resp.term} from {pid}; becoming follower")
                    self._become_follower(resp.term, leader_id=None)
                    return
                if self.state != "CANDIDATE" or args.term != self.current_term:
                    return
                if resp.vote_granted:
                    self.votes_received += 1
                    logger.debug(f"Vote granted by {pid}; votes={self.votes_received}")
                    if self.votes_received >= self._quorum_count():
                        self._become_leader()
        except grpc.RpcError as e:
            logger.warning(f"RequestVote RPC to {pid} failed: {e}")
        except Exception as e:
            logger.exception("Error in _send_request_vote: %s", e)

    # -------------------------
    # Leader transition & AppendEntries sending
    # -------------------------
    def _become_leader(self):
        if self.state == "LEADER":
            return
        self.state = "LEADER"
        self.leader_id = NODE_ID
        logger.info(f"Won election and became LEADER for term {self.current_term}")
        # initialize next_index/match_index
        nexti = len(self.log)
        for pid in PEERS:
            self.next_index[pid] = nexti
            self.match_index[pid] = -1
        # leader's own indices
        self.match_index[NODE_ID] = len(self.log) - 1
        self.next_index[NODE_ID] = len(self.log)
        # send initial heartbeats
        self._send_heartbeats()

    def _become_follower(self, term, leader_id=None):
        self.state = "FOLLOWER"
        self.current_term = term
        self.voted_for = None
        self.leader_id = leader_id
        self._reset_election_deadline()
        self.last_heartbeat = time.time()
        logger.info(f"Transition to FOLLOWER term={self.current_term}, leader={self.leader_id}")

    def _send_heartbeats(self):
        # Send AppendEntries tailored to each follower
        for pid, addr in PEERS.items():
            nxt = self.next_index.get(pid, len(self.log))
            prev_idx = nxt - 1
            prev_term = self.log[prev_idx].term if (0 <= prev_idx < len(self.log)) else 0
            entries = self.log[nxt:]  # empty on heartbeat
            args = raft_pb2.AppendArgs(
                term=self.current_term,
                leader_id=NODE_ID,
                prev_log_index=prev_idx,
                prev_log_term=prev_term,
                entries=entries,
                leader_commit=self.commit_index
            )
            threading.Thread(target=self._send_append_entries, args=(pid, addr, args), daemon=True).start()

    def _send_append_entries(self, pid, addr, args):
        try:
            self._get_or_create_peer_channel(pid, addr)
            stub = self.peer_raft_stubs[pid]
            resp = stub.AppendEntries(args, timeout=RPC_TIMEOUT)
            with self.lock:
                if resp.term > self.current_term:
                    logger.info(f"Peer {pid} has higher term {resp.term}; stepping down")
                    self._become_follower(resp.term, leader_id=None)
                    return
                if resp.success:
                    replicated_up_to = args.prev_log_index + len(args.entries)
                    self.match_index[pid] = replicated_up_to
                    self.next_index[pid] = replicated_up_to + 1
                    logger.debug(f"AppendEntries success from {pid}: match_index={self.match_index[pid]}")
                    # Attempt to advance commit index
                    self._advance_commit_index()
                else:
                    # simple fallback: decrement next_index and try later
                    old_next = self.next_index.get(pid, len(self.log))
                    self.next_index[pid] = max(0, old_next - 1)
                    logger.debug(f"AppendEntries failed for {pid}; next_index {old_next}->{self.next_index[pid]}")
        except grpc.RpcError as e:
            logger.warning(f"AppendEntries RPC to {pid} failed: {e}")
        except Exception as e:
            logger.exception("Error in _send_append_entries: %s", e)

    def _advance_commit_index(self):
        # Caller holds lock
        last_index = len(self.log) - 1
        for N in range(self.commit_index + 1, last_index + 1):
            # safe commit rule: only commit entries from current term by leader
            if self.log[N].term != self.current_term:
                continue
            # count nodes with match_index >= N (leader included)
            count = 1
            for pid in PEERS:
                if self.match_index.get(pid, -1) >= N:
                    count += 1
            if count >= self._quorum_count():
                self.commit_index = N
                logger.info(f"Advanced commit_index -> {self.commit_index}")
                # notify waiters
                self.commit_cond.notify_all()
            # continue checking higher N

        # apply logs after possibly advancing
        self._apply_logs_locked()

    # -------------------------
    # RPC handlers - Raft
    # -------------------------
    def RequestVote(self, request, context):
        with self.lock:
            logger.info(f"RequestVote from {request.candidate_id} (term {request.term})")
            if request.term > self.current_term:
                self._become_follower(request.term, leader_id=None)

            vote_granted = False
            if request.term == self.current_term:
                if self.voted_for is None or self.voted_for == request.candidate_id:
                    last_idx = len(self.log) - 1
                    last_term = self.log[last_idx].term if last_idx >= 0 else 0
                    # candidate up-to-date check
                    if (request.last_log_term > last_term) or (request.last_log_term == last_term and request.last_log_index >= last_idx):
                        vote_granted = True
                        self.voted_for = request.candidate_id
                        self._reset_election_deadline()
                        logger.info(f"Voted for {request.candidate_id}")
            return raft_pb2.VoteReply(term=self.current_term, vote_granted=vote_granted)

    def AppendEntries(self, request, context):
        with self.lock:
            logger.debug(f"AppendEntries from leader {request.leader_id} (term {request.term})")
            if request.term < self.current_term:
                return raft_pb2.AppendReply(term=self.current_term, success=False)

            if request.term > self.current_term:
                self._become_follower(request.term, leader_id=request.leader_id)
            else:
                # same term -> update leader and heartbeat
                self.leader_id = request.leader_id
                self.last_heartbeat = time.time()
                self._reset_election_deadline()

            # consistency check: prev_log must match
            if request.prev_log_index >= 0:
                if request.prev_log_index >= len(self.log):
                    return raft_pb2.AppendReply(term=self.current_term, success=False)
                if self.log[request.prev_log_index].term != request.prev_log_term:
                    return raft_pb2.AppendReply(term=self.current_term, success=False)

            # append entries, resolving conflicts by truncation
            insert_idx = request.prev_log_index + 1
            for entry in request.entries:
                if insert_idx < len(self.log):
                    if self.log[insert_idx].term != entry.term:
                        # conflict -> truncate and append the rest
                        self.log = self.log[:insert_idx]
                        self.log.append(entry)
                    # else already have same entry -> do nothing
                else:
                    self.log.append(entry)
                insert_idx += 1

            # update commit index
            if request.leader_commit > self.commit_index:
                self.commit_index = min(request.leader_commit, len(self.log) - 1)
                logger.debug(f"Updated commit_index to {self.commit_index}")
                self._apply_logs_locked()

            return raft_pb2.AppendReply(term=self.current_term, success=True)

    # -------------------------
    # Apply logs to state machine
    # -------------------------
    def _apply_logs_locked(self):
        # lock must be held by caller
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            logger.info(f"Applying log[{self.last_applied}] cmd={entry.command}")
            try:
                if entry.command == "ADD":
                    t = queue_pb2.Track()
                    t.ParseFromString(entry.data)
                    if not any(x.id == t.id for x in self.music_queue):
                        self.music_queue.append(t)
                elif entry.command == "REMOVE":
                    tid = queue_pb2.TrackId()
                    tid.ParseFromString(entry.data)
                    self.music_queue = [x for x in self.music_queue if x.id != tid.id]
                else:
                    logger.warning(f"Unknown command in log: {entry.command}")
            except Exception as e:
                logger.exception("Failed to apply log entry: %s", e)

    def _apply_logs(self):
        with self.lock:
            self._apply_logs_locked()

    # -------------------------
    # Client-facing Queue RPCs
    # -------------------------
    def _forward_to_leader(self, request, method_name):
        target = self.leader_id
        if target is None:
            return queue_pb2.QueueResponse(message="No leader elected")
        if target == NODE_ID:
            return queue_pb2.QueueResponse(message="Leader state mismatch")
        if target not in PEERS:
            return queue_pb2.QueueResponse(message=f"Unknown leader id {target}")
        try:
            self._get_or_create_peer_channel(target, PEERS[target])
            qstub = self.peer_queue_stubs[target]
            method = getattr(qstub, method_name)
            return method(request, timeout=RPC_TIMEOUT)
        except grpc.RpcError as e:
            logger.warning("Forwarding RPC failed: %s", e)
            return queue_pb2.QueueResponse(message=f"Forwarding failed: {e}")
        except Exception as e:
            logger.exception("Forwarding error: %s", e)
            return queue_pb2.QueueResponse(message="Forwarding error")


    def AddTrack(self, request, context):
        # log RPC call
        client_id = "unknown"
        for key, value in context.invocation_metadata():
            if key == "node-id":
                client_id = value
        logger.info(f"Node {NODE_ID} runs RPC AddTrack called by Node {client_id}")

        with self.lock:
            if self.state != "LEADER":
                return self._forward_to_leader(request, "AddTrack")

            entry = raft_pb2.LogEntry(term=self.current_term, command="ADD", data=request.SerializeToString())
            index = len(self.log)
            self.log.append(entry)
            logger.info(f"Leader appended log[{index}]")

            # leader bookkeeping
            self.match_index[NODE_ID] = index
            self.next_index[NODE_ID] = index + 1

            # request replication
            self._send_heartbeats()

            # wait for commit
            start = time.time()
            with self.commit_cond:
                while self.commit_index < index:
                    remaining = CLIENT_APPLY_TIMEOUT - (time.time() - start)
                    if remaining <= 0:
                        logger.warning("AddTrack: commit timeout")
                        return queue_pb2.QueueResponse(message="Queued but not committed (timeout)", queue=self.music_queue)
                    self.commit_cond.wait(timeout=remaining)
            logger.info("AddTrack committed")
            return queue_pb2.QueueResponse(message="Queued", queue=self.music_queue)

    # def AddTrack(self, request, context):
    #     with self.lock:
    #         logger.info("AddTrack called")
    #         if self.state != "LEADER":
    #             return self._forward_to_leader(request, "AddTrack")

    #         entry = raft_pb2.LogEntry(term=self.current_term, command="ADD", data=request.SerializeToString())
    #         index = len(self.log)
    #         self.log.append(entry)
    #         logger.info(f"Leader appended log[{index}]")

    #         # leader bookkeeping
    #         self.match_index[NODE_ID] = index
    #         self.next_index[NODE_ID] = index + 1

    #         # request replication
    #         self._send_heartbeats()

    #         # wait for commit
    #         start = time.time()
    #         with self.commit_cond:
    #             while self.commit_index < index:
    #                 remaining = CLIENT_APPLY_TIMEOUT - (time.time() - start)
    #                 if remaining <= 0:
    #                     logger.warning("AddTrack: commit timeout")
    #                     return queue_pb2.QueueResponse(message="Queued but not committed (timeout)", queue=self.music_queue)
    #                 self.commit_cond.wait(timeout=remaining)
    #         logger.info("AddTrack committed")
    #         return queue_pb2.QueueResponse(message="Queued", queue=self.music_queue)

    def RemoveTrack(self, request, context):
        client_id = "unknown"
        for key, value in context.invocation_metadata():
            if key == "node-id":
                client_id = value
        logger.info(f"Node {NODE_ID} runs RPC RemoveTrack called by Node {client_id}")

        with self.lock:
            if self.state != "LEADER":
                return self._forward_to_leader(request, "RemoveTrack")

            entry = raft_pb2.LogEntry(term=self.current_term, command="REMOVE", data=request.SerializeToString())
            index = len(self.log)
            self.log.append(entry)
            logger.info(f"Leader appended REMOVE log[{index}]")

            self.match_index[NODE_ID] = index
            self.next_index[NODE_ID] = index + 1
            self._send_heartbeats()

            start = time.time()
            with self.commit_cond:
                while self.commit_index < index:
                    remaining = CLIENT_APPLY_TIMEOUT - (time.time() - start)
                    if remaining <= 0:
                        logger.warning("RemoveTrack: commit timeout")
                        return queue_pb2.QueueResponse(message="Queued but not committed (timeout)", queue=self.music_queue)
                    self.commit_cond.wait(timeout=remaining)
            logger.info("RemoveTrack committed")
            return queue_pb2.QueueResponse(message="Removed", queue=self.music_queue)

    # def RemoveTrack(self, request, context):
    #     with self.lock:
    #         logger.info("RemoveTrack called")
    #         if self.state != "LEADER":
    #             return self._forward_to_leader(request, "RemoveTrack")

    #         entry = raft_pb2.LogEntry(term=self.current_term, command="REMOVE", data=request.SerializeToString())
    #         index = len(self.log)
    #         self.log.append(entry)
    #         logger.info(f"Leader appended REMOVE log[{index}]")

    #         self.match_index[NODE_ID] = index
    #         self.next_index[NODE_ID] = index + 1
    #         self._send_heartbeats()

    #         start = time.time()
    #         with self.commit_cond:
    #             while self.commit_index < index:
    #                 remaining = CLIENT_APPLY_TIMEOUT - (time.time() - start)
    #                 if remaining <= 0:
    #                     logger.warning("RemoveTrack: commit timeout")
    #                     return queue_pb2.QueueResponse(message="Queued but not committed (timeout)", queue=self.music_queue)
    #                 self.commit_cond.wait(timeout=remaining)
    #         logger.info("RemoveTrack committed")
    #         return queue_pb2.QueueResponse(message="Removed", queue=self.music_queue)

    def GetQueue(self, request, context):
        client_id = "unknown"
        for key, value in context.invocation_metadata():
            if key == "node-id":
                client_id = value
        logger.info(f"Node {NODE_ID} runs RPC GetQueue called by Node {client_id}")

        with self.lock:
            return queue_pb2.QueueList(queue=self.music_queue)

    # def GetQueue(self, request, context):
    #     with self.lock:
    #         return queue_pb2.QueueList(queue=self.music_queue)

    # Unused stubs - implement as needed
    def VoteTrack(self, request, context):
        return queue_pb2.QueueResponse()
    def GetMetadata(self, request, context):
        return queue_pb2.Track()
    def PlayNext(self, request, context):
        return queue_pb2.Track()
    def GetHistory(self, request, context):
        return queue_pb2.QueueList()

    def stop(self):
        self._stop.set()

# -------------------------
# Server bootstrap
# -------------------------
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=20))
    raft_server = RaftServer()
    queue_pb2_grpc.add_QueueServiceServicer_to_server(raft_server, server)
    raft_pb2_grpc.add_RaftServiceServicer_to_server(raft_server, server)
    bind = f"[::]:{PORT}"
    server.add_insecure_port(bind)
    logger.info(f"Starting gRPC server on {bind}")
    server.start()
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        raft_server.stop()
        server.stop(0)

if __name__ == "__main__":
    serve()
