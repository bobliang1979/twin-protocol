
import sys, json, hashlib, base64
sys.path.insert(0, "C:\\Users\\10074\\Documents\\控制\\src\\twin_protocol")
from identity import AgentIdentity, _canonicalize

# Create identity
id_test = AgentIdentity("cross-test-py")
id_test.generate()

# Sign a message WITHOUT payload (to isolate)
msg1 = {
    "type": "tool_request",
    "source": "cross-test-py",
    "tool": "shell.run",
    "params": {"command": "echo hello"},
    "request_id": "cross-test-001",
    "timestamp": "2026-06-26T00:00:00Z",
    "id": "cross-lang-001"
}

canonical1 = _canonicalize(msg1, "cross-test-py")
print("CANON1:" + canonical1.decode())

# Also sign it and get the full signed message
signed1 = id_test.sign(msg1)
print("SIGNED1:" + json.dumps(signed1, sort_keys=True))

# Check what signer value is used
print("SIGNER1:" + id_test.name)

# Test 2: message WITH payload
msg2 = {
    "type": "message",
    "source": "cross-test-py",
    "payload": {"text": "hello world"},
    "timestamp": "2026-06-26T00:00:00Z",
    "id": "cross-lang-002"
}
canonical2 = _canonicalize(msg2, "cross-test-py")
print("CANON2:" + canonical2.decode())
