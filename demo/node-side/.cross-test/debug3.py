
import sys, json
sys.path.insert(0, "C:\\Users\\10074\\Documents\\控制\\src\\twin_protocol")
from identity import _canonicalize

msg1 = {
    "type": "tool_request",
    "source": "cross-test-py",
    "tool": "shell.run",
    "params": {"command": "echo hello"},
    "request_id": "cross-test-001",
    "timestamp": "2026-06-26T00:00:00Z",
    "id": "cross-lang-001"
}

canon1 = _canonicalize(msg1, "cross-test-py")
print("C:" + canon1.decode())
