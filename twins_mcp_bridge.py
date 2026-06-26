"""
twins_mcp_bridge.py — MCP ↔ Twins Protocol Adapter

MCP (Model Context Protocol) is the standard for AI-to-tool.
Twins Protocol is the standard for AI-to-AI.

This bridge connects them:
  • Any Twin agent can call any MCP tool
  • Any MCP client can discover Twin agents

Usage:
    # Wrap an MCP server as a Twin agent
    python twins_mcp_bridge.py --serve mcp-server.js

    # List available MCP tools
    python twins_mcp_bridge.py --list

    # Call an MCP tool via Twins Protocol
    python twins_mcp_bridge.py --call <tool_name> '<params-json>'
"""
import sys, json, subprocess, uuid, os, time
from pathlib import Path
from typing import Optional


MCP_SERVERS = {
    "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem"],
        "description": "File system operations"
    },
    "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "description": "GitHub API integration"
    },
    "postgres": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres"],
        "description": "PostgreSQL database queries"
    },
    "playwright": {
        "command": "npx",
        "args": ["-y", "@playwright/mcp"],
        "description": "Browser automation"
    },
    "sequential-thinking": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        "description": "Structured reasoning"
    },
}


class MCPBridge:
    """Bridge between MCP servers and Twins Protocol."""

    def __init__(self):
        self._processes = {}
        self._tools = {}

    def start_server(self, name: str) -> bool:
        """Start an MCP server and discover its tools."""
        if name not in MCP_SERVERS:
            print(f"❌ Unknown MCP server: {name}")
            return False

        config = MCP_SERVERS[name]
        print(f"🧬 Starting MCP server: {name} ({config['description']})")

        try:
            proc = subprocess.Popen(
                [config["command"]] + config["args"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self._processes[name] = proc

            # Send initialize request
            req_id = str(uuid.uuid4())[:8]
            init_msg = json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "twins-mcp-bridge", "version": "0.1.0"}
                }
            })
            proc.stdin.write(init_msg + "\n")
            proc.stdin.flush()

            # Read response
            response = proc.stdout.readline()
            if not response:
                print(f"❌ No response from {name}")
                return False

            # Send initialized notification
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            proc.stdin.flush()

            # List tools
            list_id = str(uuid.uuid4())[:8]
            list_msg = json.dumps({
                "jsonrpc": "2.0",
                "id": list_id,
                "method": "tools/list",
                "params": {}
            })
            proc.stdin.write(list_msg + "\n")
            proc.stdin.flush()

            # Read tools list
            tools_response = proc.stdout.readline()
            if tools_response:
                tools_data = json.loads(tools_response)
                if "result" in tools_data and "tools" in tools_data["result"]:
                    tools = tools_data["result"]["tools"]
                    for tool in tools:
                        tool_name = f"{name}:{tool['name']}"
                        self._tools[tool_name] = {
                            "server": name,
                            "name": tool["name"],
                            "description": tool.get("description", ""),
                            "inputSchema": tool.get("inputSchema", {}),
                        }
                    print(f"  ✅ {len(tools)} tools registered from {name}")
                    return True

            print(f"  ⚠️ Server started but no tools listed")
            return True

        except Exception as e:
            print(f"  ❌ Failed to start {name}: {e}")
            return False

    def list_tools(self) -> dict:
        """List all available tools across all MCP servers."""
        return self._tools

    def call_tool(self, tool_name: str, params: dict) -> Optional[dict]:
        """Call an MCP tool via Twins Protocol tool_request format."""
        if tool_name not in self._tools:
            return {"error": f"Tool not found: {tool_name}", "exit_code": -1}

        info = self._tools[tool_name]
        server_name = info["server"]
        proc = self._processes.get(server_name)

        if not proc:
            return {"error": f"Server not running: {server_name}", "exit_code": -1}

        try:
            req_id = str(uuid.uuid4())[:8]
            call_msg = json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/call",
                "params": {
                    "name": info["name"],
                    "arguments": params
                }
            })
            proc.stdin.write(call_msg + "\n")
            proc.stdin.flush()

            # Read result
            response = proc.stdout.readline()
            if not response:
                return {"error": "No response from MCP server", "exit_code": -1}

            result = json.loads(response)
            if "result" in result:
                mcp_result = result["result"]
                content = mcp_result.get("content", [])
                # Convert MCP content to Twins tool_result format
                stdout_parts = []
                for item in content:
                    if item.get("type") == "text":
                        stdout_parts.append(item.get("text", ""))
                return {
                    "stdout": "\n".join(stdout_parts),
                    "content": mcp_result,
                    "exit_code": 0,
                    "tool": tool_name
                }
            elif "error" in result:
                return {"error": result["error"].get("message", "MCP error"), "exit_code": -1}
            else:
                return {"error": "Unknown MCP response", "exit_code": -1}

        except Exception as e:
            return {"error": str(e), "exit_code": -1}

    def stop_all(self):
        """Stop all MCP servers."""
        for name, proc in self._processes.items():
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"  Stopped {name}")
            except:
                proc.kill()

    def serve(self, outbox_path: str = None):
        """Run as a persistent Twins agent — processes tool_requests from outbox."""
        if not outbox_path:
            outbox_path = str(Path.home() / "Desktop/hermes_codex_bridge/twins_mcp_outbox.jsonl")

        outbox = Path(outbox_path)
        print(f"🧬 Twins MCP Bridge listening on {outbox_path}")
        print(f"  {len(self._tools)} MCP tools available")

        processed = set()
        try:
            while True:
                if outbox.exists():
                    with open(outbox, "r") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                msg = json.loads(line)
                                msg_id = msg.get("id", "")
                                if msg_id in processed:
                                    continue
                                if msg.get("type") == "tool_request":
                                    tool = msg.get("tool", "")
                                    params = msg.get("params", {})
                                    result = self.call_tool(tool, params)
                                    response = {
                                        "type": "tool_result",
                                        "request_id": msg.get("request_id", ""),
                                        "tool": tool,
                                        "source": "mcp-bridge",
                                        "target": msg.get("source", "unknown"),
                                        "result": result,
                                        "error": result.get("error") if result else "Tool not found",
                                        "_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                    }
                                    # Append result back to outbox
                                    with open(outbox, "a") as f:
                                        f.write(json.dumps(response, ensure_ascii=False) + "\n")
                                    processed.add(msg_id)
                            except json.JSONDecodeError:
                                pass
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.stop_all()


def main():
    bridge = MCPBridge()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python twins_mcp_bridge.py --list                 # List available MCP servers")
        print("  python twins_mcp_bridge.py --serve [server...]    # Start bridge (default: all)")
        print("  python twins_mcp_bridge.py --call <tool> <params> # Single tool call")
        print()
        print("Available MCP servers:")
        for name, cfg in MCP_SERVERS.items():
            print(f"  {name}: {cfg['description']}")
        return

    if sys.argv[1] == "--list":
        print("Available MCP server types:")
        for name, cfg in MCP_SERVERS.items():
            print(f"  {name:<20} {cfg['description']}")

    elif sys.argv[1] == "--serve":
        servers = sys.argv[2:] if len(sys.argv) > 2 else list(MCP_SERVERS.keys())
        for s in servers:
            bridge.start_server(s)
        bridge.serve()

    elif sys.argv[1] == "--call":
        if len(sys.argv) < 4:
            print("Usage: python twins_mcp_bridge.py --call <tool_name> '<json-params>'")
            return
        tool = sys.argv[2]
        params = json.loads(sys.argv[3])
        server_name = tool.split(":")[0]
        bridge.start_server(server_name)
        result = bridge.call_tool(tool, params)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        bridge.stop_all()


if __name__ == "__main__":
    main()
