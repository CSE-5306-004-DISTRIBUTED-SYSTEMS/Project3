package main

import (
	"context"
	"log"
	"net"
	"os"
	"sync"

	pb "auction/go-architecture/pb"
	grpc "google.golang.org/grpc"
)

type updateService struct {
	pb.UnimplementedUpdateBroadcasterServer
	mu     sync.Mutex
	events []*pb.HistoryEvent
}

func (u *updateService) Publish(ctx context.Context, event *pb.HistoryEvent) (*pb.AuctionResponse, error) {
	if event == nil {
		return &pb.AuctionResponse{Ok: false, Message: "missing event"}, nil
	}
	u.mu.Lock()
	defer u.mu.Unlock()
	copy := *event
	u.events = append(u.events, &copy)
	return &pb.AuctionResponse{Ok: true}, nil
}

func (u *updateService) List(ctx context.Context, _ *pb.Empty) (*pb.AuctionResponse, error) {
	u.mu.Lock()
	defer u.mu.Unlock()
	out := make([]*pb.HistoryEvent, len(u.events))
	for i, ev := range u.events {
		copy := *ev
		out[i] = &copy
	}
	return &pb.AuctionResponse{Ok: true, History: out}, nil
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	port := getenv("UPDATES_PORT", "7004")
	lis, err := net.Listen("tcp", ":"+port)
	if err != nil {
		log.Fatalf("listen error: %v", err)
	}
	srv := grpc.NewServer()
	pb.RegisterUpdateBroadcasterServer(srv, &updateService{})
	log.Printf("update service listening on %s", port)
	if err := srv.Serve(lis); err != nil {
		log.Fatalf("serve error: %v", err)
	}
}
