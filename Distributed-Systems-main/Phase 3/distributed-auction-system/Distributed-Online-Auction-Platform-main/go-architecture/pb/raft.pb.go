package pb

import (
    context "context"
    fmt "fmt"
    proto "github.com/golang/protobuf/proto"
    grpc "google.golang.org/grpc"
)

const _ = proto.ProtoPackageIsVersion4

type RaftNodeId struct { Id string `protobuf:"bytes,1,opt,name=id,proto3" json:"id,omitempty"` }
func (m *RaftNodeId) Reset()         { *m = RaftNodeId{} }
func (m *RaftNodeId) String() string { return proto.CompactTextString(m) }
func (*RaftNodeId) ProtoMessage()    {}

type RequestVoteArgs struct {
    CandidateId string `protobuf:"bytes,1,opt,name=candidate_id,json=candidateId,proto3" json:"candidate_id,omitempty"`
    Term        int64  `protobuf:"varint,2,opt,name=term,proto3" json:"term,omitempty"`
}
func (m *RequestVoteArgs) Reset()         { *m = RequestVoteArgs{} }
func (m *RequestVoteArgs) String() string { return proto.CompactTextString(m) }
func (*RequestVoteArgs) ProtoMessage()    {}

type RequestVoteReply struct {
    Term        int64 `protobuf:"varint,1,opt,name=term,proto3" json:"term,omitempty"`
    VoteGranted bool  `protobuf:"varint,2,opt,name=vote_granted,json=voteGranted,proto3" json:"vote_granted,omitempty"`
}
func (m *RequestVoteReply) Reset()         { *m = RequestVoteReply{} }
func (m *RequestVoteReply) String() string { return proto.CompactTextString(m) }
func (*RequestVoteReply) ProtoMessage()    {}

type AppendEntriesArgs struct {
    LeaderId    string      `protobuf:"bytes,1,opt,name=leader_id,json=leaderId,proto3" json:"leader_id,omitempty"`
    Term        int64       `protobuf:"varint,2,opt,name=term,proto3" json:"term,omitempty"`
    Entries     []*LogEntry `protobuf:"bytes,3,rep,name=entries,proto3" json:"entries,omitempty"`
    CommitIndex int64       `protobuf:"varint,4,opt,name=commit_index,json=commitIndex,proto3" json:"commit_index,omitempty"`
}
func (m *AppendEntriesArgs) Reset()         { *m = AppendEntriesArgs{} }
func (m *AppendEntriesArgs) String() string { return proto.CompactTextString(m) }
func (*AppendEntriesArgs) ProtoMessage()    {}

type AppendEntriesReply struct {
    Term        int64 `protobuf:"varint,1,opt,name=term,proto3" json:"term,omitempty"`
    Success     bool  `protobuf:"varint,2,opt,name=success,proto3" json:"success,omitempty"`
    AppliedUpTo int64 `protobuf:"varint,3,opt,name=applied_up_to,json=appliedUpTo,proto3" json:"applied_up_to,omitempty"`
}
func (m *AppendEntriesReply) Reset()         { *m = AppendEntriesReply{} }
func (m *AppendEntriesReply) String() string { return proto.CompactTextString(m) }
func (*AppendEntriesReply) ProtoMessage()    {}

// Q4 additions
type LogEntry struct {
    Operation string `protobuf:"bytes,1,opt,name=operation,proto3" json:"operation,omitempty"`
    Term      int64  `protobuf:"varint,2,opt,name=term,proto3" json:"term,omitempty"`
    Index     int64  `protobuf:"varint,3,opt,name=index,proto3" json:"index,omitempty"`
}
func (m *LogEntry) Reset()         { *m = LogEntry{} }
func (m *LogEntry) String() string { return proto.CompactTextString(m) }
func (*LogEntry) ProtoMessage()    {}

// Expand AppendEntriesArgs with full log + commit index
type ClientRequestArgs struct {
    Operation string `protobuf:"bytes,1,opt,name=operation,proto3" json:"operation,omitempty"`
}
func (m *ClientRequestArgs) Reset()         { *m = ClientRequestArgs{} }
func (m *ClientRequestArgs) String() string { return proto.CompactTextString(m) }
func (*ClientRequestArgs) ProtoMessage()    {}

type ClientRequestReply struct {
    Accepted       bool   `protobuf:"varint,1,opt,name=accepted,proto3" json:"accepted,omitempty"`
    Message        string `protobuf:"bytes,2,opt,name=message,proto3" json:"message,omitempty"`
    Index          int64  `protobuf:"varint,3,opt,name=index,proto3" json:"index,omitempty"`
    CommittedIndex int64  `protobuf:"varint,4,opt,name=committed_index,json=committedIndex,proto3" json:"committed_index,omitempty"`
}
func (m *ClientRequestReply) Reset()         { *m = ClientRequestReply{} }
func (m *ClientRequestReply) String() string { return proto.CompactTextString(m) }
func (*ClientRequestReply) ProtoMessage()    {}

