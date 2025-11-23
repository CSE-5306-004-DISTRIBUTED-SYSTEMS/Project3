import grpc
from concurrent import futures
import os
import json
import picture_pb2
import picture_pb2_grpc

UPLOAD_FOLDER = '/data/pictures'
METADATA_FILE = '/data/metadata.json'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f)

class PictureServicer(picture_pb2_grpc.PictureServiceServicer):
    def __init__(self):
        self.metadata = load_metadata()
        self.node_name = os.environ.get('NODE_NAME', 'unknown')
        # store 2pc commit status  add by John Song
        self.locks = {}

    # 2PC: Voting Phase---------------
    def VoteRequest(self, request, context):
        # Log reception
        print(f"Phase Voting of Node {self.node_name} received RPC VoteRequest from Phase Voting of Node {request.coordinator_id}")

        filename = request.filename
        # LOGIC: 
        # 1. Check if file is already locked by another transaction -> Vote No
        # 2. Check if file exists in metadata (for a Delete operation) -> Vote Yes
        # 3. If file doesn't exist -> Vote No (or Yes depending on how you want to handle 'delete non-existent')
        vote_granted = False
        if filename in self.locks:
            vote_granted = False # Resource busy
        elif filename in self.metadata:
            # Lock the resource
            self.locks[filename] = request.transaction_id
            vote_granted = True
        else:
            # File not found, cannot delete
            vote_granted = False
    
        # STRICT LOGGING: "sends RPC <rpc_name>"
        rpc_name = "VoteCommit" if vote_granted else "VoteAbort"
        print(f"Phase Voting of Node {self.node_name} sends RPC {rpc_name} to Phase Voting of Node {request.coordinator_id}")
        
        return picture_pb2.VoteReply(vote_granted=vote_granted, node_id=self.node_name)

    #---2PC: Decision Phase (commit)----
    def GlobalCommit(self, request, context):
        print(f"Phase Decision of Node {self.node_name} received RPC GlobalCommit from Phase Decision of Node {request.coordinator_id}")

        filename = request.filename
        
        # Execute Commit: Delete the file and metadata
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            
        if filename in self.metadata:
            del self.metadata[filename]
            save_metadata(self.metadata)
            
        # Unlock
        if filename in self.locks:
            del self.locks[filename]
            
        # STRICT LOGGING
        print(f"Phase Decision of Node {self.node_name} sends RPC Ack to Phase Decision of Node {request.coordinator_id}")
        
        return picture_pb2.Ack(success=True, node_id=self.node_name)
    
    # --- 2PC: DECISION PHASE (ABORT) ---
    def GlobalAbort(self, request, context):
        print(f"Phase Decision of Node {self.node_name} received RPC GlobalAbort from Phase Decision of Node {request.coordinator_id}")
        
        filename = request.filename
        
        # Execute Abort: Just release the lock, do not delete
        if filename in self.locks:
            del self.locks[filename]
            
        # STRICT LOGGING
        print(f"Phase Decision of Node {self.node_name} sends RPC Ack to Phase Decision of Node {request.coordinator_id}")
        
        return picture_pb2.Ack(success=True, node_id=self.node_name)


    def Health(self, request, context):
        return picture_pb2.HealthResponse(status='healthy', node=self.node_name)

    def Upload(self, request, context):
        filename = request.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        with open(filepath, 'wb') as f:
            f.write(request.data)
        
        self.metadata[filename] = {'likes': 0, 'node': self.node_name}
        save_metadata(self.metadata)
        
        return picture_pb2.UploadResponse(success=True, node=self.node_name)

    def Search(self, request, context):
        filename = request.filename
        if filename in self.metadata:
            return picture_pb2.SearchResponse(
                found=True,
                node=self.node_name,
                likes=self.metadata[filename]['likes']
            )
        return picture_pb2.SearchResponse(found=False)

    def Download(self, request, context):
        filename = request.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                return picture_pb2.DownloadResponse(data=f.read(), found=True)
        return picture_pb2.DownloadResponse(data=b'', found=False)

    def Delete(self, request, context):
        filename = request.filename
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            if filename in self.metadata:
                del self.metadata[filename]
                save_metadata(self.metadata)
            return picture_pb2.DeleteResponse(success=True)
        return picture_pb2.DeleteResponse(success=False)

    def Like(self, request, context):
        filename = request.filename
        if filename in self.metadata:
            self.metadata[filename]['likes'] += 1
            save_metadata(self.metadata)
            return picture_pb2.LikeResponse(
                success=True,
                likes=self.metadata[filename]['likes']
            )
        return picture_pb2.LikeResponse(success=False, likes=0)

    def List(self, request, context):
        pictures = {}
        for filename, meta in self.metadata.items():
            pictures[filename] = picture_pb2.PictureMetadata(
                likes=meta['likes'],
                node=self.node_name
            )
        return picture_pb2.ListResponse(pictures=pictures)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    picture_pb2_grpc.add_PictureServiceServicer_to_server(
        PictureServicer(), server
    )
    server.add_insecure_port('[::]:50051')
    server.start()
    print(f"gRPC node started on port 50051")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()