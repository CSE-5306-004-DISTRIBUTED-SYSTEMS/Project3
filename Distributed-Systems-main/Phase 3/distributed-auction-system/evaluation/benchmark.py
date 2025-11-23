import requests
import time
import sys
import os
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

# Get BASE_URL from command line or environment
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else os.getenv('BASE_URL', 'http://localhost:8000')

# Correct API endpoints based on gateway
CREATE_AUCTION_URL = f"{BASE_URL}/api/auctions"
VIEW_AUCTIONS_URL = f"{BASE_URL}/api/auctions"
VIEW_HISTORY_URL = f"{BASE_URL}/api/history"

auction_ids = []

def create_auction():
    data = {"name": "Test Item", "description": "Test", "starting_bid": 10.0, "duration_seconds": 3600}
    start = time.time()
    try:
        response = requests.post(CREATE_AUCTION_URL, json=data)
        response.raise_for_status()
        resp = response.json()
        auction_id = resp.get("auction", {}).get("id")
        if auction_id:
            auction_ids.append(auction_id)
        return time.time() - start
    except Exception as e:
        print(f"Error creating auction: {e}")
        return None

def place_bid():
    if not auction_ids:
        return None
    auction_id = auction_ids[-1]  # Use the last created
    data = {"bidder": "user1", "amount": 15.0}
    url = f"{BASE_URL}/api/auctions/{auction_id}/bid"
    start = time.time()
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return time.time() - start
    except Exception as e:
        print(f"Error placing bid: {e}")
        return None

def view_auctions():
    start = time.time()
    try:
        response = requests.get(VIEW_AUCTIONS_URL)
        response.raise_for_status()
        return time.time() - start
    except Exception as e:
        print(f"Error viewing auctions: {e}")
        return None

def view_history():
    start = time.time()
    try:
        response = requests.get(VIEW_HISTORY_URL)
        response.raise_for_status()
        return time.time() - start
    except Exception as e:
        print(f"Error viewing history: {e}")
        return None

def run_benchmark(num_requests=100, concurrency=10):
    latencies = []
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for i in range(num_requests):
            if i % 4 == 0:
                futures.append(executor.submit(create_auction))
            elif i % 4 == 1:
                futures.append(executor.submit(place_bid))
            elif i % 4 == 2:
                futures.append(executor.submit(view_auctions))
            else:
                futures.append(executor.submit(view_history))

        for future in as_completed(futures):
            latency = future.result()
            if latency is not None:
                latencies.append(latency)

    total_time = time.time() - start_time
    throughput = len(latencies) / total_time if total_time > 0 else 0

    if latencies:
        avg_latency = statistics.mean(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        print(f"Total requests: {len(latencies)}")
        print(f"Average latency: {avg_latency:.4f} seconds")
        print(f"Min latency: {min_latency:.4f} seconds")
        print(f"Max latency: {max_latency:.4f} seconds")
        print(f"Throughput: {throughput:.2f} requests/second")
    else:
        print("No successful requests")

if __name__ == "__main__":
    run_benchmark()
