import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib import request

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://gateway:8000")


class FrontendHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/"):
            self.forward_request("GET")
        else:
            if self.path == "/":
                self.path = "/static/index.html"
            return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self.forward_request("POST")
        else:
            self.send_error(405, "Method not allowed")

    def forward_request(self, method: str):
        target = f"{GATEWAY_URL}{self.path}"
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length) if length else None
        req = request.Request(target, data=data, method=method)
        req.add_header("Content-Type", self.headers.get("Content-Type", "application/json"))
        try:
            with request.urlopen(req) as resp:
                self.send_response(resp.status)
                for key, value in resp.headers.items():
                    if key.lower() == "transfer-encoding":
                        continue
                    self.send_header(key, value)
                self.end_headers()
                content_type = resp.headers.get("Content-Type", "")
                try:
                    chunk = resp.read(8192)
                    while chunk:
                        self.wfile.write(chunk)
                        if "text/event-stream" in content_type:
                            self.wfile.flush()
                        chunk = resp.read(8192)
                except BrokenPipeError:
                    pass
        except Exception as exc:
            self.send_error(502, f"Gateway error: {exc}")


def run():
    port = int(os.getenv("FRONTEND_PORT", "8080"))
    os.chdir(os.path.dirname(__file__))
    server = ThreadingHTTPServer(("0.0.0.0", port), FrontendHandler)
    print(f"Frontend listening on {port}")
    server.serve_forever()


if __name__ == "__main__":
    run()

