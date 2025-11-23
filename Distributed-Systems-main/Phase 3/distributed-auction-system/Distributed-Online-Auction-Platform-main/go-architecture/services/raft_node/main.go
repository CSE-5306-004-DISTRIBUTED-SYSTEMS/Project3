package main

import (
    "context"
    "encoding/json"
    "fmt"
    "log"
    "math/rand"
    "net"
    "net/http"
    "os"
    "strings"
    "sync"
    "time"

    pb "auction/go-architecture/pb"
    grpc "google.golang.org/grpc"
)

type role int
const (
    Follower role = iota
    Candidate
    Leader
)

type raftServer struct {
    pb.UnimplementedRaftNodeServer
    mu sync.Mutex
    id string
    peers []string                       // host:port addresses
    peerIDs []string                     // corresponding node IDs (n1, n2, etc)
    conns map[string]pb.RaftNodeClient   // addr -> client
    connsByID map[string]pb.RaftNodeClient // node ID -> client for forwarding
    currentTerm int64
    votedFor string
    state role
    electionReset time.Time
    stopCh chan struct{}
    // Q4 log replication state
    log []*pb.LogEntry
    commitIndex int64
    lastApplied int64
    ackCounts map[int64]int // leader-side ack counts per index
    leaderAddr string        // cached leader ID for forwarding
}

func newRaft(id string, peers []string) *raftServer {
    // Extract node IDs from peer addresses (e.g., raft_node1:7201 -> n1)
    peerIDs := make([]string, len(peers))
    for i, addr := range peers {
        // Extract node number from raft_nodeN:port
        parts := strings.Split(addr, ":")
        if len(parts) > 0 && strings.HasPrefix(parts[0], "raft_node") {
            nodeNum := strings.TrimPrefix(parts[0], "raft_node")
            peerIDs[i] = "n" + nodeNum
        }
    }
    
    rs := &raftServer{
        id: id, 
        peers: peers,
        peerIDs: peerIDs,
        conns: make(map[string]pb.RaftNodeClient), 
        connsByID: make(map[string]pb.RaftNodeClient),
        state: Follower, 
        electionReset: time.Now(), 
        stopCh: make(chan struct{}), 
        ackCounts: make(map[int64]int),
        commitIndex: -1,
        lastApplied: -1,
    }
    return rs
}

func (r *raftServer) dialPeers() {
    for i, addr := range r.peers {
        if addr == "" { continue }
        conn, err := grpc.Dial(addr)
        if err != nil { log.Printf("raft %s dial %s error: %v", r.id, addr, err); continue }
        client := pb.NewRaftNodeClient(conn)
        r.conns[addr] = client
        if i < len(r.peerIDs) && r.peerIDs[i] != "" {
            r.connsByID[r.peerIDs[i]] = client
        }
    }
}

// RequestVote RPC (server side)
func (r *raftServer) RequestVote(ctx context.Context, args *pb.RequestVoteArgs) (*pb.RequestVoteReply, error) {
    r.mu.Lock()
    defer r.mu.Unlock()
    log.Printf("Node %s runs RPC RequestVote called by Node %s", r.id, args.CandidateId)
    if args.Term < r.currentTerm {
        return &pb.RequestVoteReply{Term: r.currentTerm, VoteGranted: false}, nil
    }
    if args.Term > r.currentTerm {
        r.currentTerm = args.Term
        r.state = Follower
        r.votedFor = ""
    }
    if r.votedFor == "" || r.votedFor == args.CandidateId {
        r.votedFor = args.CandidateId
        r.electionReset = time.Now()
        return &pb.RequestVoteReply{Term: r.currentTerm, VoteGranted: true}, nil
    }
    return &pb.RequestVoteReply{Term: r.currentTerm, VoteGranted: false}, nil
}

// AppendEntries RPC (heartbeat only for Q3)
func (r *raftServer) AppendEntries(ctx context.Context, args *pb.AppendEntriesArgs) (*pb.AppendEntriesReply, error) {
    r.mu.Lock()
    defer r.mu.Unlock()
    log.Printf("Node %s runs RPC AppendEntries called by Node %s", r.id, args.LeaderId)
    if args.Term < r.currentTerm {
        return &pb.AppendEntriesReply{Term: r.currentTerm, Success: false, AppliedUpTo: r.lastApplied}, nil
    }
    if args.Term >= r.currentTerm {
        r.currentTerm = args.Term
        r.state = Follower
        r.votedFor = args.LeaderId
        r.leaderAddr = args.LeaderId // cache for forwarding
        r.electionReset = time.Now()
    }
    // Replace entire log snapshot (simplified spec)
    if len(args.Entries) > 0 {
        r.log = cloneLog(args.Entries)
    }
    // Apply up to commit index
    if args.CommitIndex > r.commitIndex {
        r.commitIndex = args.CommitIndex
        r.applyEntries()
    }
    return &pb.AppendEntriesReply{Term: r.currentTerm, Success: true, AppliedUpTo: r.lastApplied}, nil
}

