package pb

import (
	context "context"
	fmt "fmt"
	proto "github.com/golang/protobuf/proto"
	grpc "google.golang.org/grpc"
)

const _ = proto.ProtoPackageIsVersion4

type Auction struct {
	Id              string  `protobuf:"bytes,1,opt,name=id,proto3" json:"id,omitempty"`
	Name            string  `protobuf:"bytes,2,opt,name=name,proto3" json:"name,omitempty"`
	Description     string  `protobuf:"bytes,3,opt,name=description,proto3" json:"description,omitempty"`
	StartingBid     float64 `protobuf:"fixed64,4,opt,name=starting_bid,json=startingBid,proto3" json:"starting_bid,omitempty"`
	CurrentBid      float64 `protobuf:"fixed64,5,opt,name=current_bid,json=currentBid,proto3" json:"current_bid,omitempty"`
	HighestBidder   string  `protobuf:"bytes,6,opt,name=highest_bidder,json=highestBidder,proto3" json:"highest_bidder,omitempty"`
	DurationSeconds int64   `protobuf:"varint,7,opt,name=duration_seconds,json=durationSeconds,proto3" json:"duration_seconds,omitempty"`
	Status          string  `protobuf:"bytes,8,opt,name=status,proto3" json:"status,omitempty"`
	ClosingTime     int64   `protobuf:"varint,9,opt,name=closing_time,json=closingTime,proto3" json:"closing_time,omitempty"`
}

func (m *Auction) Reset()         { *m = Auction{} }
func (m *Auction) String() string { return proto.CompactTextString(m) }
func (*Auction) ProtoMessage()    {}

type HistoryEvent struct {
	AuctionId string `protobuf:"bytes,1,opt,name=auction_id,json=auctionId,proto3" json:"auction_id,omitempty"`
	EventType string `protobuf:"bytes,2,opt,name=event_type,json=eventType,proto3" json:"event_type,omitempty"`
	Payload   string `protobuf:"bytes,3,opt,name=payload,proto3" json:"payload,omitempty"`
	Timestamp int64  `protobuf:"varint,4,opt,name=timestamp,proto3" json:"timestamp,omitempty"`
}

func (m *HistoryEvent) Reset()         { *m = HistoryEvent{} }
func (m *HistoryEvent) String() string { return proto.CompactTextString(m) }
func (*HistoryEvent) ProtoMessage()    {}

type AuctionCommand struct {
	Command   string   `protobuf:"bytes,1,opt,name=command,proto3" json:"command,omitempty"`
	Auction   *Auction `protobuf:"bytes,2,opt,name=auction,proto3" json:"auction,omitempty"`
	BidAmount float64  `protobuf:"fixed64,3,opt,name=bid_amount,json=bidAmount,proto3" json:"bid_amount,omitempty"`
	Bidder    string   `protobuf:"bytes,4,opt,name=bidder,proto3" json:"bidder,omitempty"`
}

func (m *AuctionCommand) Reset()         { *m = AuctionCommand{} }
func (m *AuctionCommand) String() string { return proto.CompactTextString(m) }
func (*AuctionCommand) ProtoMessage()    {}

type AuctionResponse struct {
	Ok       bool            `protobuf:"varint,1,opt,name=ok,proto3" json:"ok,omitempty"`
	Message  string          `protobuf:"bytes,2,opt,name=message,proto3" json:"message,omitempty"`
	Auction  *Auction        `protobuf:"bytes,3,opt,name=auction,proto3" json:"auction,omitempty"`
	Auctions []*Auction      `protobuf:"bytes,4,rep,name=auctions,proto3" json:"auctions,omitempty"`
	History  []*HistoryEvent `protobuf:"bytes,5,rep,name=history,proto3" json:"history,omitempty"`
}

func (m *AuctionResponse) Reset()         { *m = AuctionResponse{} }
func (m *AuctionResponse) String() string { return proto.CompactTextString(m) }
func (*AuctionResponse) ProtoMessage()    {}

type Empty struct{}

func (m *Empty) Reset()         { *m = Empty{} }
func (m *Empty) String() string { return "{}" }
func (*Empty) ProtoMessage()    {}

type AuctionGatewayClient interface {
	Execute(ctx context.Context, in *AuctionCommand, opts ...grpc.CallOption) (*AuctionResponse, error)
	GetHistory(ctx context.Context, in *Empty, opts ...grpc.CallOption) (*AuctionResponse, error)
}

type auctionGatewayClient struct {
	cc *grpc.ClientConn
}

func NewAuctionGatewayClient(cc *grpc.ClientConn) AuctionGatewayClient {
	return &auctionGatewayClient{cc}
}

