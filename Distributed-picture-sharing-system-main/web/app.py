from flask import Flask, render_template, request, jsonify, send_file
import requests
import grpc
import picture_pb2
import picture_pb2_grpc
import random
import io
import time
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# All nodes with their types
ALL_NODES = [
    {'url': 'http://http-node1:5000', 'type': 'HTTP', 'name': 'http-node1'},
    {'url': 'http://http-node2:5000', 'type': 'HTTP', 'name': 'http-node2'},
    {'url': 'http://http-node3:5000', 'type': 'HTTP', 'name': 'http-node3'},
    {'url': 'grpc-node1:50051', 'type': 'gRPC', 'name': 'grpc-node1'},
    {'url': 'grpc-node2:50051', 'type': 'gRPC', 'name': 'grpc-node2'},
    {'url': 'grpc-node3:50051', 'type': 'gRPC', 'name': 'grpc-node3'},
]

logs = []

def add_log(message):
    """Add a log message with timestamp"""
    logs.append({
        'time': time.strftime('%H:%M:%S'),
        'message': message
    })
    if len(logs) > 100:
        logs.pop(0)

def upload_to_http(node, filename, file_data):
    """Upload to HTTP node"""
    try:
        files = {'file': (filename, io.BytesIO(file_data), 'image/jpeg')}
        response = requests.post(f"{node['url']}/upload", files=files, timeout=5)
        return response.json()
    except Exception as e:
        add_log(f"Error uploading to {node['name']}: {str(e)}")
        return None

def upload_to_grpc(node, filename, file_data):
    """Upload to gRPC node"""
    try:
        channel = grpc.insecure_channel(node['url'])
        stub = picture_pb2_grpc.PictureServiceStub(channel)
        response = stub.Upload(picture_pb2.UploadRequest(filename=filename, data=file_data))
        return {'success': response.success, 'node': response.node}
    except Exception as e:
        add_log(f"Error uploading to {node['name']}: {str(e)}")
        return None

def search_http(node, filename):
    """Search in HTTP node"""
    try:
        response = requests.get(f"{node['url']}/search/{filename}", timeout=2)
        result = response.json()
        if result.get('found'):
            result['type'] = node['type']
        return result
    except:
        return {'found': False}

def search_grpc(node, filename):
    """Search in gRPC node"""
    try:
        channel = grpc.insecure_channel(node['url'])
        stub = picture_pb2_grpc.PictureServiceStub(channel)
        response = stub.Search(picture_pb2.SearchRequest(filename=filename))
        if response.found:
            return {
                'found': True,
                'node': response.node,
                'likes': response.likes,
                'type': node['type']
            }
        return {'found': False}
    except:
        return {'found': False}

def list_from_http(node):
    """List pictures from HTTP node"""
    try:
        response = requests.get(f"{node['url']}/list", timeout=2)
        pictures = response.json()
        for filename in pictures:
            pictures[filename]['type'] = node['type']
        return pictures
    except:
        return {}

def list_from_grpc(node):
    """List pictures from gRPC node"""
    try:
        channel = grpc.insecure_channel(node['url'])
        stub = picture_pb2_grpc.PictureServiceStub(channel)
        response = stub.List(picture_pb2.ListRequest())
        pictures = {}
        for filename, meta in response.pictures.items():
            pictures[filename] = {
                'likes': meta.likes,
                'node': meta.node,
                'type': node['type']
            }
        return pictures
    except:
        return {}

def download_from_http(node, filename):
    """Download from HTTP node"""
    try:
        response = requests.get(f"{node['url']}/download/{filename}", timeout=5)
        if response.status_code == 200:
            return response.content
        return None
    except:
        return None

def download_from_grpc(node, filename):
    """Download from gRPC node"""
    try:
        channel = grpc.insecure_channel(node['url'])
        stub = picture_pb2_grpc.PictureServiceStub(channel)
        response = stub.Download(picture_pb2.DownloadRequest(filename=filename))
        if response.found:
            return response.data
        return None
    except:
        return None

