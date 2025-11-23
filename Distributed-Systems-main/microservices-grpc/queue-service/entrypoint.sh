#!/bin/sh
set -e

# Start the gRPC server
exec python3 /app/raft_server.py
