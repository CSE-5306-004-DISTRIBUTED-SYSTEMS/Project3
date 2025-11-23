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

type gatewayServer struct {
	pb.UnimplementedAuctionGatewayServer
	catalog   pb.AuctionCatalogClient
	validator pb.BidValidatorClient
	history   pb.HistoryRecorderClient
	updates   pb.UpdateBroadcasterClient
	notifier  pb.WinnerNotifierClient
}

func newGateway() *gatewayServer {
	rand.Seed(time.Now().UnixNano())
	return &gatewayServer{}
}

func dialClient(addr string) *grpc.ClientConn {
	conn, err := grpc.Dial(addr)
	if err != nil {
		log.Fatalf("failed to dial %s: %v", addr, err)
	}
	return conn
}

func (g *gatewayServer) initClients() {
	catalogAddr := getenv("CATALOG_ADDR", "catalog:7001")
	validatorAddr := getenv("VALIDATOR_ADDR", "validator:7002")
	historyAddr := getenv("HISTORY_ADDR", "history:7003")
	updatesAddr := getenv("UPDATES_ADDR", "updates:7004")
	notifierAddr := getenv("NOTIFIER_ADDR", "notifier:7005")

	g.catalog = pb.NewAuctionCatalogClient(dialClient(catalogAddr))
	g.validator = pb.NewBidValidatorClient(dialClient(validatorAddr))
	g.history = pb.NewHistoryRecorderClient(dialClient(historyAddr))
	g.updates = pb.NewUpdateBroadcasterClient(dialClient(updatesAddr))
	g.notifier = pb.NewWinnerNotifierClient(dialClient(notifierAddr))
}

func (g *gatewayServer) Execute(ctx context.Context, cmd *pb.AuctionCommand) (*pb.AuctionResponse, error) {
	switch cmd.Command {
	case "create":
		return g.handleCreate(ctx, cmd)
	case "place_bid":
		return g.handleBid(ctx, cmd)
	case "close":
		return g.handleClose(ctx, cmd)
	case "list":
		return g.handleList(ctx, cmd)
	default:
		return &pb.AuctionResponse{Ok: false, Message: "unknown command"}, nil
	}
}

func (g *gatewayServer) handleCreate(ctx context.Context, cmd *pb.AuctionCommand) (*pb.AuctionResponse, error) {
	if cmd.Auction == nil {
		return &pb.AuctionResponse{Ok: false, Message: "missing auction payload"}, nil
	}
	item := cmd.Auction
	if item.Name == "" {
		return &pb.AuctionResponse{Ok: false, Message: "name is required"}, nil
	}
	if item.StartingBid <= 0 {
		return &pb.AuctionResponse{Ok: false, Message: "starting bid must be positive"}, nil
	}
	if item.DurationSeconds <= 0 {
		item.DurationSeconds = 60
	}
	item.Id = generateID()
	item.CurrentBid = item.StartingBid
	item.Status = "OPEN"
	item.ClosingTime = time.Now().Add(time.Duration(item.DurationSeconds) * time.Second).Unix()

	res, err := g.catalog.Execute(ctx, &pb.AuctionCommand{Command: "create", Auction: item})
	if err != nil {
		return nil, err
	}
	g.recordHistory(ctx, item.Id, "auction_created", item.Name)
	g.publishUpdate(ctx, item.Id, "Auction created: "+item.Name)
	return res, nil
}

