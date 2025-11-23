package pb

import (
    context "context"
    fmt "fmt"
    proto "github.com/golang/protobuf/proto"
    grpc "google.golang.org/grpc"
)

// Generated manually for consensus.proto to allow fully dockerized build
// without requiring host-side protoc installation.

const _ = proto.ProtoPackageIsVersion4

// Two-Phase Commit message types (Instructions.txt Q1/Q2).
type TwoPCVoteRequest struct {
    TxId      string `protobuf:"bytes,1,opt,name=tx_id,json=txId,proto3" json:"tx_id,omitempty"`
    Operation string `protobuf:"bytes,2,opt,name=operation,proto3" json:"operation,omitempty"`
}

func (m *TwoPCVoteRequest) Reset()         { *m = TwoPCVoteRequest{} }
func (m *TwoPCVoteRequest) String() string { return proto.CompactTextString(m) }
func (*TwoPCVoteRequest) ProtoMessage()    {}

type TwoPCVoteReply struct {
    TxId        string `protobuf:"bytes,1,opt,name=tx_id,json=txId,proto3" json:"tx_id,omitempty"`
    CommitReady bool   `protobuf:"varint,2,opt,name=commit_ready,json=commitReady,proto3" json:"commit_ready,omitempty"`
    Reason      string `protobuf:"bytes,3,opt,name=reason,proto3" json:"reason,omitempty"`
}

func (m *TwoPCVoteReply) Reset()         { *m = TwoPCVoteReply{} }
func (m *TwoPCVoteReply) String() string { return proto.CompactTextString(m) }
func (*TwoPCVoteReply) ProtoMessage()    {}

type TwoPCDecision struct {
    TxId         string `protobuf:"bytes,1,opt,name=tx_id,json=txId,proto3" json:"tx_id,omitempty"`
    GlobalCommit bool   `protobuf:"varint,2,opt,name=global_commit,json=globalCommit,proto3" json:"global_commit,omitempty"`
    Reason       string `protobuf:"bytes,3,opt,name=reason,proto3" json:"reason,omitempty"`
}

func (m *TwoPCDecision) Reset()         { *m = TwoPCDecision{} }
func (m *TwoPCDecision) String() string { return proto.CompactTextString(m) }
func (*TwoPCDecision) ProtoMessage()    {}

// --- TwoPCParticipant service ---

type TwoPCParticipantClient interface {
    Vote(ctx context.Context, in *TwoPCVoteRequest, opts ...grpc.CallOption) (*TwoPCVoteReply, error)
    Decide(ctx context.Context, in *TwoPCDecision, opts ...grpc.CallOption) (*TwoPCDecision, error)
}

type twoPCParticipantClient struct { cc *grpc.ClientConn }

func NewTwoPCParticipantClient(cc *grpc.ClientConn) TwoPCParticipantClient { return &twoPCParticipantClient{cc} }

func (c *twoPCParticipantClient) Vote(ctx context.Context, in *TwoPCVoteRequest, opts ...grpc.CallOption) (*TwoPCVoteReply, error) {
    out := new(TwoPCVoteReply)
    err := c.cc.Invoke(ctx, "/auction.TwoPCParticipant/Vote", in, out, opts...)
    if err != nil { return nil, err }
    return out, nil
}

func (c *twoPCParticipantClient) Decide(ctx context.Context, in *TwoPCDecision, opts ...grpc.CallOption) (*TwoPCDecision, error) {
    out := new(TwoPCDecision)
    err := c.cc.Invoke(ctx, "/auction.TwoPCParticipant/Decide", in, out, opts...)
    if err != nil { return nil, err }
    return out, nil
}

type TwoPCParticipantServer interface {
    Vote(context.Context, *TwoPCVoteRequest) (*TwoPCVoteReply, error)
    Decide(context.Context, *TwoPCDecision) (*TwoPCDecision, error)
}

type UnimplementedTwoPCParticipantServer struct{}

func (*UnimplementedTwoPCParticipantServer) Vote(context.Context, *TwoPCVoteRequest) (*TwoPCVoteReply, error) {
    return nil, fmt.Errorf("method Vote not implemented")
}
func (*UnimplementedTwoPCParticipantServer) Decide(context.Context, *TwoPCDecision) (*TwoPCDecision, error) {
    return nil, fmt.Errorf("method Decide not implemented")
}

