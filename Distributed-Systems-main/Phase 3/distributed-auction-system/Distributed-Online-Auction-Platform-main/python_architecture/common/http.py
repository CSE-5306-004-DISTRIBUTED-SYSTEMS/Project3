import json
from http.server import BaseHTTPRequestHandler
from typing import Dict, Iterable, Tuple, Union


class StreamingResponse:
    """Represents a streaming HTTP response such as an SSE feed."""

    def __init__(self, status: int, headers: Dict[str, str], iterator: Iterable[Union[str, bytes]]):
        self.status = status
        self.headers = headers
        self.iterator = iterator


class JSONRequestHandler(BaseHTTPRequestHandler):
    routes = []

    def do_GET(self):
        self.handle_request("GET")

    def do_POST(self):
        self.handle_request("POST")

    def do_PUT(self):
        self.handle_request("PUT")

    def do_DELETE(self):
        self.handle_request("DELETE")

    def handle_request(self, method: str):
        path = self.path.split("?")[0]
        handler, params = self._match_route(method, path)
        if handler is None:
            self.send_error(404, "Not Found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length) if length else b""
            payload = json.loads(body.decode("utf-8")) if body else {}
            response = handler(self, payload, params)
            if isinstance(response, StreamingResponse):
                self.send_response(response.status)
                for key, value in response.headers.items():
                    self.send_header(key, value)
                self.end_headers()
                try:
                    for chunk in response.iterator:
                        if isinstance(chunk, str):
                            chunk = chunk.encode("utf-8")
                        self.wfile.write(chunk)
                        self.wfile.flush()
                except BrokenPipeError:
                    pass
                finally:
                    close_iter = getattr(response.iterator, "close", None)
                    if callable(close_iter):
                        try:
                            close_iter()
                        except Exception:
                            pass
                return

            status, payload_body = self._normalize_response(response)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload_body).encode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
        except Exception as exc:
            self.send_error(500, f"Internal error: {exc}")

    @classmethod
    def _match_route(cls, method: str, path: str):
        for registered_method, parts, handler in cls.routes:
            if registered_method != method:
                continue
            candidate = path.strip("/").split("/") if path.strip("/") else []
            if len(candidate) != len(parts):
                continue
            params = {}
            match = True
            for idx, part in enumerate(parts):
                if part.startswith("<") and part.endswith(">"):
                    params[part[1:-1]] = candidate[idx]
                elif part != candidate[idx]:
                    match = False
                    break
            if match:
                return handler, params
        return None, {}

    @classmethod
    def route(cls, method: str, path: str):
        def decorator(func):
            parts = path.strip("/").split("/") if path.strip("/") else []
            cls.routes.append((method, parts, func))
            return func

        return decorator

    def log_message(self, format: str, *args):  # noqa: D401 - suppress noisy logs
        """Silence default stderr logging to keep test output clean."""
        return

    @staticmethod
    def _normalize_response(response) -> Tuple[int, Dict]:
        if isinstance(response, tuple) and len(response) == 2:
            status, payload_body = response
            if not isinstance(payload_body, dict):
                raise TypeError("Handler must return a (status, dict) pair")
            return int(status), payload_body
        raise TypeError(
            "Handlers must return either StreamingResponse or (status, dict)"
        )