func (g *gatewayServer) handleBid(ctx context.Context, cmd *pb.AuctionCommand) (*pb.AuctionResponse, error) {
	if cmd.Auction == nil || cmd.Auction.Id == "" {
		return &pb.AuctionResponse{Ok: false, Message: "auction id required"}, nil
	}
	if cmd.BidAmount <= 0 {
		return &pb.AuctionResponse{Ok: false, Message: "bid must be positive"}, nil
	}
	auctionRes, err := g.catalog.Execute(ctx, &pb.AuctionCommand{Command: "get", Auction: &pb.Auction{Id: cmd.Auction.Id}})
	if err != nil {
		return nil, err
	}
	if !auctionRes.Ok || auctionRes.Auction == nil {
		return auctionRes, nil
	}
	current := auctionRes.Auction
	if current.Status != "OPEN" {
		return &pb.AuctionResponse{Ok: false, Message: "auction is not open"}, nil
	}
	validation, err := g.validator.Execute(ctx, &pb.AuctionCommand{Command: "validate", Auction: current, BidAmount: cmd.BidAmount, Bidder: cmd.Bidder})
	if err != nil {
		return nil, err
	}
	if !validation.Ok {
		return validation, nil
	}
	updateRes, err := g.catalog.Execute(ctx, &pb.AuctionCommand{Command: "update_bid", Auction: &pb.Auction{Id: current.Id}, BidAmount: cmd.BidAmount, Bidder: cmd.Bidder})
	if err != nil {
		return nil, err
	}
	if updateRes.Ok {
		g.recordHistory(ctx, current.Id, "bid_placed", cmd.Bidder+" bid $"+formatAmount(cmd.BidAmount))
		g.publishUpdate(ctx, current.Id, "New highest bid $"+formatAmount(cmd.BidAmount)+" by "+cmd.Bidder)
	}
	return updateRes, nil
}

func (g *gatewayServer) handleClose(ctx context.Context, cmd *pb.AuctionCommand) (*pb.AuctionResponse, error) {
	if cmd.Auction == nil || cmd.Auction.Id == "" {
		return &pb.AuctionResponse{Ok: false, Message: "auction id required"}, nil
	}
	res, err := g.catalog.Execute(ctx, &pb.AuctionCommand{Command: "close", Auction: &pb.Auction{Id: cmd.Auction.Id}})
	if err != nil {
		return nil, err
	}
	if res.Ok && res.Auction != nil {
		g.recordHistory(ctx, res.Auction.Id, "auction_closed", res.Auction.HighestBidder)
		if res.Auction.HighestBidder != "" {
			g.notifier.Execute(ctx, &pb.AuctionCommand{Command: "notify", Auction: res.Auction})
		}
		g.publishUpdate(ctx, res.Auction.Id, "Auction closed")
	}
	return res, nil
}

func (g *gatewayServer) handleList(ctx context.Context, cmd *pb.AuctionCommand) (*pb.AuctionResponse, error) {
	res, err := g.catalog.Execute(ctx, &pb.AuctionCommand{Command: "list"})
	if err != nil {
		return nil, err
	}
	return res, nil
}

func (g *gatewayServer) GetHistory(ctx context.Context, _ *pb.Empty) (*pb.AuctionResponse, error) {
	res, err := g.history.List(ctx, &pb.Empty{})
	if err != nil {
		return nil, err
	}
	updates, err := g.updates.List(ctx, &pb.Empty{})
	if err == nil && updates != nil {
		res.History = append(res.History, updates.History...)
	}
	return res, nil
}

func (g *gatewayServer) recordHistory(ctx context.Context, auctionID, eventType, payload string) {
	_, err := g.history.Execute(ctx, &pb.AuctionCommand{Command: "record", Auction: &pb.Auction{Id: auctionID, Name: payload}, Bidder: eventType})
	if err != nil {
		log.Printf("history record error: %v", err)
	}
	event := &pb.HistoryEvent{AuctionId: auctionID, EventType: eventType, Payload: payload, Timestamp: time.Now().Unix()}
	_, err = g.updates.Publish(ctx, event)
	if err != nil {
		log.Printf("update publish error: %v", err)
	}
}

func (g *gatewayServer) publishUpdate(ctx context.Context, auctionID, payload string) {
	event := &pb.HistoryEvent{AuctionId: auctionID, EventType: "update", Payload: payload, Timestamp: time.Now().Unix()}
	_, err := g.updates.Publish(ctx, event)
	if err != nil {
		log.Printf("update publish error: %v", err)
	}
}

func generateID() string {
	return strconv.FormatInt(time.Now().UnixNano()+int64(rand.Intn(1000)), 36)
}

func formatAmount(v float64) string {
	return strconv.FormatFloat(v, 'f', 2, 64)
}

func getenv(key, fallback string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return fallback
}

func main() {
	port := getenv("GATEWAY_PORT", "7000")
	lis, err := net.Listen("tcp", ":"+port)
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}
	srv := grpc.NewServer()
	gateway := newGateway()
	gateway.initClients()
	pb.RegisterAuctionGatewayServer(srv, gateway)
	log.Printf("gateway listening on %s", port)
	if err := srv.Serve(lis); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
