package main

import (
    "context"
    "log"
    "net"
    "os"
    "strings"

    pb "auction/go-architecture/pb"
    grpc "google.golang.org/grpc"
)

// coordinatorServer implements TwoPCCoordinator.
type coordinatorServer struct {
    pb.UnimplementedTwoPCCoordinatorServer
    nodeID       string
    participants map[string]pb.TwoPCParticipantClient
}

func newCoordinator(nodeID string) *coordinatorServer {
    return &coordinatorServer{nodeID: nodeID, participants: make(map[string]pb.TwoPCParticipantClient)}
}

func (c *coordinatorServer) initParticipants(csv string) {
    for _, addr := range strings.Split(csv, ",") {
        addr = strings.TrimSpace(addr)
        if addr == "" { continue }
        conn, err := grpc.Dial(addr) // custom grpc stub ignores options
        if err != nil {
            log.Printf("dial error %s: %v", addr, err)
            continue
        }
        c.participants[addr] = pb.NewTwoPCParticipantClient(conn)
    }
}

// StartVoting server-side entry for coordinator (vote + decision phases).
func (c *coordinatorServer) StartVoting(ctx context.Context, req *pb.TwoPCVoteRequest) (*pb.TwoPCDecision, error) {
    log.Printf("Phase voting of Node %s sends RPC StartVoting to Phase voting of Node %s", c.nodeID, c.nodeID)
    if req == nil || req.TxId == "" {
        return &pb.TwoPCDecision{TxId: req.TxId, GlobalCommit: false, Reason: "missing tx_id"}, nil
    }
    allCommit := true
    for addr, client := range c.participants {
        log.Printf("Phase voting of Node %s sends RPC Vote to Phase voting of Node %s", c.nodeID, addr)
        reply, err := client.Vote(ctx, req)
        if err != nil {
            allCommit = false
            log.Printf("vote error %s: %v", addr, err)
            continue
        }
        if !reply.CommitReady {
            allCommit = false
            log.Printf("participant %s aborts tx %s reason=%s", addr, req.TxId, reply.Reason)
        }
    }
    decision := &pb.TwoPCDecision{TxId: req.TxId, GlobalCommit: allCommit}
    if !allCommit { decision.Reason = "abort triggered by participant" }
    for addr, client := range c.participants {
        log.Printf("Phase decision of Node %s sends RPC Decide to Phase decision of Node %s", c.nodeID, addr)
        _, err := client.Decide(ctx, decision)
        if err != nil {
            log.Printf("decision error %s: %v", addr, err)
        }
    }
    return decision, nil
}

func getenv(key, def string) string { v := os.Getenv(key); if v == "" { return def }; return v }

func main() {
    nodeID := getenv("NODE_ID", "coord1")
    port := getenv("COORDINATOR_PORT", "7100")
    participantAddrs := getenv("PARTICIPANT_ADDRS", "2pc_participant1:7101,2pc_participant2:7102,2pc_participant3:7103,2pc_participant4:7104")
    lis, err := net.Listen("tcp", ":"+port)
    if err != nil { log.Fatalf("listen error: %v", err) }
    srv := grpc.NewServer()
    coord := newCoordinator(nodeID)
    coord.initParticipants(participantAddrs)
    pb.RegisterTwoPCCoordinatorServer(srv, coord)
    log.Printf("2PC coordinator Node %s listening on %s participants=%s", nodeID, port, participantAddrs)
    if err := srv.Serve(lis); err != nil { log.Fatalf("serve error: %v", err) }
}
