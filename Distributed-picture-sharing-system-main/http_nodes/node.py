from flask import Flask, request, jsonify, send_file
import os
import json
import time
from werkzeug.utils import secure_filename

import uuid
# --- NEW IMPORTS FOR 2PC ---
import grpc
# You must copy picture_pb2.py and picture_pb2_grpc.py into the http_nodes folder!
import picture_pb2
import picture_pb2_grpc



app = Flask(__name__)
UPLOAD_FOLDER = '/data/pictures'
METADATA_FILE = '/data/metadata.json'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

#-----Add for Coordinator-----
# Helper to identify this node (e.g., http-node1)
NODE_NAME = os.environ.get('NODE_NAME', 'http-node-unknown')

# Define the 3 gRPC Participants (The Workers)
GRPC_NODES = [
    'grpc-node1:50051',
    'grpc-node2:50051',
    'grpc-node3:50051'
]
#----------------------------



def load_metadata():
    """Load picture metadata from disk"""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_metadata(metadata):
    """Save picture metadata to disk"""
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f)

metadata = load_metadata()

##----Modify section---------------------
@app.route('/delete-2pc/<filename>', methods=['DELETE'])
def delete_two_phase(filename):
    """
    Coordinator logic for Two-Phase Commit Delete.
    This function manages the Voting and Decision phases.
    """
    transaction_id = str(uuid.uuid4())
    print(f"\n--- Starting 2PC Transaction {transaction_id} for {filename} ---")

    # 1. Connect to Participants
    stubs = []
    for target in GRPC_NODES:
        channel = grpc.insecure_channel(target)
        stubs.append(picture_pb2_grpc.PictureServiceStub(channel))

    # --- PHASE 1: VOTING ---
    votes = []
    
    for i, stub in enumerate(stubs):
        participant_name = f"grpc-node{i+1}"
        
        # LOG REQUIREMENT: Node <id> sends RPC <name> to Node <id>
        print(f"Node {NODE_NAME} sends RPC VoteRequest to Node {participant_name}")
        
        try:
            req = picture_pb2.VoteArgs(
                transaction_id=transaction_id,
                coordinator_id=NODE_NAME,
                filename=filename
            )
            # Short timeout to fail fast if node is down
            reply = stub.VoteRequest(req, timeout=2)
            votes.append(reply.vote_granted)
            
        except grpc.RpcError:
            print(f"Node {participant_name} failed to respond (Voting).")
            votes.append(False) # Treat as NO vote

    # --- PHASE 2: DECISION ---
    # Logic: If ALL participants voted True (Yes), we Commit. Otherwise Abort.
    if all(votes) and len(votes) == len(GRPC_NODES):
        decision_rpc = "GlobalCommit"
    else:
        decision_rpc = "GlobalAbort"

    results = []

    for i, stub in enumerate(stubs):
        participant_name = f"grpc-node{i+1}"
        
        # LOG REQUIREMENT: Node <id> sends RPC <name> to Node <id>
        print(f"Node {NODE_NAME} sends RPC {decision_rpc} to Node {participant_name}")
        
        req = picture_pb2.DecisionArgs(
            transaction_id=transaction_id,
            coordinator_id=NODE_NAME,
            filename=filename
        )
        try:
            if decision_rpc == "GlobalCommit":
                stub.GlobalCommit(req, timeout=2)
            else:
                stub.GlobalAbort(req, timeout=2)
            results.append("ACK")
        except grpc.RpcError:
            print(f"Node {participant_name} failed to respond (Decision).")
            results.append("FAILED")

    # Finalize local deletion if global commit succeeded
    if decision_rpc == "GlobalCommit":
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        if filename in metadata:
            del metadata[filename]
            save_metadata(metadata)

    return jsonify({
        "transaction_id": transaction_id,
        "status": "COMMITTED" if decision_rpc == "GlobalCommit" else "ABORTED",
        "details": results
    })




##-------------unchange------------------

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'node': os.environ.get('NODE_NAME', 'unknown')})

@app.route('/upload', methods=['POST'])
def upload():
    """Upload a picture to this node"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # Save metadata
    metadata[filename] = {
        'likes': 0,
        'upload_time': time.time(),
        'node': os.environ.get('NODE_NAME', 'unknown')
    }
    save_metadata(metadata)
    
    return jsonify({
        'success': True,
        'filename': filename,
        'node': os.environ.get('NODE_NAME', 'unknown')
    })

@app.route('/list', methods=['GET'])
def list_pictures():
    """List all pictures on this node"""
    return jsonify(metadata)

@app.route('/search/<filename>', methods=['GET'])
def search(filename):
    """Search for a picture by filename"""
    if filename in metadata:
        return jsonify({
            'found': True,
            'filename': filename,
            'node': os.environ.get('NODE_NAME', 'unknown'),
            'likes': metadata[filename]['likes']
        })
    return jsonify({'found': False})

@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    """Download a picture from this node"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404

@app.route('/delete/<filename>', methods=['DELETE'])
def delete(filename):
    """Delete a picture from this node"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        if filename in metadata:
            del metadata[filename]
            save_metadata(metadata)
        return jsonify({'success': True})
    return jsonify({'error': 'File not found'}), 404

@app.route('/like/<filename>', methods=['POST'])
def like(filename):
    """Increment like count for a picture"""
    if filename in metadata:
        metadata[filename]['likes'] += 1
        save_metadata(metadata)
        return jsonify({
            'success': True,
            'likes': metadata[filename]['likes']
        })
    return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)