func (r *raftServer) runBackground() {
    go r.runElectionTimer()
    go r.runHeartbeats()
}

func (r *raftServer) runElectionTimer() {
    for {
        select { case <-r.stopCh: return; default: }
        timeout := randomElectionTimeout()
        time.Sleep(timeout)
        r.mu.Lock()
        if r.state == Leader { r.mu.Unlock(); continue }
        if time.Since(r.electionReset) >= timeout {
            r.startElection()
        }
        r.mu.Unlock()
    }
}

func (r *raftServer) startElection() {
    r.state = Candidate
    r.currentTerm++
    r.votedFor = r.id
    r.leaderAddr = ""
    r.electionReset = time.Now()
    log.Printf("Node %s sends RPC RequestVote to Node (broadcast) term=%d", r.id, r.currentTerm)
    
    // Use channel and mutex for vote counting
    termAtStart := r.currentTerm
    voteCh := make(chan bool, len(r.peers))
    
    for _, addr := range r.peers {
        client := r.conns[addr]
        if client == nil { continue }
        go func(a string, c pb.RaftNodeClient, term int64) {
            args := &pb.RequestVoteArgs{CandidateId: r.id, Term: term}
            log.Printf("Node %s sends RPC RequestVote to Node %s", r.id, a)
            reply, err := c.RequestVote(context.Background(), args)
            if err != nil { 
                log.Printf("vote request error %s->%s: %v", r.id, a, err)
                voteCh <- false
                return 
            }
            r.mu.Lock()
            if r.state != Candidate || term != r.currentTerm { 
                r.mu.Unlock()
                voteCh <- false
                return 
            }
            if reply.Term > r.currentTerm { 
                r.currentTerm = reply.Term
                r.state = Follower
                r.votedFor = ""
                r.mu.Unlock()
                voteCh <- false
                return 
            }
            r.mu.Unlock()
            voteCh <- reply.VoteGranted
        }(addr, client, termAtStart)
    }
    
    // Count votes in main goroutine
    go func() {
        votes := 1 // self vote
        needed := (len(r.peers)+1)/2 + 1
        for i := 0; i < len(r.peers); i++ {
            if <-voteCh {
                votes++
                if votes >= needed {
                    r.mu.Lock()
                    if r.state == Candidate && r.currentTerm == termAtStart {
                        r.becomeLeader()
                    }
                    r.mu.Unlock()
                    return
                }
            }
        }
    }()
}

func (r *raftServer) becomeLeader() {
    if r.state == Leader { return }
    r.state = Leader
    r.leaderAddr = r.id
    log.Printf("Node %s becomes leader term=%d", r.id, r.currentTerm)
    // Initialize leader heartbeat with current log snapshot
    if r.log == nil { r.log = []*pb.LogEntry{} }
    // Reset ack counts for new term
    r.ackCounts = make(map[int64]int)
}

func (r *raftServer) runHeartbeats() {
    ticker := time.NewTicker(1 * time.Second)
    defer ticker.Stop()
    for {
        select { case <-r.stopCh: return; case <-ticker.C: }
        r.mu.Lock()
        if r.state == Leader {
            for _, addr := range r.peers {
                client := r.conns[addr]
                if client == nil { continue }
                go func(a string, c pb.RaftNodeClient, term int64, logSnapshot []*pb.LogEntry, commitIdx int64) {
                    log.Printf("Node %s sends RPC AppendEntries to Node %s", r.id, a)
                    // send full log + commit index snapshot
                    args := &pb.AppendEntriesArgs{LeaderId: r.id, Term: term, Entries: logSnapshot, CommitIndex: commitIdx}
                    reply, err := c.AppendEntries(context.Background(), args)
                    if err != nil { log.Printf("heartbeat error %s->%s: %v", r.id, a, err); return }
                    
                    r.mu.Lock()
                    defer r.mu.Unlock()
                    // Track acknowledgments for last log index if any
                    if reply.Success && len(logSnapshot) > 0 {
                        lastIdx := logSnapshot[len(logSnapshot)-1].Index
                        r.ackCounts[lastIdx]++
                        r.maybeCommit(lastIdx)
                    }
                }(addr, client, r.currentTerm, r.log, r.commitIndex)
            }
        }
        r.mu.Unlock()
    }
}

func randomElectionTimeout() time.Duration {
    // 1.5s - 3s
    base := 1500
    extra := rand.Intn(1500)
    return time.Duration(base+extra) * time.Millisecond
}

