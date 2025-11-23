package main

import (
	"context"
	"log"
	"net"
	"os"
	"strconv"
	"sync"

	pb "auction/go-architecture/pb"
	grpc "google.golang.org/grpc"
)

type notifierService struct {
	pb.UnimplementedWinnerNotifierServer
	mu            sync.Mutex
	notifications []string
}

func (n *notifierService) Execute(ctx context.Context, cmd *pb.AuctionCommand) (*pb.AuctionResponse, error) {
	if cmd.Command != "notify" {
		return &pb.AuctionResponse{Ok: false, Message: "unsupported command"}, nil
	}
	if cmd.Auction == nil {
		return &pb.AuctionResponse{Ok: false, Message: "missing auction"}, nil
	}
	message := "Winner: " + cmd.Auction.HighestBidder + " for $" + formatAmount(cmd.Auction.CurrentBid)
	n.mu.Lock()
	n.notifications = append(n.notifications, message)
	n.mu.Unlock()
	log.Printf("notification: %s", message)
	return &pb.AuctionResponse{Ok: true, Message: message}, nil
}

func formatAmount(v float64) string {
	return strconv.FormatFloat(v, 'f', 2, 64)
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	port := getenv("NOTIFIER_PORT", "7005")
	lis, err := net.Listen("tcp", ":"+port)
	if err != nil {
		log.Fatalf("listen error: %v", err)
	}
	srv := grpc.NewServer()
	pb.RegisterWinnerNotifierServer(srv, &notifierService{})
	log.Printf("notifier listening on %s", port)
	if err := srv.Serve(lis); err != nil {
		log.Fatalf("serve error: %v", err)
	}
}
