"""
twin_protocol.message — Message types for Twins Protocol v0.1
"""
import json, uuid, datetime
from typing import Optional


def _ts() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


class TwinsMessage:
    """Base message with envelope fields."""

    def __init__(self, msg_type: str, source: str, target: str = "*",
                 payload: dict = None, msg_id: str = None):
        self.id = msg_id or str(uuid.uuid4())
        self.timestamp = _ts()
        self.type = msg_type
        self.source = source
        self.target = target
        self.payload = payload or {}

    def to_dict(self) -> dict:
        d = {
            "type": self.type,
            "source": self.source,
            "target": self.target,
            "timestamp": self.timestamp,
            "id": self.id,
        }
        d.update(self.payload)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def __str__(self):
        return f"[{self.timestamp[-8:]}] {self.source}→{self.target} ({self.type})"


class ToolRequest(TwinsMessage):
    """tool_request — ask the other agent to run a tool."""

    def __init__(self, source: str, tool: str, params: dict,
                 request_id: str = None, target: str = "*"):
        super().__init__("tool_request", source, target,
                         payload={"tool": tool, "params": params,
                                  "request_id": request_id or str(uuid.uuid4())})

    @property
    def request_id(self): return self.payload["request_id"]

    @property
    def tool(self): return self.payload["tool"]

    @property
    def params(self): return self.payload["params"]


class ToolResult(TwinsMessage):
    """tool_result — response to a tool_request."""

    def __init__(self, source: str, request_id: str, tool: str,
                 result, error: str = None, target: str = "*"):
        super().__init__("tool_result", source, target,
                         payload={"request_id": request_id, "tool": tool,
                                  "result": result, "error": error})


class TextMessage(TwinsMessage):
    """message — free-form text communication."""

    def __init__(self, source: str, text: str,
                 reply_to: str = None, target: str = "*"):
        payload = {"text": text}
        if reply_to:
            payload["reply_to"] = reply_to
        super().__init__("message", source, target, payload=payload)


def parse_line(line: str) -> Optional[TwinsMessage]:
    """Parse a JSONL line into a TwinsMessage or None."""
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None
    msg_type = data.get("type")
    source = data.get("source", "?")
    if msg_type == "tool_request":
        return ToolRequest(source, data["tool"], data["params"],
                          request_id=data.get("request_id"), target=data.get("target"))
    if msg_type == "tool_result":
        return ToolResult(source, data["request_id"], data["tool"],
                         data.get("result"), data.get("error"), data.get("target"))
    if msg_type == "message":
        return TextMessage(source, data.get("payload", {}).get("text", ""),
                          data.get("payload", {}).get("reply_to"), data.get("target"))
    return None
