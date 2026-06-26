
import sys, json, base64, os
sys.path.insert(0, "C:\\Users\\10074\\Documents\\控制\\src\\twin_protocol")
from identity import AgentIdentity, _canonicalize, _canonicalize_v02

# Generate identity (once, reuse for all tests)
id_test = AgentIdentity("cross-lang-test")
if not id_test.load():
    id_test.generate()

msg = {
    "type": "tool_request",
    "source": "cross-lang-test",
    "tool": "shell.run",
    "params": {"command": "echo cross-lang"},
    "request_id": "cross-lang-001",
    "timestamp": "2026-06-26T00:00:00Z",
    "id": "cross-lang-001"
}

# v0.1 sign (with spaces in JSON)
signed_v01 = id_test.sign(msg)
canon_v01 = _canonicalize(msg, "cross-lang-test").decode().strip()

# v0.2 sign (no-space JSON)
signed_v02 = id_test.sign_v02(msg)
canon_v02 = _canonicalize_v02(msg, "cross-lang-test").decode().strip()

# Also message with payload
msg2 = {
    "type": "message",
    "source": "cross-lang-test",
    "payload": {"text": "Hello cross-lang!"},
    "timestamp": "2026-06-26T00:00:00Z",
    "id": "cross-lang-002"
}
signed_v02b = id_test.sign_v02(msg2)

result = {
    "public_key_raw": base64.b64encode(id_test.public_key).decode(),
    "v01": {"canonical": canon_v01, "signed": signed_v01},
    "v02": {"canonical": canon_v02, "signed": signed_v02},
    "v02b": {"signed": signed_v02b}
}
print(json.dumps(result, ensure_ascii=False))
