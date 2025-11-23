package main

import (
	"context"
	"log"
	"net"
	"os"
	"sync"
	"time"

	pb "auction/go-architecture/pb"
	grpc "google.golang.org/grpc"
)

type historyService struct {
	pb.UnimplementedHistoryRecorderServer
	mu     sync.Mutex
	events []*pb.HistoryEvent
}

func (h *historyService) Execute(ctx context.Context, cmd *pb.AuctionCommand) (*pb.AuctionResponse, error) {
	if cmd.Command != "record" {
		return &pb.AuctionResponse{Ok: false, Message: "unsupported command"}, nil
	}
	if cmd.Auction == nil {
		return &pb.AuctionResponse{Ok: false, Message: "missing auction"}, nil
	}
	event := &pb.HistoryEvent{
		AuctionId: cmd.Auction.Id,
		EventType: cmd.Bidder,
		Payload:   cmd.Auction.Name,
		Timestamp: time.Now().Unix(),
	}
	h.mu.Lock()
	defer h.mu.Unlock()
	h.events = append(h.events, event)
	return &pb.AuctionResponse{Ok: true}, nil
}

func (h *historyService) List(ctx context.Context, _ *pb.Empty) (*pb.AuctionResponse, error) {
	h.mu.Lock()
	defer h.mu.Unlock()
	copyEvents := make([]*pb.HistoryEvent, len(h.events))
	for i, ev := range h.events {
		e := *ev
		copyEvents[i] = &e
	}
	return &pb.AuctionResponse{Ok: true, History: copyEvents}, nil
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	port := getenv("HISTORY_PORT", "7003")
	lis, err := net.Listen("tcp", ":"+port)
	if err != nil {
		log.Fatalf("listen error: %v", err)
	}
	srv := grpc.NewServer()
	pb.RegisterHistoryRecorderServer(srv, &historyService{})
	log.Printf("history service listening on %s", port)
	if err := srv.Serve(lis); err != nil {
		log.Fatalf("serve error: %v", err)
	}
}
