import os
import threading
import time
from http.server import HTTPServer

from python_architecture.common.http import JSONRequestHandler


_events = []
_lock = threading.Lock()


class HistoryHandler(JSONRequestHandler):
    routes = []


@HistoryHandler.route("POST", "/events")
def record_event(handler, payload, params):
    event = {
        "auction_id": payload.get("auction_id"),
        "event_type": payload.get("event_type"),
        "payload": payload.get("payload", ""),
        "timestamp": time.time(),
    }
    with _lock:
        _events.append(event)
    return 201, {"event": event}


@HistoryHandler.route("GET", "/events")
def list_events(handler, payload, params):
    with _lock:
        events = list(_events)
    return 200, {"events": events}


def run():
    port = int(os.getenv("HISTORY_SERVICE_PORT", "8003"))
    server = HTTPServer(("0.0.0.0", port), HistoryHandler)
    print(f"History service listening on {port}")
    server.serve_forever()


if __name__ == "__main__":
    run()

