import os
from http.server import HTTPServer

from python_architecture.common.http import JSONRequestHandler


class BiddingHandler(JSONRequestHandler):
    routes = []


@BiddingHandler.route("POST", "/validate")
def validate_bid(handler, payload, params):
    amount = payload.get("amount", 0)
    current = payload.get("current_bid", 0)
    bidder = payload.get("bidder", "")
    if amount <= current:
        return 200, {"ok": False, "message": "Bid must exceed current value"}
    if not bidder:
        return 200, {"ok": False, "message": "Bidder is required"}
    return 200, {"ok": True, "message": "Bid accepted"}


def run():
    port = int(os.getenv("BIDDING_SERVICE_PORT", "8002"))
    server = HTTPServer(("0.0.0.0", port), BiddingHandler)
    print(f"Bidding service listening on {port}")
    server.serve_forever()


if __name__ == "__main__":
    run()

