"""
twins_client.py — Twins Protocol HTTP Client for Python
Call any Codex++ tool via HTTP Transport.

Usage:
    python twins_client.py js.eval '{"code": "1+1"}'
    python twins_client.py shell.run '{"command": "echo hello"}'
    python twins_client.py workspace.read '{"path": "README.md"}'
"""

import requests
import json
import sys
import uuid

SERVER_URL = "http://localhost:3738"

def call_tool(tool_name, params, server=SERVER_URL):
    """Call a tool on the remote agent and return the result."""
    request = {
        "type": "tool_request",
        "source": "hermes",
        "request_id": str(uuid.uuid4()),
        "tool": tool_name,
        "params": params
    }
    
    try:
        resp = requests.post(f"{server}/twins", json=request, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        
        if result.get("error"):
            print(f"❌ Error: {result['error']}")
            return None
        
        return result.get("result")
    
    except requests.exceptions.Timeout:
        print("❌ Timeout: server did not respond within 30s")
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection refused: {server}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    return None

def check_health(server=SERVER_URL):
    """Check if the remote agent is alive."""
    try:
        resp = requests.get(f"{server}/health", timeout=5)
        return resp.json()
    except:
        return {"status": "unreachable"}

def list_capabilities(server=SERVER_URL):
    """List all tools available on the remote agent."""
    try:
        resp = requests.get(f"{server}/capabilities", timeout=5)
        return resp.json()
    except:
        return {"error": "unreachable"}

def repl(server=SERVER_URL):
    """Interactive REPL for calling tools."""
    print(f"🧬 Twins Protocol REPL — connected to {server}")
    print("Type 'help' for commands, 'quit' to exit")
    print()
    
    while True:
        try:
            cmd = input("twins> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        
        if cmd in ("quit", "exit", "q"):
            break
        elif cmd == "help":
            print("Commands:")
            print("  health          — check agent health")
            print("  caps            — list available tools")
            print("  js <code>       — run js.eval")
            print("  shell <cmd>     — run shell.run")
            print("  read <path>     — run workspace.read")
            print("  quit            — exit")
        elif cmd == "health":
            h = check_health(server)
            print(json.dumps(h, indent=2))
        elif cmd == "caps":
            c = list_capabilities(server)
            for tool, info in c.get("tools", {}).items():
                print(f"  {tool}: {info.get('description', '')}")
        elif cmd.startswith("js "):
            code = cmd[3:]
            result = call_tool("js.eval", {"code": code}, server)
            if result:
                print(result.get("stdout", result))
        elif cmd.startswith("shell "):
            command = cmd[6:]
            result = call_tool("shell.run", {"command": command}, server)
            if result:
                print(result.get("stdout", result))
        elif cmd.startswith("read "):
            path = cmd[5:]
            result = call_tool("workspace.read", {"path": path}, server)
            if result:
                content = result.get("content", "")
                print(f"({result.get('size', 0)} bytes)")
                print(content[:500] + ("..." if len(content) > 500 else ""))
        else:
            print(f"Unknown: {cmd}")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        # CLI mode: python twins_client.py <tool> <params-json>
        tool = sys.argv[1]
        params = json.loads(sys.argv[2])
        server = sys.argv[3] if len(sys.argv) >= 4 else SERVER_URL
        result = call_tool(tool, params, server)
        if result:
            print(json.dumps(result, indent=2, ensure_ascii=False))
    elif len(sys.argv) == 2 and sys.argv[1] == "repl":
        repl()
    elif len(sys.argv) == 2 and sys.argv[1] == "health":
        print(json.dumps(check_health(), indent=2))
    else:
        print("Usage:")
        print("  python twins_client.py <tool> <params-json> [server-url]")
        print("  python twins_client.py repl")
        print("  python twins_client.py health")
        print()
        print("Examples:")
        print('  python twins_client.py js.eval \'{"code": "1+1"}\'')
        print('  python twins_client.py shell.run \'{"command": "echo hi"}\'')
        print('  python twins_client.py repl')
