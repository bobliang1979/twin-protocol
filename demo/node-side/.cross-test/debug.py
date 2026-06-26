
import sys, json, hashlib, base64
sys.path.insert(0, "C:\\Users\\10074\\Documents\\控制\\src\\twin_protocol")
from identity import AgentIdentity

# Create identity
id_test = AgentIdentity("cross-test-py")
id_test.generate()

# Sign a message with payload
msg = {
    "type": "tool_request",
    "source": "cross-test-py",
    "tool": "shell.run",
    "params": {"command": "echo hello"},
    "request_id": "cross-test-001",
    "timestamp": "2026-06-26T00:00:00Z",
    "id": "cross-lang-001"
}

# Access the internal _canonicalize
canonical = id_test._canonicalize(msg, "cross-test-py")
print("PYTHON_CANONICAL:" + canonical.decode())

# What does payload look like?
print("PYTHON_PAYLOAD:" + json.dumps(msg.get("payload")))

# What does full msg look like?
print("PYTHON_MSG:" + json.dumps(msg, sort_keys=True))

# Also get the signed version
signed = id_test.sign(msg)
print("PYTHON_SIGNED:" + json.dumps(signed, sort_keys=True))