// ClientRequest: accept operation, append to leader log or forward
func (r *raftServer) ClientRequest(ctx context.Context, args *pb.ClientRequestArgs) (*pb.ClientRequestReply, error) {
    r.mu.Lock()
    if r.state != Leader {
        // Attempt forward to known leader
        leaderID := r.leaderAddr
        leaderClient := r.connsByID[leaderID]
        r.mu.Unlock()
        
        if leaderID == "" || leaderID == r.id || leaderClient == nil {
            return &pb.ClientRequestReply{Accepted: false, Message: fmt.Sprintf("no leader (current: %s)", leaderID)}, nil
        }
        
        log.Printf("Node %s sends RPC ClientRequest to Node %s (forward)", r.id, leaderID)
        reply, err := leaderClient.ClientRequest(context.Background(), args)
        if err != nil { 
            return &pb.ClientRequestReply{Accepted: false, Message: fmt.Sprintf("forward error: %v", err)}, nil 
        }
        return reply, nil
    }
    
    // Leader path: append to log
    idx := int64(len(r.log))
    entry := &pb.LogEntry{Operation: args.Operation, Term: r.currentTerm, Index: idx}
    r.log = append(r.log, entry)
    // Initialize ack count including leader itself
    r.ackCounts[idx] = 1
    committed := r.commitIndex
    r.mu.Unlock()
    
    log.Printf("Node %s queued operation '%s' at index %d", r.id, args.Operation, idx)
    return &pb.ClientRequestReply{Accepted: true, Message: "queued", Index: idx, CommittedIndex: committed}, nil
}



func (r *raftServer) maybeCommit(lastIdx int64) {
    if r.state != Leader { return }
    // Majority threshold (cluster size = peers + leader)
    clusterSize := len(r.peers) + 1
    majority := clusterSize/2 + 1
    count := r.ackCounts[lastIdx]
    if count >= majority && lastIdx > r.commitIndex {
        r.commitIndex = lastIdx
        r.applyEntries()
    }
}

func (r *raftServer) applyEntries() {
    // Apply all entries from lastApplied+1 up to commitIndex
    for r.lastApplied < r.commitIndex {
        nextIdx := r.lastApplied + 1
        // Find entry with matching index in log array
        var found *pb.LogEntry
        for _, e := range r.log {
            if e.Index == nextIdx {
                found = e
                break
            }
        }
        if found != nil {
            log.Printf("Node %s applies operation idx=%d op=%s", r.id, found.Index, found.Operation)
            r.lastApplied = nextIdx
        } else {
            // Entry not in log yet, stop applying
            break
        }
    }
}

func cloneLog(entries []*pb.LogEntry) []*pb.LogEntry {
    out := make([]*pb.LogEntry, len(entries))
    for i, e := range entries {
        out[i] = &pb.LogEntry{Operation: e.Operation, Term: e.Term, Index: e.Index}
    }
    return out
}

func getenv(k, d string) string { v := os.Getenv(k); if v == "" { return d }; return v }

func main() {
    rand.Seed(time.Now().UnixNano())
    id := getenv("RAFT_NODE_ID", "n1")
    port := getenv("RAFT_PORT", "7201")
    httpPort := os.Getenv("RAFT_HTTP_PORT")
    peersCSV := getenv("RAFT_PEERS", "")
    // peersCSV is host:port list excluding self
    var peers []string
    if peersCSV != "" { peers = strings.Split(peersCSV, ",") }
    srv := newRaft(id, peers)
    srv.dialPeers()
    lis, err := net.Listen("tcp", ":"+port)
    if err != nil { log.Fatalf("raft listen error: %v", err) }
    g := grpc.NewServer()
    pb.RegisterRaftNodeServer(g, srv)
    log.Printf("Raft node %s follower term=%d listening on %s peers=%v", id, srv.currentTerm, port, peers)
    srv.runBackground()
    // Optional HTTP shim for simple client testing (JSON over HTTP instead of gRPC tooling)
    if httpPort != "" {
        go func() {
            mux := http.NewServeMux()
            mux.HandleFunc("/client_request", func(w http.ResponseWriter, r *http.Request) {
                if r.Method != http.MethodPost { http.Error(w, "method not allowed", http.StatusMethodNotAllowed); return }
                var body struct { Operation string `json:"operation"` }
                if err := json.NewDecoder(r.Body).Decode(&body); err != nil { http.Error(w, "bad json", http.StatusBadRequest); return }
                reply, err := srv.ClientRequest(context.Background(), &pb.ClientRequestArgs{Operation: body.Operation})
                if err != nil { http.Error(w, "rpc error", http.StatusInternalServerError); return }
                _ = json.NewEncoder(w).Encode(map[string]any{"accepted": reply.Accepted, "message": reply.Message, "index": reply.Index, "committed_index": reply.CommittedIndex})
            })
            log.Printf("Raft node %s HTTP shim listening on %s", id, httpPort)
            if err := http.ListenAndServe(":"+httpPort, mux); err != nil { log.Printf("HTTP shim error: %v", err) }
        }()
    }
    if err := g.Serve(lis); err != nil { log.Fatalf("raft serve error: %v", err) }
}
