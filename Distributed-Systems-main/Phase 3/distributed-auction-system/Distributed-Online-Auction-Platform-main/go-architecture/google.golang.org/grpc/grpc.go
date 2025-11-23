package grpc

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
)

type CallOption interface{}
type DialOption interface{}
type ServerOption interface{}

type UnaryServerInfo struct {
	Server     interface{}
	FullMethod string
}

type UnaryHandler func(ctx context.Context, req interface{}) (interface{}, error)

type UnaryServerInterceptor func(ctx context.Context, req interface{}, info *UnaryServerInfo, handler UnaryHandler) (interface{}, error)

type MethodDesc struct {
	MethodName string
	Handler    func(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor UnaryServerInterceptor) (interface{}, error)
}

type StreamDesc struct{}

type ServiceDesc struct {
	ServiceName string
	HandlerType interface{}
	Methods     []MethodDesc
	Streams     []StreamDesc
	Metadata    interface{}
}

type serviceInfo struct {
	impl    interface{}
	methods map[string]func(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor UnaryServerInterceptor) (interface{}, error)
}

type Server struct {
	services map[string]*serviceInfo
}

func NewServer(opts ...ServerOption) *Server {
	return &Server{services: make(map[string]*serviceInfo)}
}

func (s *Server) RegisterService(sd *ServiceDesc, impl interface{}) {
	if _, exists := s.services[sd.ServiceName]; exists {
		panic("service already registered")
	}
	info := &serviceInfo{impl: impl, methods: make(map[string]func(interface{}, context.Context, func(interface{}) error, UnaryServerInterceptor) (interface{}, error))}
	for _, m := range sd.Methods {
		info.methods[m.MethodName] = m.Handler
	}
	s.services[sd.ServiceName] = info
}

func (s *Server) Serve(lis net.Listener) error {
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "unsupported method", http.StatusMethodNotAllowed)
			return
		}
		service, method, err := parseFullMethod(r.URL.Path)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		svc, ok := s.services[service]
		if !ok {
			http.Error(w, "service not found", http.StatusNotFound)
			return
		}
		handler, ok := svc.methods[method]
		if !ok {
			http.Error(w, "method not found", http.StatusNotFound)
			return
		}
		body, err := io.ReadAll(r.Body)
		if err != nil {
			http.Error(w, "invalid body", http.StatusBadRequest)
			return
		}
		dec := func(v interface{}) error {
			if len(body) == 0 {
				return nil
			}
			return json.Unmarshal(body, v)
		}
		resp, err := handler(svc.impl, r.Context(), dec, nil)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		if resp == nil {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		enc := json.NewEncoder(w)
		_ = enc.Encode(resp)
	})
	return http.Serve(lis, handler)
}

type ClientConn struct {
	target string
	client *http.Client
}

func Dial(target string, opts ...DialOption) (*ClientConn, error) {
	return &ClientConn{target: target, client: &http.Client{}}, nil
}

func (c *ClientConn) Invoke(ctx context.Context, method string, in interface{}, out interface{}, opts ...CallOption) error {
	url := fmt.Sprintf("http://%s%s", c.target, method)
	var buf bytes.Buffer
	if in != nil {
		if err := json.NewEncoder(&buf).Encode(in); err != nil {
			return err
		}
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, &buf)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := c.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("remote error: %s", bytes.TrimSpace(body))
	}
	if out == nil {
		io.Copy(io.Discard, resp.Body)
		return nil
	}
	return json.NewDecoder(resp.Body).Decode(out)
}

type ServerStream interface{}

type ClientStream interface{}

func parseFullMethod(path string) (string, string, error) {
	if len(path) == 0 || path[0] != '/' {
		return "", "", fmt.Errorf("invalid method path")
	}
	parts := bytes.Split([]byte(path[1:]), []byte{'/'})
	if len(parts) != 2 {
		return "", "", fmt.Errorf("invalid method path")
	}
	return string(parts[0]), string(parts[1]), nil
}
