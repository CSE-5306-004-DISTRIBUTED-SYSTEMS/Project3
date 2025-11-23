import json
import os
import threading
from http.server import ThreadingHTTPServer
from queue import Empty, Queue
from urllib import error, request

from python_architecture.common.http import JSONRequestHandler, StreamingResponse

AUCTION_SERVICE = os.getenv("AUCTION_SERVICE_URL", "http://auction_service:8001")
BIDDING_SERVICE = os.getenv("BIDDING_SERVICE_URL", "http://bidding_service:8002")
HISTORY_SERVICE = os.getenv("HISTORY_SERVICE_URL", "http://history_service:8003")


class GatewayHandler(JSONRequestHandler):
    routes = []


class _EventBus:
    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers = []

    def subscribe(self) -> Queue:
        queue: Queue = Queue()
        with self._lock:
            self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: Queue):
        with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    def publish(self, event_type: str, payload):
        message = {"type": event_type, "data": payload}
        with self._lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            queue.put(message)


_updates_bus = _EventBus()


def _broadcast_auction(auction: dict):
    if auction:
        _updates_bus.publish("auction", auction)


def _broadcast_history(event: dict):
    if event:
        _updates_bus.publish("history", event)


def call_service(method: str, url: str, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req) as resp:
            body = resp.read()
            return resp.status, json.loads(body.decode("utf-8")) if body else {}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {"error": body or exc.reason}
        if "error" not in payload:
            payload.setdefault("error", exc.reason)
        return exc.code, payload


@GatewayHandler.route("POST", "/api/auctions")
def create_auction(handler, payload, params):
    status, resp = call_service("POST", f"{AUCTION_SERVICE}/auctions", payload)
    if status >= 400:
        return status, resp
    auction = resp.get("auction")
    if auction:
        history_payload = {
            "auction_id": auction["id"],
            "event_type": "created",
            "payload": auction["name"],
        }
        _, history_resp = call_service("POST", f"{HISTORY_SERVICE}/events", history_payload)
        _broadcast_auction(auction)
        _broadcast_history(history_resp.get("event"))
    return 201, resp


@GatewayHandler.route("GET", "/api/auctions")
def list_auctions(handler, payload, params):
    status, resp = call_service("GET", f"{AUCTION_SERVICE}/auctions")
    return status, resp


def _execute_bid(auction_id: str, bidder: str, amount):
    if not bidder:
        return 400, {"error": "bidder is required"}
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        return 400, {"error": "amount must be numeric"}
    if amount_value <= 0:
        return 400, {"error": "amount must be positive"}

    status, current = call_service("GET", f"{AUCTION_SERVICE}/auctions/{auction_id}")
    if status != 200:
        return status, current
    auction = current.get("auction")
    if not auction:
        return 404, {"error": "auction not found"}
    if auction.get("status") != "OPEN":
        message = auction.get("status_reason") or "Auction is not active"
        return 409, {"error": message}

    validation_payload = {
        "amount": amount_value,
        "current_bid": auction.get("current_bid"),
        "bidder": bidder,
    }
    status, validation = call_service("POST", f"{BIDDING_SERVICE}/validate", validation_payload)
    if status >= 400:
        return status, validation
    if not validation.get("ok"):
        return 409, validation

    status, update = call_service("POST", f"{AUCTION_SERVICE}/auctions/{auction_id}/bid", {
        "bidder": bidder,
        "amount": amount_value,
    })
    if status >= 400:
        return status, update

    _, history_resp = call_service("POST", f"{HISTORY_SERVICE}/events", {
        "auction_id": auction_id,
        "event_type": "bid",
        "payload": f"{bidder} bid ${amount_value}",
    })
    _broadcast_auction(update.get("auction"))
    _broadcast_history(history_resp.get("event"))
    return 200, update


@GatewayHandler.route("POST", "/api/auctions/<auction_id>/bid")
def place_bid(handler, payload, params):
    auction_id = params.get("auction_id")
    bidder = payload.get("bidder", "")
    amount = payload.get("amount")
    status, resp = _execute_bid(auction_id, bidder, amount)
    return status, resp


@GatewayHandler.route("POST", "/api/auctions/<auction_id>/bids/bulk")
def place_bulk_bids(handler, payload, params):
    auction_id = params.get("auction_id")
    bids = payload.get("bids")
    if not isinstance(bids, list) or not bids:
        return 400, {"error": "bids must be a non-empty list"}

    results = []
    accepted = 0
    for entry in bids:
        bidder = entry.get("bidder", "") if isinstance(entry, dict) else ""
        amount = entry.get("amount") if isinstance(entry, dict) else None
        status, resp = _execute_bid(auction_id, bidder, amount)
        results.append({
            "bidder": bidder,
            "amount": amount,
            "status": status,
            "response": resp,
        })
        if status < 400:
            accepted += 1

    overall_status = 200 if accepted else 409
    return overall_status, {
        "submitted": len(bids),
        "accepted": accepted,
        "results": results,
    }


@GatewayHandler.route("POST", "/api/auctions/<auction_id>/close")
def close_auction(handler, payload, params):
    auction_id = params.get("auction_id")
    status, closed = call_service("POST", f"{AUCTION_SERVICE}/auctions/{auction_id}/close")
    if status >= 400:
        return status, closed
    auction = closed.get("auction")
    if auction:
        _, history_resp = call_service("POST", f"{HISTORY_SERVICE}/events", {
            "auction_id": auction_id,
            "event_type": "closed",
            "payload": auction.get("highest_bidder", ""),
        })
        _broadcast_auction(auction)
        _broadcast_history(history_resp.get("event"))
    return 200, closed


@GatewayHandler.route("GET", "/api/history")
def get_history(handler, payload, params):
    status, events = call_service("GET", f"{HISTORY_SERVICE}/events")
    return status, events


@GatewayHandler.route("GET", "/api/updates/stream")
def stream_updates(handler, payload, params):
    subscriber = _updates_bus.subscribe()

    def iterator():
        try:
            status, auctions_resp = call_service("GET", f"{AUCTION_SERVICE}/auctions")
            status_hist, history_resp = call_service("GET", f"{HISTORY_SERVICE}/events")
            snapshot = {
                "auctions": auctions_resp.get("auctions", []) if status == 200 else [],
                "events": history_resp.get("events", []) if status_hist == 200 else [],
            }
            yield f"event: snapshot\ndata: {json.dumps(snapshot)}\n\n"
            while True:
                try:
                    message = subscriber.get(timeout=15)
                except Empty:
                    yield "event: ping\ndata: {}\n\n"
                    continue
                if message is None:
                    break
                payload = json.dumps(message["data"])
                yield f"event: {message['type']}\ndata: {payload}\n\n"
        finally:
            _updates_bus.unsubscribe(subscriber)

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return StreamingResponse(200, headers, iterator())


def run():
    port = int(os.getenv("GATEWAY_PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), GatewayHandler)
    print(f"Gateway listening on {port}")
    server.serve_forever()


if __name__ == "__main__":
    run()

