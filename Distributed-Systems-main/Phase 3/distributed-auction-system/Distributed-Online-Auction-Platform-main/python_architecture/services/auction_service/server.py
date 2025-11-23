import json
import os
import threading
import time
from http.server import HTTPServer
from typing import Dict, List

from python_architecture.common.http import JSONRequestHandler


auctions: Dict[str, dict] = {}
_lock = threading.Lock()


def _clone_auction(auction: dict) -> dict:
    copy = dict(auction)
    bids: List[dict] = copy.get("bids", [])
    copy["bids"] = [dict(bid) for bid in bids]
    if "status_reason" not in copy:
        status = copy.get("status")
        if status == "OPEN":
            copy["status_reason"] = "Open for bids"
        elif status == "ENDED":
            copy["status_reason"] = "Bid time ended"
        elif status == "CLOSED":
            copy["status_reason"] = "Closed manually"
        else:
            copy["status_reason"] = "Auction is not active"
    return copy


def _expire_if_needed(auction: dict) -> bool:
    if not auction or auction.get("status") != "OPEN":
        return False
    closing_time = auction.get("closing_time")
    if not closing_time:
        return False
    if time.time() >= closing_time:
        auction["status"] = "ENDED"
        auction["status_reason"] = "Bid time ended"
        auction["closing_time"] = closing_time
        return True
    return False


class AuctionHandler(JSONRequestHandler):
    routes = []


@AuctionHandler.route("POST", "/auctions")
def create_auction(handler, payload, params):
    name = payload.get("name")
    starting_bid = payload.get("starting_bid", 0)
    duration = payload.get("duration_seconds")
    if duration in (None, ""):
        duration = 0
    try:
        duration = int(duration)
    except (TypeError, ValueError):
        return 400, {"error": "duration_seconds must be an integer"}
    if duration < 0:
        return 400, {"error": "duration_seconds cannot be negative"}
    if not name:
        return 400, {"error": "name is required"}
    if starting_bid <= 0:
        return 400, {"error": "starting_bid must be positive"}
    auction_id = str(int(time.time() * 1000))
    auction = {
        "id": auction_id,
        "name": name,
        "description": payload.get("description", ""),
        "starting_bid": starting_bid,
        "current_bid": starting_bid,
        "highest_bidder": "",
        "duration_seconds": duration,
        "status": "OPEN",
        "status_reason": "Open for bids",
        "closing_time": time.time() + duration if duration else 0,
        "bids": [],
    }
    with _lock:
        auctions[auction_id] = auction
    return 201, {"auction": _clone_auction(auction)}


@AuctionHandler.route("GET", "/auctions")
def list_auctions(handler, payload, params):
    with _lock:
        for item in auctions.values():
            _expire_if_needed(item)
        values = [_clone_auction(item) for item in auctions.values()]
    return 200, {"auctions": values}


@AuctionHandler.route("GET", "/auctions/<auction_id>")
def get_auction(handler, payload, params):
    auction_id = params.get("auction_id")
    with _lock:
        auction = auctions.get(auction_id)
        if not auction:
            return 404, {"error": "auction not found"}
        _expire_if_needed(auction)
        cloned = _clone_auction(auction)
    return 200, {"auction": cloned}


@AuctionHandler.route("POST", "/auctions/<auction_id>/bid")
def update_bid(handler, payload, params):
    auction_id = params.get("auction_id")
    amount = payload.get("amount", 0)
    bidder = payload.get("bidder", "")
    if amount <= 0 or not bidder:
        return 400, {"error": "invalid bid"}
    with _lock:
        auction = auctions.get(auction_id)
        if not auction:
            return 404, {"error": "auction not found"}
        if _expire_if_needed(auction):
            return 409, {"error": "Bid time ended"}
        if auction.get("status") != "OPEN":
            message = auction.get("status_reason") or "auction is not active"
            return 409, {"error": message}
        auction["current_bid"] = amount
        auction["highest_bidder"] = bidder
        auction.setdefault("bids", []).append({
            "bidder": bidder,
            "amount": amount,
            "timestamp": time.time(),
        })
        cloned = _clone_auction(auction)
    return 200, {"auction": cloned}


@AuctionHandler.route("POST", "/auctions/<auction_id>/close")
def close_auction(handler, payload, params):
    auction_id = params.get("auction_id")
    with _lock:
        auction = auctions.get(auction_id)
        if not auction:
            return 404, {"error": "auction not found"}
        previously_open = auction.get("status") == "OPEN"
        if _expire_if_needed(auction):
            previously_open = False
        if previously_open:
            auction["status"] = "CLOSED"
            auction["status_reason"] = "Closed manually"
            auction["closing_time"] = time.time()
        closed = _clone_auction(auction)
    return 200, {"auction": closed}


def run():
    port = int(os.getenv("AUCTION_SERVICE_PORT", "8001"))
    server = HTTPServer(("0.0.0.0", port), AuctionHandler)
    print(f"Auction service listening on {port}")
    server.serve_forever()


if __name__ == "__main__":
    run()

