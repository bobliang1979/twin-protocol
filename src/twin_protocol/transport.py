"""
twin_protocol.transport — HTTP Transport Layer for Twins Protocol v0.2

Allows agents to communicate across machines without sharing a filesystem.
Agent A starts an HTTP server, Agent B sends tool requests/responses via POST.

Usage:
    # Agent A (server)
    python -c "from twin_protocol.transport import serve; serve(port=3739)"

    # Agent B (client)
    python -c "from twin_protocol.transport import request; print(request('http://host:3739', tool='shell.run', params={'command': 'echo hi'}))"
"""
import json, uuid, datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen, ProxyHandler, build_opener
from urllib.error import URLError
from typing import Optional


def _ts() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


# ── Server ──

_handler_instance = None


class _TwinsHandler(BaseHTTPRequestHandler):
    """HTTP handler that processes tool_requests and returns tool_results."""

    def do_GET(self):
        """GET /health — health check endpoint."""
        if self.path == "/health":
            self._respond(200, {
                "status": "alive",
                "agent": "hermes",
                "protocol": "Twins Protocol v0.2",
                "transport": "HTTP",
                "tools": ["shell.run", "file.read", "file.write", "memory.read", "skill_view"],
            })
        elif self.path == "/capabilities":
            self._respond(200, {
                "agent": "hermes",
                "protocol": "Twins Protocol v0.2",
                "transport": "HTTP",
                "tools": {
                    "shell.run": {"description": "Execute shell command", "params": {"command": "string", "timeout": "int?"}},
                    "file.read": {"description": "Read file content", "params": {"path": "string"}},
                    "file.write": {"description": "Write file content", "params": {"path": "string", "content": "string"}},
                }
            })
        else:
            self._respond(404, {"error": "Not found"})

    def do_POST(self):
        global _handler_instance
        # Accept both / and /twins endpoints
        if self.path not in ("/", "/twins"):
            self._respond(404, {"error": f"Not found: {self.path}"})
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"

        try:
            msg = json.loads(body)
        except json.JSONDecodeError:
            self._respond(400, {"error": "Invalid JSON"})
            return

        msg_type = msg.get("type", "")
        source = msg.get("source", "remote")

        if msg_type == "tool_request":
            tool = msg.get("tool", "")
            params = msg.get("params", {})
            req_id = msg.get("request_id", str(uuid.uuid4())[:12])

            # Dispatch to registered handler
            if _handler_instance and _handler_instance._handler:
                result = _handler_instance._handler(source, tool, params)
                response = {
                    "type": "tool_result",
                    "request_id": req_id,
                    "tool": tool,
                    "source": "twins-server",
                    "target": source,
                    "result": result,
                    "error": result.get("error"),
                    "_ts": _ts(),
                }
            else:
                response = {
                    "type": "tool_result",
                    "request_id": req_id,
                    "tool": tool,
                    "source": "twins-server",
                    "target": source,
                    "result": None,
                    "error": "No handler registered",
                    "_ts": _ts(),
                }
            self._respond(200, response)

        elif msg_type == "ping":
            self._respond(200, {"type": "pong", "source": "twins-server", "_ts": _ts()})

        else:
            self._respond(400, {"error": f"Unknown type: {msg_type}"})

    def _respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        pass  # Suppress default HTTP server logs


class TwinsServer:
    """HTTP server that receives tool_requests from remote agents."""

    def __init__(self, host="0.0.0.0", port=3739, handler=None):
        """
        handler: callable(source, tool, params) -> dict
                 Should return {"stdout": ..., "error": ...} or similar.
        """
        global _handler_instance
        self.host = host
        self.port = port
        self._handler = handler
        self._server = None
        _handler_instance = self

    def start(self):
        """Start the server (blocking)."""
        self._server = HTTPServer((self.host, self.port), _TwinsHandler)
        print(f"🧬 Twins HTTP Transport listening on http://{self.host}:{self.port}")
        try:
            self._server.serve_forever()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        if self._server:
            self._server.shutdown()
            print("🧬 Twins HTTP Transport stopped")


def serve(host="0.0.0.0", port=3739, handler=None):
    """Convenience function to start the Twins HTTP Transport server."""
    server = TwinsServer(host=host, port=port, handler=handler)
    server.start()


# ── Client ──

def send(url: str, msg: dict, timeout: int = 30) -> Optional[dict]:
    """Send a Twins Protocol message to a remote agent via HTTP POST."""
    try:
        data = json.dumps(msg, ensure_ascii=False).encode("utf-8")
        req = Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "twins-protocol/0.2",
            },
            method="POST",
        )
        # Bypass system proxy (common on Windows)
        proxy_handler = ProxyHandler({})
        opener = build_opener(proxy_handler)
        with opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except URLError as e:
        return {"type": "error", "error": str(e.reason)}
    except Exception as e:
        return {"type": "error", "error": str(e)}


def request(url: str, tool: str, params: dict,
            request_id: str = None, source: str = "twins-client",
            timeout: int = 30) -> Optional[dict]:
    """Send a tool_request to a remote agent and return the tool_result."""
    msg = {
        "type": "tool_request",
        "source": source,
        "request_id": request_id or str(uuid.uuid4())[:12],
        "tool": tool,
        "params": params,
    }
    return send(url, msg, timeout=timeout)


def ping(url: str, timeout: int = 5) -> Optional[dict]:
    """Check if a remote agent is alive."""
    return send(url, {"type": "ping", "source": "twins-client"}, timeout=timeout)