def delete_from_http(node, filename):
    """Delete from HTTP node"""
    try:
        response = requests.delete(f"{node['url']}/delete/{filename}", timeout=2)
        return response.json().get('success', False)
    except:
        return False

def delete_from_grpc(node, filename):
    """Delete from gRPC node"""
    try:
        channel = grpc.insecure_channel(node['url'])
        stub = picture_pb2_grpc.PictureServiceStub(channel)
        response = stub.Delete(picture_pb2.DeleteRequest(filename=filename))
        return response.success
    except:
        return False

def like_http(node, filename):
    """Like in HTTP node"""
    try:
        response = requests.post(f"{node['url']}/like/{filename}", timeout=2)
        return response.json()
    except:
        return None

def like_grpc(node, filename):
    """Like in gRPC node"""
    try:
        channel = grpc.insecure_channel(node['url'])
        stub = picture_pb2_grpc.PictureServiceStub(channel)
        response = stub.Like(picture_pb2.LikeRequest(filename=filename))
        if response.success:
            return {'success': True, 'likes': response.likes}
        return None
    except:
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logs')
def get_logs():
    """Get recent logs"""
    return jsonify(logs)

@app.route('/upload', methods=['POST'])
def upload():
    """Upload picture to a random node (HTTP or gRPC)"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    # Read file data once
    file_data = file.read()
    filename = file.filename
    
    # Randomly select a node from all available nodes
    node = random.choice(ALL_NODES)
    
    # Upload based on node type
    if node['type'] == 'HTTP':
        result = upload_to_http(node, filename, file_data)
    else:  # gRPC
        result = upload_to_grpc(node, filename, file_data)
    
    if result and result.get('success'):
        add_log(f"Uploaded '{filename}' to {node['type']} node '{node['name']}'")
        return jsonify({
            'success': True,
            'filename': filename,
            'node': node['name'],
            'type': node['type']
        })
    
    return jsonify({'error': 'Upload failed'}), 500

@app.route('/list')
def list_pictures():
    """List all pictures from all nodes"""
    all_pictures = {}
    
    for node in ALL_NODES:
        if node['type'] == 'HTTP':
            pictures = list_from_http(node)
        else:  # gRPC
            pictures = list_from_grpc(node)
        
        all_pictures.update(pictures)
    
    return jsonify(all_pictures)

@app.route('/search/<filename>')
def search(filename):
    """Search for a picture across all nodes"""
    for node in ALL_NODES:
        if node['type'] == 'HTTP':
            result = search_http(node, filename)
        else:  # gRPC
            result = search_grpc(node, filename)
        
        if result.get('found'):
            add_log(f"Found '{filename}' on {node['type']} node '{node['name']}'")
            return jsonify(result)
    
    add_log(f"Picture '{filename}' not found in any node")
    return jsonify({'found': False})

@app.route('/download/<filename>')
def download(filename):
    """Download a picture from any node"""
    for node in ALL_NODES:
        if node['type'] == 'HTTP':
            data = download_from_http(node, filename)
        else:  # gRPC
            data = download_from_grpc(node, filename)
        
        if data:
            add_log(f"Downloaded '{filename}' from {node['type']} node '{node['name']}'")
            return send_file(
                io.BytesIO(data),
                as_attachment=True,
                download_name=filename
            )
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/delete/<filename>', methods=['DELETE'])
def delete(filename):
    """Delete a picture from any node"""
    for node in ALL_NODES:
        if node['type'] == 'HTTP':
            success = delete_from_http(node, filename)
        else:  # gRPC
            success = delete_from_grpc(node, filename)
        
        if success:
            add_log(f"Deleted '{filename}' from {node['type']} node '{node['name']}'")
            return jsonify({'success': True})
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/like/<filename>', methods=['POST'])
def like(filename):
    """Like a picture on any node"""
    for node in ALL_NODES:
        if node['type'] == 'HTTP':
            result = like_http(node, filename)
        else:  # gRPC
            result = like_grpc(node, filename)
        
        if result and result.get('success'):
            add_log(f"Liked '{filename}' on {node['type']} node, total likes: {result['likes']}")
            return jsonify(result)
    
    return jsonify({'error': 'File not found'}), 404

@app.route('/benchmark', methods=['POST'])
def benchmark():
    """Run benchmark tests on different strategies"""
    data = request.json
    test_type = data.get('test_type', 'mixed')  # http, grpc, or mixed
    workload = data.get('workload', 50)
    
    add_log(f"Starting benchmark: {test_type} strategy, {workload} requests")
    
    results = {
        'upload': {'latencies': [], 'successes': 0, 'http_count': 0, 'grpc_count': 0},
        'search': {'latencies': [], 'successes': 0},
        'download': {'latencies': [], 'successes': 0},
        'delete': {'latencies': [], 'successes': 0},
        'like': {'latencies': [], 'successes': 0}
    }
    
    # Filter nodes based on test type
    if test_type == 'http':
        test_nodes = [n for n in ALL_NODES if n['type'] == 'HTTP']
    elif test_type == 'grpc':
        test_nodes = [n for n in ALL_NODES if n['type'] == 'gRPC']
    else:  # mixed
        test_nodes = ALL_NODES
    
    test_files = []
    
    # Upload benchmark
    for i in range(workload):
        node = random.choice(test_nodes)
        filename = f"bench_{i}_{int(time.time())}.jpg"
        file_data = b'0' * (10 * 1024)  # 10KB test file
        
        start = time.time()
        if node['type'] == 'HTTP':
            result = upload_to_http(node, filename, file_data)
            if result:
                results['upload']['http_count'] += 1
        else:
            result = upload_to_grpc(node, filename, file_data)
            if result:
                results['upload']['grpc_count'] += 1
        
        latency = (time.time() - start) * 1000
        
        if result and result.get('success'):
            results['upload']['latencies'].append(latency)
            results['upload']['successes'] += 1
            test_files.append(filename)
    
    # Search, download, like benchmarks on uploaded files
    for filename in test_files[:min(30, len(test_files))]:
        # Search
        start = time.time()
        for node in test_nodes:
            if node['type'] == 'HTTP':
                result = search_http(node, filename)
            else:
                result = search_grpc(node, filename)
            if result.get('found'):
                results['search']['latencies'].append((time.time() - start) * 1000)
                results['search']['successes'] += 1
                break
        
        # Download
        start = time.time()
        for node in test_nodes:
            if node['type'] == 'HTTP':
                data = download_from_http(node, filename)
            else:
                data = download_from_grpc(node, filename)
            if data:
                results['download']['latencies'].append((time.time() - start) * 1000)
                results['download']['successes'] += 1
                break
        
        # Like
        start = time.time()
        for node in test_nodes:
            if node['type'] == 'HTTP':
                result = like_http(node, filename)
            else:
                result = like_grpc(node, filename)
            if result and result.get('success'):
                results['like']['latencies'].append((time.time() - start) * 1000)
                results['like']['successes'] += 1
                break
    
    # Delete benchmark
    for filename in test_files:
        start = time.time()
        for node in test_nodes:
            if node['type'] == 'HTTP':
                success = delete_from_http(node, filename)
            else:
                success = delete_from_grpc(node, filename)
            if success:
                results['delete']['latencies'].append((time.time() - start) * 1000)
                results['delete']['successes'] += 1
                break
    
    # Calculate statistics
    final_results = {}
    for operation, data in results.items():
        if data['latencies']:
            avg_latency = sum(data['latencies']) / len(data['latencies'])
            throughput = data['successes'] / (sum(data['latencies']) / 1000) if sum(data['latencies']) > 0 else 0
            final_results[operation] = {
                'avg_latency': round(avg_latency, 2),
                'min_latency': round(min(data['latencies']), 2),
                'max_latency': round(max(data['latencies']), 2),
                'throughput': round(throughput, 2),
                'successes': data['successes']
            }
            if operation == 'upload':
                final_results[operation]['http_count'] = data['http_count']
                final_results[operation]['grpc_count'] = data['grpc_count']
        else:
            final_results[operation] = {
                'avg_latency': 0,
                'throughput': 0,
                'successes': 0
            }
    
    add_log(f"Benchmark completed: {test_type} strategy")
    return jsonify(final_results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)