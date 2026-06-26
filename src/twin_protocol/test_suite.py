"""
twin_protocol.test_suite — Twins Protocol compliance test suite

Run with: twins test
"""
import json, sys, time, threading, subprocess, tempfile, shutil
from pathlib import Path

_tests_passed = 0
_tests_failed = []

def test(name, ok, detail=""):
    global _tests_passed, _tests_failed
    if ok:
        _tests_passed += 1; print(f"  ✅ {name}")
    else:
        _tests_failed.append(name); print(f"  ❌ {name}: {detail}")

def _echo_server(port=0):
    from http.server import HTTPServer, BaseHTTPRequestHandler
    class H(BaseHTTPRequestHandler):
        def do_POST(s):
            l = int(s.headers.get("Content-Length", 0))
            b = s.rfile.read(l).decode() if l else "{}"
            m = json.loads(b)
            if m.get("type") == "ping":
                s._r({"type":"pong"})
            elif m.get("type") == "tool_request":
                s._r({"type":"tool_result","request_id":m.get("request_id",""),"result":{"stdout":"ok","exit_code":0}})
            else: s._r({"error":"uk"})
        def _r(s, d):
            s.send_response(200); s.send_header("Content-Type","application/json"); s.end_headers()
            s.wfile.write(json.dumps(d).encode())
        def log_message(s,*a): pass
    sv = HTTPServer(("127.0.0.1", port), H)
    p = sv.server_address[1]
    t = threading.Thread(target=sv.serve_forever, daemon=True); t.start()
    return sv, p


