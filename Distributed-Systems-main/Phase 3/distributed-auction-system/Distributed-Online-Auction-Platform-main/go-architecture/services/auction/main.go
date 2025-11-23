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

type catalogService struct {
	pb.UnimplementedAuctionCatalogServer
	mu    sync.Mutex
	items map[string]*pb.Auction
}

func newCatalog() *catalogService {
	return &catalogService{items: make(map[string]*pb.Auction)}
}

func (s *catalogService) Execute(ctx context.Context, cmd *pb.AuctionCommand) (*pb.AuctionResponse, error) {
	switch cmd.Command {
	case "create":
		return s.create(cmd.Auction)
	case "get":
		return s.get(cmd.Auction)
	case "update_bid":
		return s.updateBid(cmd.Auction, cmd.BidAmount, cmd.Bidder)
	case "close":
		return s.closeAuction(cmd.Auction)
	case "list":
		return s.list()
	default:
		return &pb.AuctionResponse{Ok: false, Message: "unsupported command"}, nil
	}
}

func (s *catalogService) create(item *pb.Auction) (*pb.AuctionResponse, error) {
	if item == nil {
		return &pb.AuctionResponse{Ok: false, Message: "missing auction"}, nil
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	copied := cloneAuction(item)
	s.items[item.Id] = copied
	return &pb.AuctionResponse{Ok: true, Auction: cloneAuction(copied)}, nil
}

func (s *catalogService) get(item *pb.Auction) (*pb.AuctionResponse, error) {
	if item == nil {
		return &pb.AuctionResponse{Ok: false, Message: "missing id"}, nil
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	found, ok := s.items[item.Id]
	if !ok {
		return &pb.AuctionResponse{Ok: false, Message: "auction not found"}, nil
	}
	expireIfNeeded(found)
	return &pb.AuctionResponse{Ok: true, Auction: cloneAuction(found)}, nil
}

func (s *catalogService) updateBid(item *pb.Auction, amount float64, bidder string) (*pb.AuctionResponse, error) {
	if item == nil {
		return &pb.AuctionResponse{Ok: false, Message: "missing id"}, nil
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	existing, ok := s.items[item.Id]
	if !ok {
		return &pb.AuctionResponse{Ok: false, Message: "auction not found"}, nil
	}
	if expireIfNeeded(existing) || existing.Status != "OPEN" {
		return &pb.AuctionResponse{Ok: false, Message: "auction is not open"}, nil
	}
	existing.CurrentBid = amount
	existing.HighestBidder = bidder
	return &pb.AuctionResponse{Ok: true, Auction: cloneAuction(existing)}, nil
}

func (s *catalogService) closeAuction(item *pb.Auction) (*pb.AuctionResponse, error) {
	if item == nil {
		return &pb.AuctionResponse{Ok: false, Message: "missing id"}, nil
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	existing, ok := s.items[item.Id]
	if !ok {
		return &pb.AuctionResponse{Ok: false, Message: "auction not found"}, nil
	}
	expireIfNeeded(existing)
	existing.Status = "CLOSED"
	existing.ClosingTime = time.Now().Unix()
	return &pb.AuctionResponse{Ok: true, Auction: cloneAuction(existing)}, nil
}

func (s *catalogService) list() (*pb.AuctionResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	out := make([]*pb.Auction, 0, len(s.items))
	for _, item := range s.items {
		expireIfNeeded(item)
		out = append(out, cloneAuction(item))
	}
	return &pb.AuctionResponse{Ok: true, Auctions: out}, nil
}

func expireIfNeeded(item *pb.Auction) bool {
	if item == nil {
		return false
	}
	if item.Status != "OPEN" {
		return false
	}
	if item.ClosingTime == 0 {
		return false
	}
	if time.Now().Unix() >= item.ClosingTime {
		item.Status = "CLOSED"
		return true
	}
	return false
}

func cloneAuction(in *pb.Auction) *pb.Auction {
	if in == nil {
		return nil
	}
	copy := *in
	return &copy
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	port := getenv("CATALOG_PORT", "7001")
	lis, err := net.Listen("tcp", ":"+port)
	if err != nil {
		log.Fatalf("listen error: %v", err)
	}
	srv := grpc.NewServer()
	pb.RegisterAuctionCatalogServer(srv, newCatalog())
	log.Printf("auction catalog listening on %s", port)
	if err := srv.Serve(lis); err != nil {
		log.Fatalf("serve error: %v", err)
	}
}
