package main

import (
    "context"
    "log"
    "math/rand"
    "net"
    "os"
    "strconv"
    "time"

    pb "auction/go-architecture/pb"
    grpc "google.golang.org/grpc"
)

type participantServer struct {
    pb.UnimplementedTwoPCParticipantServer
    nodeID          string
    prepared        map[string]*pb.TwoPCVoteRequest
    abortProbability float64
}

func newParticipant(nodeID string, abortProb float64) *participantServer {
    rand.Seed(time.Now().UnixNano())
    return &participantServer{nodeID: nodeID, prepared: make(map[string]*pb.TwoPCVoteRequest), abortProbability: abortProb}
}

func (p *participantServer) Vote(ctx context.Context, req *pb.TwoPCVoteRequest) (*pb.TwoPCVoteReply, error) {
    log.Printf("Phase voting of Node %s sends RPC Vote to Phase voting of Node %s", p.nodeID, p.nodeID)
    if req == nil || req.TxId == "" {
        return &pb.TwoPCVoteReply{TxId: req.TxId, CommitReady: false, Reason: "missing tx_id"}, nil
    }
    if rand.Float64() < p.abortProbability {
        return &pb.TwoPCVoteReply{TxId: req.TxId, CommitReady: false, Reason: "random abort simulation"}, nil
    }
    p.prepared[req.TxId] = req
    return &pb.TwoPCVoteReply{TxId: req.TxId, CommitReady: true}, nil
}

func (p *participantServer) Decide(ctx context.Context, d *pb.TwoPCDecision) (*pb.TwoPCDecision, error) {
    log.Printf("Phase decision of Node %s sends RPC Decide to Phase decision of Node %s", p.nodeID, p.nodeID)
    if d == nil || d.TxId == "" {
        return &pb.TwoPCDecision{TxId: d.TxId, GlobalCommit: false, Reason: "missing tx_id"}, nil
    }
    _, prepared := p.prepared[d.TxId]
    if d.GlobalCommit && prepared {
        delete(p.prepared, d.TxId)
        log.Printf("Node %s committed tx %s", p.nodeID, d.TxId)
    } else {
        delete(p.prepared, d.TxId)
        log.Printf("Node %s aborted tx %s reason=%s", p.nodeID, d.TxId, d.Reason)
    }
    return d, nil
}

func getenv(k, d string) string { v := os.Getenv(k); if v == "" { return d }; return v }

func main() {
    nodeID := getenv("NODE_ID", "participant")
    port := getenv("PARTICIPANT_PORT", "7101")
    abortProbEnv := getenv("ABORT_PROB", "0.0")
    abortProb, _ := strconv.ParseFloat(abortProbEnv, 64)
    lis, err := net.Listen("tcp", ":"+port)
    if err != nil { log.Fatalf("listen error: %v", err) }
    srv := grpc.NewServer()
    pb.RegisterTwoPCParticipantServer(srv, newParticipant(nodeID, abortProb))
    log.Printf("2PC participant Node %s listening on %s abort_prob=%.2f", nodeID, port, abortProb)
    if err := srv.Serve(lis); err != nil { log.Fatalf("serve error: %v", err) }
}