func RegisterTwoPCParticipantServer(s *grpc.Server, srv TwoPCParticipantServer) {
    s.RegisterService(&_TwoPCParticipant_serviceDesc, srv)
}

func _TwoPCParticipant_Vote_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
    in := new(TwoPCVoteRequest)
    if err := dec(in); err != nil { return nil, err }
    if interceptor == nil { return srv.(TwoPCParticipantServer).Vote(ctx, in) }
    info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/auction.TwoPCParticipant/Vote"}
    handler := func(ctx context.Context, req interface{}) (interface{}, error) { return srv.(TwoPCParticipantServer).Vote(ctx, req.(*TwoPCVoteRequest)) }
    return interceptor(ctx, in, info, handler)
}

func _TwoPCParticipant_Decide_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
    in := new(TwoPCDecision)
    if err := dec(in); err != nil { return nil, err }
    if interceptor == nil { return srv.(TwoPCParticipantServer).Decide(ctx, in) }
    info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/auction.TwoPCParticipant/Decide"}
    handler := func(ctx context.Context, req interface{}) (interface{}, error) { return srv.(TwoPCParticipantServer).Decide(ctx, req.(*TwoPCDecision)) }
    return interceptor(ctx, in, info, handler)
}

var _TwoPCParticipant_serviceDesc = grpc.ServiceDesc{
    ServiceName: "auction.TwoPCParticipant",
    HandlerType: (*TwoPCParticipantServer)(nil),
    Methods: []grpc.MethodDesc{
        {MethodName: "Vote", Handler: _TwoPCParticipant_Vote_Handler},
        {MethodName: "Decide", Handler: _TwoPCParticipant_Decide_Handler},
    },
    Streams:  []grpc.StreamDesc{},
    Metadata: "proto/consensus.proto",
}

// --- TwoPCCoordinator service ---

type TwoPCCoordinatorClient interface {
    StartVoting(ctx context.Context, in *TwoPCVoteRequest, opts ...grpc.CallOption) (*TwoPCDecision, error)
}

type twoPCCoordinatorClient struct { cc *grpc.ClientConn }

func NewTwoPCCoordinatorClient(cc *grpc.ClientConn) TwoPCCoordinatorClient { return &twoPCCoordinatorClient{cc} }

func (c *twoPCCoordinatorClient) StartVoting(ctx context.Context, in *TwoPCVoteRequest, opts ...grpc.CallOption) (*TwoPCDecision, error) {
    out := new(TwoPCDecision)
    err := c.cc.Invoke(ctx, "/auction.TwoPCCoordinator/StartVoting", in, out, opts...)
    if err != nil { return nil, err }
    return out, nil
}

type TwoPCCoordinatorServer interface {
    StartVoting(context.Context, *TwoPCVoteRequest) (*TwoPCDecision, error)
}

type UnimplementedTwoPCCoordinatorServer struct{}

func (*UnimplementedTwoPCCoordinatorServer) StartVoting(context.Context, *TwoPCVoteRequest) (*TwoPCDecision, error) {
    return nil, fmt.Errorf("method StartVoting not implemented")
}

func RegisterTwoPCCoordinatorServer(s *grpc.Server, srv TwoPCCoordinatorServer) {
    s.RegisterService(&_TwoPCCoordinator_serviceDesc, srv)
}

func _TwoPCCoordinator_StartVoting_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
    in := new(TwoPCVoteRequest)
    if err := dec(in); err != nil { return nil, err }
    if interceptor == nil { return srv.(TwoPCCoordinatorServer).StartVoting(ctx, in) }
    info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/auction.TwoPCCoordinator/StartVoting"}
    handler := func(ctx context.Context, req interface{}) (interface{}, error) { return srv.(TwoPCCoordinatorServer).StartVoting(ctx, req.(*TwoPCVoteRequest)) }
    return interceptor(ctx, in, info, handler)
}

var _TwoPCCoordinator_serviceDesc = grpc.ServiceDesc{
    ServiceName: "auction.TwoPCCoordinator",
    HandlerType: (*TwoPCCoordinatorServer)(nil),
    Methods: []grpc.MethodDesc{
        {MethodName: "StartVoting", Handler: _TwoPCCoordinator_StartVoting_Handler},
    },
    Streams:  []grpc.StreamDesc{},
    Metadata: "proto/consensus.proto",
}
