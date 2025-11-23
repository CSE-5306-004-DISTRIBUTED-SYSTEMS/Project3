package main

import (
	"context"
	"log"
	"net"
	"os"

	pb "auction/go-architecture/pb"
	grpc "google.golang.org/grpc"
)

type validatorService struct {
	pb.UnimplementedBidValidatorServer
}

func (s *validatorService) Execute(ctx context.Context, cmd *pb.AuctionCommand) (*pb.AuctionResponse, error) {
	if cmd.Command != "validate" {
		return &pb.AuctionResponse{Ok: false, Message: "unsupported command"}, nil
	}
	auction := cmd.Auction
	if auction == nil {
		return &pb.AuctionResponse{Ok: false, Message: "missing auction"}, nil
	}
	if cmd.BidAmount <= auction.CurrentBid {
		return &pb.AuctionResponse{Ok: false, Message: "bid must exceed current"}, nil
	}
	return &pb.AuctionResponse{Ok: true, Message: "bid accepted"}, nil
}

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func main() {
	port := getenv("VALIDATOR_PORT", "7002")
	lis, err := net.Listen("tcp", ":"+port)
	if err != nil {
		log.Fatalf("listen error: %v", err)
	}
	srv := grpc.NewServer()
	pb.RegisterBidValidatorServer(srv, &validatorService{})
	log.Printf("bid validator listening on %s", port)
	if err := srv.Serve(lis); err != nil {
		log.Fatalf("serve error: %v", err)
	}
}