// Client interface
type RaftNodeClient interface {
    RequestVote(ctx context.Context, in *RequestVoteArgs, opts ...grpc.CallOption) (*RequestVoteReply, error)
    AppendEntries(ctx context.Context, in *AppendEntriesArgs, opts ...grpc.CallOption) (*AppendEntriesReply, error)
    ClientRequest(ctx context.Context, in *ClientRequestArgs, opts ...grpc.CallOption) (*ClientRequestReply, error)
}
type raftNodeClient struct { cc *grpc.ClientConn }
func NewRaftNodeClient(cc *grpc.ClientConn) RaftNodeClient { return &raftNodeClient{cc} }
func (c *raftNodeClient) RequestVote(ctx context.Context, in *RequestVoteArgs, opts ...grpc.CallOption) (*RequestVoteReply, error) {
    out := new(RequestVoteReply)
    err := c.cc.Invoke(ctx, "/auction.RaftNode/RequestVote", in, out, opts...)
    if err != nil { return nil, err }
    return out, nil
}
func (c *raftNodeClient) AppendEntries(ctx context.Context, in *AppendEntriesArgs, opts ...grpc.CallOption) (*AppendEntriesReply, error) {
    out := new(AppendEntriesReply)
    err := c.cc.Invoke(ctx, "/auction.RaftNode/AppendEntries", in, out, opts...)
    if err != nil { return nil, err }
    return out, nil
}
func (c *raftNodeClient) ClientRequest(ctx context.Context, in *ClientRequestArgs, opts ...grpc.CallOption) (*ClientRequestReply, error) {
    out := new(ClientRequestReply)
    err := c.cc.Invoke(ctx, "/auction.RaftNode/ClientRequest", in, out, opts...)
    if err != nil { return nil, err }
    return out, nil
}

// Server interface
type RaftNodeServer interface {
    RequestVote(context.Context, *RequestVoteArgs) (*RequestVoteReply, error)
    AppendEntries(context.Context, *AppendEntriesArgs) (*AppendEntriesReply, error)
    ClientRequest(context.Context, *ClientRequestArgs) (*ClientRequestReply, error)
}
type UnimplementedRaftNodeServer struct{}
func (*UnimplementedRaftNodeServer) RequestVote(context.Context, *RequestVoteArgs) (*RequestVoteReply, error) {
    return nil, fmt.Errorf("method RequestVote not implemented")
}
func (*UnimplementedRaftNodeServer) AppendEntries(context.Context, *AppendEntriesArgs) (*AppendEntriesReply, error) {
    return nil, fmt.Errorf("method AppendEntries not implemented")
}
func (*UnimplementedRaftNodeServer) ClientRequest(context.Context, *ClientRequestArgs) (*ClientRequestReply, error) {
    return nil, fmt.Errorf("method ClientRequest not implemented")
}

func RegisterRaftNodeServer(s *grpc.Server, srv RaftNodeServer) { s.RegisterService(&_RaftNode_serviceDesc, srv) }

func _RaftNode_RequestVote_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
    in := new(RequestVoteArgs)
    if err := dec(in); err != nil { return nil, err }
    if interceptor == nil { return srv.(RaftNodeServer).RequestVote(ctx, in) }
    info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/auction.RaftNode/RequestVote"}
    handler := func(ctx context.Context, req interface{}) (interface{}, error) { return srv.(RaftNodeServer).RequestVote(ctx, req.(*RequestVoteArgs)) }
    return interceptor(ctx, in, info, handler)
}
func _RaftNode_AppendEntries_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
    in := new(AppendEntriesArgs)
    if err := dec(in); err != nil { return nil, err }
    if interceptor == nil { return srv.(RaftNodeServer).AppendEntries(ctx, in) }
    info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/auction.RaftNode/AppendEntries"}
    handler := func(ctx context.Context, req interface{}) (interface{}, error) { return srv.(RaftNodeServer).AppendEntries(ctx, req.(*AppendEntriesArgs)) }
    return interceptor(ctx, in, info, handler)
}
func _RaftNode_ClientRequest_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
    in := new(ClientRequestArgs)
    if err := dec(in); err != nil { return nil, err }
    if interceptor == nil { return srv.(RaftNodeServer).ClientRequest(ctx, in) }
    info := &grpc.UnaryServerInfo{Server: srv, FullMethod: "/auction.RaftNode/ClientRequest"}
    handler := func(ctx context.Context, req interface{}) (interface{}, error) { return srv.(RaftNodeServer).ClientRequest(ctx, req.(*ClientRequestArgs)) }
    return interceptor(ctx, in, info, handler)
}
var _RaftNode_serviceDesc = grpc.ServiceDesc{ ServiceName: "auction.RaftNode", HandlerType: (*RaftNodeServer)(nil), Methods: []grpc.MethodDesc{ {MethodName: "RequestVote", Handler: _RaftNode_RequestVote_Handler}, {MethodName: "AppendEntries", Handler: _RaftNode_AppendEntries_Handler}, {MethodName: "ClientRequest", Handler: _RaftNode_ClientRequest_Handler}, }, Streams: []grpc.StreamDesc{}, Metadata: "proto/raft.proto" }