func (c *auctionGatewayClient) Execute(ctx context.Context, in *AuctionCommand, opts ...grpc.CallOption) (*AuctionResponse, error) {
	out := new(AuctionResponse)
	err := c.cc.Invoke(ctx, "/auction.AuctionGateway/Execute", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *auctionGatewayClient) GetHistory(ctx context.Context, in *Empty, opts ...grpc.CallOption) (*AuctionResponse, error) {
	out := new(AuctionResponse)
	err := c.cc.Invoke(ctx, "/auction.AuctionGateway/GetHistory", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

type AuctionGatewayServer interface {
	Execute(context.Context, *AuctionCommand) (*AuctionResponse, error)
	GetHistory(context.Context, *Empty) (*AuctionResponse, error)
}

type UnimplementedAuctionGatewayServer struct{}

func (*UnimplementedAuctionGatewayServer) Execute(context.Context, *AuctionCommand) (*AuctionResponse, error) {
	return nil, fmt.Errorf("method Execute not implemented")
}

func (*UnimplementedAuctionGatewayServer) GetHistory(context.Context, *Empty) (*AuctionResponse, error) {
	return nil, fmt.Errorf("method GetHistory not implemented")
}

func RegisterAuctionGatewayServer(s *grpc.Server, srv AuctionGatewayServer) {
	s.RegisterService(&_AuctionGateway_serviceDesc, srv)
}

func _AuctionGateway_Execute_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(AuctionCommand)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(AuctionGatewayServer).Execute(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/auction.AuctionGateway/Execute"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(AuctionGatewayServer).Execute(ctx, req.(*AuctionCommand))
	}
	return interceptor(ctx, in, info, handler)
}

func _AuctionGateway_GetHistory_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(Empty)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(AuctionGatewayServer).GetHistory(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/auction.AuctionGateway/GetHistory"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(AuctionGatewayServer).GetHistory(ctx, req.(*Empty))
	}
	return interceptor(ctx, in, info, handler)
}

var _AuctionGateway_serviceDesc = grpc.ServiceDesc{
	ServiceName: "auction.AuctionGateway",
	HandlerType: (*AuctionGatewayServer)(nil),
	Methods: []grpc.MethodDesc{
		{MethodName: "Execute", Handler: _AuctionGateway_Execute_Handler},
		{MethodName: "GetHistory", Handler: _AuctionGateway_GetHistory_Handler},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "proto/auction.proto",
}

type AuctionCatalogClient interface {
	Execute(ctx context.Context, in *AuctionCommand, opts ...grpc.CallOption) (*AuctionResponse, error)
}

type auctionCatalogClient struct{ cc *grpc.ClientConn }

func NewAuctionCatalogClient(cc *grpc.ClientConn) AuctionCatalogClient {
	return &auctionCatalogClient{cc}
}

func (c *auctionCatalogClient) Execute(ctx context.Context, in *AuctionCommand, opts ...grpc.CallOption) (*AuctionResponse, error) {
	out := new(AuctionResponse)
	err := c.cc.Invoke(ctx, "/auction.AuctionCatalog/Execute", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

type AuctionCatalogServer interface {
	Execute(context.Context, *AuctionCommand) (*AuctionResponse, error)
}

type UnimplementedAuctionCatalogServer struct{}

func (*UnimplementedAuctionCatalogServer) Execute(context.Context, *AuctionCommand) (*AuctionResponse, error) {
	return nil, fmt.Errorf("method Execute not implemented")
}

func RegisterAuctionCatalogServer(s *grpc.Server, srv AuctionCatalogServer) {
	s.RegisterService(&_AuctionCatalog_serviceDesc, srv)
}

func _AuctionCatalog_Execute_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(AuctionCommand)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(AuctionCatalogServer).Execute(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/auction.AuctionCatalog/Execute"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(AuctionCatalogServer).Execute(ctx, req.(*AuctionCommand))
	}
	return interceptor(ctx, in, info, handler)
}

var _AuctionCatalog_serviceDesc = grpc.ServiceDesc{
	ServiceName: "auction.AuctionCatalog",
	HandlerType: (*AuctionCatalogServer)(nil),
	Methods:     []grpc.MethodDesc{{MethodName: "Execute", Handler: _AuctionCatalog_Execute_Handler}},
	Streams:     []grpc.StreamDesc{},
	Metadata:    "proto/auction.proto",
}

type BidValidatorClient interface {
	Execute(ctx context.Context, in *AuctionCommand, opts ...grpc.CallOption) (*AuctionResponse, error)
}

type bidValidatorClient struct{ cc *grpc.ClientConn }

func NewBidValidatorClient(cc *grpc.ClientConn) BidValidatorClient { return &bidValidatorClient{cc} }

func (c *bidValidatorClient) Execute(ctx context.Context, in *AuctionCommand, opts ...grpc.CallOption) (*AuctionResponse, error) {
	out := new(AuctionResponse)
	err := c.cc.Invoke(ctx, "/auction.BidValidator/Execute", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

type BidValidatorServer interface {
	Execute(context.Context, *AuctionCommand) (*AuctionResponse, error)
}

type UnimplementedBidValidatorServer struct{}

func (*UnimplementedBidValidatorServer) Execute(context.Context, *AuctionCommand) (*AuctionResponse, error) {
	return nil, fmt.Errorf("method Execute not implemented")
}

func RegisterBidValidatorServer(s *grpc.Server, srv BidValidatorServer) {
	s.RegisterService(&_BidValidator_serviceDesc, srv)
}

func _BidValidator_Execute_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(AuctionCommand)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(BidValidatorServer).Execute(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/auction.BidValidator/Execute"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(BidValidatorServer).Execute(ctx, req.(*AuctionCommand))
	}
	return interceptor(ctx, in, info, handler)
}

var _BidValidator_serviceDesc = grpc.ServiceDesc{
	ServiceName: "auction.BidValidator",
	HandlerType: (*BidValidatorServer)(nil),
	Methods:     []grpc.MethodDesc{{MethodName: "Execute", Handler: _BidValidator_Execute_Handler}},
	Streams:     []grpc.StreamDesc{},
	Metadata:    "proto/auction.proto",
}

type HistoryRecorderClient interface {
	Execute(ctx context.Context, in *AuctionCommand, opts ...grpc.CallOption) (*AuctionResponse, error)
	List(ctx context.Context, in *Empty, opts ...grpc.CallOption) (*AuctionResponse, error)
}

type historyRecorderClient struct{ cc *grpc.ClientConn }

func NewHistoryRecorderClient(cc *grpc.ClientConn) HistoryRecorderClient {
	return &historyRecorderClient{cc}
}

func (c *historyRecorderClient) Execute(ctx context.Context, in *AuctionCommand, opts ...grpc.CallOption) (*AuctionResponse, error) {
	out := new(AuctionResponse)
	err := c.cc.Invoke(ctx, "/auction.HistoryRecorder/Execute", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *historyRecorderClient) List(ctx context.Context, in *Empty, opts ...grpc.CallOption) (*AuctionResponse, error) {
	out := new(AuctionResponse)
	err := c.cc.Invoke(ctx, "/auction.HistoryRecorder/List", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

type HistoryRecorderServer interface {
	Execute(context.Context, *AuctionCommand) (*AuctionResponse, error)
	List(context.Context, *Empty) (*AuctionResponse, error)
}

type UnimplementedHistoryRecorderServer struct{}

func (*UnimplementedHistoryRecorderServer) Execute(context.Context, *AuctionCommand) (*AuctionResponse, error) {
	return nil, fmt.Errorf("method Execute not implemented")
}

func (*UnimplementedHistoryRecorderServer) List(context.Context, *Empty) (*AuctionResponse, error) {
	return nil, fmt.Errorf("method List not implemented")
}

func RegisterHistoryRecorderServer(s *grpc.Server, srv HistoryRecorderServer) {
	s.RegisterService(&_HistoryRecorder_serviceDesc, srv)
}

func _HistoryRecorder_Execute_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(AuctionCommand)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(HistoryRecorderServer).Execute(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/auction.HistoryRecorder/Execute"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(HistoryRecorderServer).Execute(ctx, req.(*AuctionCommand))
	}
	return interceptor(ctx, in, info, handler)
}

func _HistoryRecorder_List_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(Empty)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(HistoryRecorderServer).List(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/auction.HistoryRecorder/List"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(HistoryRecorderServer).List(ctx, req.(*Empty))
	}
	return interceptor(ctx, in, info, handler)
}

var _HistoryRecorder_serviceDesc = grpc.ServiceDesc{
	ServiceName: "auction.HistoryRecorder",
	HandlerType: (*HistoryRecorderServer)(nil),
	Methods: []grpc.MethodDesc{
		{MethodName: "Execute", Handler: _HistoryRecorder_Execute_Handler},
		{MethodName: "List", Handler: _HistoryRecorder_List_Handler},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "proto/auction.proto",
}

type UpdateBroadcasterClient interface {
	Publish(ctx context.Context, in *HistoryEvent, opts ...grpc.CallOption) (*AuctionResponse, error)
	List(ctx context.Context, in *Empty, opts ...grpc.CallOption) (*AuctionResponse, error)
}

type updateBroadcasterClient struct{ cc *grpc.ClientConn }

func NewUpdateBroadcasterClient(cc *grpc.ClientConn) UpdateBroadcasterClient {
	return &updateBroadcasterClient{cc}
}

func (c *updateBroadcasterClient) Publish(ctx context.Context, in *HistoryEvent, opts ...grpc.CallOption) (*AuctionResponse, error) {
	out := new(AuctionResponse)
	err := c.cc.Invoke(ctx, "/auction.UpdateBroadcaster/Publish", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

func (c *updateBroadcasterClient) List(ctx context.Context, in *Empty, opts ...grpc.CallOption) (*AuctionResponse, error) {
	out := new(AuctionResponse)
	err := c.cc.Invoke(ctx, "/auction.UpdateBroadcaster/List", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

type UpdateBroadcasterServer interface {
	Publish(context.Context, *HistoryEvent) (*AuctionResponse, error)
	List(context.Context, *Empty) (*AuctionResponse, error)
}

type UnimplementedUpdateBroadcasterServer struct{}

func (*UnimplementedUpdateBroadcasterServer) Publish(context.Context, *HistoryEvent) (*AuctionResponse, error) {
	return nil, fmt.Errorf("method Publish not implemented")
}

func (*UnimplementedUpdateBroadcasterServer) List(context.Context, *Empty) (*AuctionResponse, error) {
	return nil, fmt.Errorf("method List not implemented")
}

func RegisterUpdateBroadcasterServer(s *grpc.Server, srv UpdateBroadcasterServer) {
	s.RegisterService(&_UpdateBroadcaster_serviceDesc, srv)
}

func _UpdateBroadcaster_Publish_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(HistoryEvent)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(UpdateBroadcasterServer).Publish(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/auction.UpdateBroadcaster/Publish"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(UpdateBroadcasterServer).Publish(ctx, req.(*HistoryEvent))
	}
	return interceptor(ctx, in, info, handler)
}

func _UpdateBroadcaster_List_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(Empty)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(UpdateBroadcasterServer).List(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/auction.UpdateBroadcaster/List"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(UpdateBroadcasterServer).List(ctx, req.(*Empty))
	}
	return interceptor(ctx, in, info, handler)
}

var _UpdateBroadcaster_serviceDesc = grpc.ServiceDesc{
	ServiceName: "auction.UpdateBroadcaster",
	HandlerType: (*UpdateBroadcasterServer)(nil),
	Methods: []grpc.MethodDesc{
		{MethodName: "Publish", Handler: _UpdateBroadcaster_Publish_Handler},
		{MethodName: "List", Handler: _UpdateBroadcaster_List_Handler},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "proto/auction.proto",
}

type WinnerNotifierClient interface {
	Execute(ctx context.Context, in *AuctionCommand, opts ...grpc.CallOption) (*AuctionResponse, error)
}

type winnerNotifierClient struct{ cc *grpc.ClientConn }

func NewWinnerNotifierClient(cc *grpc.ClientConn) WinnerNotifierClient {
	return &winnerNotifierClient{cc}
}

func (c *winnerNotifierClient) Execute(ctx context.Context, in *AuctionCommand, opts ...grpc.CallOption) (*AuctionResponse, error) {
	out := new(AuctionResponse)
	err := c.cc.Invoke(ctx, "/auction.WinnerNotifier/Execute", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

type WinnerNotifierServer interface {
	Execute(context.Context, *AuctionCommand) (*AuctionResponse, error)
}

type UnimplementedWinnerNotifierServer struct{}

func (*UnimplementedWinnerNotifierServer) Execute(context.Context, *AuctionCommand) (*AuctionResponse, error) {
	return nil, fmt.Errorf("method Execute not implemented")
}

func RegisterWinnerNotifierServer(s *grpc.Server, srv WinnerNotifierServer) {
	s.RegisterService(&_WinnerNotifier_serviceDesc, srv)
}

func _WinnerNotifier_Execute_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(AuctionCommand)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(WinnerNotifierServer).Execute(ctx, in)
	}
	info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/auction.WinnerNotifier/Execute"}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(WinnerNotifierServer).Execute(ctx, req.(*AuctionCommand))
	}
	return interceptor(ctx, in, info, handler)
}

var _WinnerNotifier_serviceDesc = grpc.ServiceDesc{
	ServiceName: "auction.WinnerNotifier",
	HandlerType: (*WinnerNotifierServer)(nil),
	Methods:     []grpc.MethodDesc{{MethodName: "Execute", Handler: _WinnerNotifier_Execute_Handler}},
	Streams:     []grpc.StreamDesc{},
	Metadata:    "proto/auction.proto",
}
