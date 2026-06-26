# Changelog

## [0.1.0] — 2026-06-26

### Added
- 🧬 **Twins Protocol v0.1**: File-based agent-to-agent communication protocol
- 📦 **Python package** (`pip install twin-protocol`): `twins` CLI with init/demo commands
- 📦 **Node.js package** (`npm install @bobliang1979/twin-protocol`): CLI with solo mode
- 🔐 **Ed25519 identity**: Every message signed, cross-language verification (Python↔Node.js)
- 🌐 **HTTP Transport Layer v0.2**: Cross-machine agent communication via POST /twins
- 🖥️ **Demo Dashboard**: Real-time visualization of agent communication
- 🎬 **Solo Mode** (`twins solo`): Single-user demo with simulated agent pair
- 🧪 **Test suite**: 13+ tests for review.py and standby.py
- 🔧 **MCP Adapter P0**: MCP server for LangChain/CrewAI integration
- 📋 **Code Review Protocol P1**: Structured review workflow for agent pairs
- 🔄 **Hot Standby Mode P2**: Failover agent pair
- 🐳 **Docker Compose**: One-command deployment
- 🤖 **GitHub Actions CI**: Automated compliance tests

### Fixed
- `review.py` datetime import error
- `npx.cmd` Windows compatibility (subprocess on MSYS bash)
- `docker-compose.yml` restoration after cleanup
- `cli.js` entry point creation
- `codex_outbox.jsonl` git tracking (added to .gitignore)
- Dashboard `serveOutbox` returning JSON array instead of JSONL