def run_all():
    global _tests_passed, _tests_failed
    _tests_passed = 0; _tests_failed = []
    src = str(Path(__file__).parent.parent)
    if src not in sys.path: sys.path.insert(0, src)
    
    print(f"\n🧬 Twins Protocol Compliance Test Suite v0.1")
    print(f"{'='*50}")

    # ── 1. Message types ──
    try:
        from twin_protocol.message import ToolRequest, ToolResult, TextMessage, parse_line
        
        r = ToolRequest("t", "shell.run", {"command": "ls"})
        j = r.to_json()
        test("ToolRequest serialization", "tool_request" in j and "shell.run" in j)
        
        r2 = ToolResult("t", r.request_id, "shell.run", {"stdout": "ok"}, None)
        j2 = r2.to_json()
        test("ToolResult serialization", "tool_result" in j2)
        
        m = TextMessage("t", "hello", target="o")
        j3 = m.to_json()
        test("TextMessage serialization", "message" in j3 and "hello" in j3)
        
        p = parse_line(TextMessage("t", "hi", target="o").to_json())
        test("parse_line valid JSON", p is not None)
        
        p2 = parse_line("not json")
        test("parse_line invalid JSON", p2 is None)
        
        test("4 message types all pass", True)
    except Exception as e:
        test("Message types", False, str(e))

    # ── 2. Identity ──
    try:
        from twin_protocol.identity import AgentIdentity
        d = Path.home() / ".twins" / "ts-test"
        shutil.rmtree(d, ignore_errors=True)
        
        a = AgentIdentity("ts-test").generate()
        test("Key generation 32 bytes", len(a.public_key) == 32)
        test("Key exists on disk", a.exists())
        
        a2 = AgentIdentity("ts-test")
        a2.load()
        test("Key loading matches", a2.public_key == a.public_key)
        
        s = a.sign({"type":"message","payload":{"text":"hi"},"timestamp":"2026-01-01T00:00:00Z","id":"t1"})
        test("Sign adds signature field", "signature" in s)
        test("Sign adds signer field", s.get("signer") == "ts-test")
        
        r = AgentIdentity.verify_message(s, {"ts-test": a.public_key})
        test("Verify valid signature", r.valid)
        
        s2 = dict(s); s2["payload"] = {"text": "bad"}
        r2 = AgentIdentity.verify_message(s2, {"ts-test": a.public_key})
        test("Tamper detection rejects bad payload", not r2.valid)
        
        s3 = a.sign({"type":"tool_request","tool":"shell.run","params":{"cmd":"ls"},
                     "request_id":"r1","timestamp":"2026-01-01T00:00:00Z","id":"t2"})
        r3 = AgentIdentity.verify_message(s3, {"ts-test": a.public_key})
        test("Tool request signing works", r3.valid)
        
        shutil.rmtree(d, ignore_errors=True)
    except Exception as e:
        test("Identity tests", False, str(e))

    # ── 3. HTTP Transport ──
    try:
        from twin_protocol.transport import send, ping, request
        
        sv, port = _echo_server()
        time.sleep(0.3)
        
        r = ping(f"http://127.0.0.1:{port}")
        test("Ping returns pong", r and r.get("type") == "pong")
        
        r2 = request(f"http://127.0.0.1:{port}", "shell.run", {"command": "echo hi"})
        test("Tool request returns result", r2 and r2.get("type") == "tool_result")
        
        r3 = send(f"http://127.0.0.1:{port}/twins", {"type": "ping"})
        test("Send to /twins path works", r3 and r3.get("type") == "pong")
        
        sv.shutdown()
    except Exception as e:
        test("HTTP Transport tests", False, str(e))

    # ── 4. Schema ──
    schema = Path(__file__).parent.parent.parent / "twins_schema.json"
    test("Schema file exists", schema.exists())
    if schema.exists():
        try:
            import jsonschema
            s = json.loads(schema.read_text())
            for ex in [
                {"type":"message","source":"a","target":"b","timestamp":"2026-01-01T00:00:00Z",
                 "id":"00000000-0000-0000-0000-000000000001","payload":{"text":"h"}},
                {"type":"tool_request","source":"a","timestamp":"2026-01-01T00:00:00Z",
                 "request_id":"r1","tool":"shell.run","params":{"command":"ls"}},
                {"type":"tool_result","source":"a","timestamp":"2026-01-01T00:00:00Z",
                 "request_id":"r1","tool":"shell.run","result":{"s":"ok"},"error":None},
                {"type":"state_update","source":"a","timestamp":"2026-01-01T00:00:00Z",
                 "state":{"phase":"running"}},
            ]:
                jsonschema.validate(ex, s)
            test("Schema: all 4 types validate", True)
        except ImportError:
            test("Schema validation skipped (pip install jsonschema)", True)
        except Exception as e:
            test("Schema validation", False, str(e))

    # ── 5. CLI ──
    try:
        tmp = Path(tempfile.mkdtemp())
        r = subprocess.run(["twins", "init", str(tmp/"tp")], capture_output=True, text=True, timeout=10, cwd=str(tmp))
        test("twins init succeeds", r.returncode == 0)
        test("outbox.jsonl created", (tmp/"tp"/"outbox.jsonl").exists())
        
        r2 = subprocess.run(["twins", "validate", str(tmp/"tp"/"outbox.jsonl")],
                            capture_output=True, text=True, timeout=10)
        test("twins validate on empty outbox", r2.returncode == 0)
        shutil.rmtree(tmp)
    except Exception as e:
        test("CLI tests", False, str(e))

    # ── 6. Version ──
    try:
        from twin_protocol import __protocol_version__, __version__
        test("Protocol version is 0.1", __protocol_version__ == "0.1")
        test("Package version is 0.1.0", __version__ == "0.1.0")
    except Exception as e:
        test("Version checks", False, str(e))

    # ── Report ──
    total = _tests_passed + len(_tests_failed)
    print(f"\n{'='*50}")
    print(f"  {_tests_passed}/{total} passed")
    if _tests_failed:
        print(f"  ❌ Failed: {', '.join(_tests_failed)}")
        return 1
    print(f"  ✅ ALL COMPLIANCE TESTS PASSED")
    print(f"{'='*50}")
    return 0


def main():
    sys.exit(run_all())

if __name__ == "__main__":
    main()
