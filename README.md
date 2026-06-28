# Twin Protocol v2.20 — Cognitive Desktop Control

A production-grade computer control system with multi-model parallel inference, cascade vision pipeline, cognitive energy management, and dual-agent architecture.

## Components

- **brain.py** — Multi-model decision engine (Gemini + ChatGLM + Qwen + Copilot)
- **phase2_engine.py** — Action executor with failure recovery + DSV4 adjudication
- **phase3_engine.py** — Dual-agent (Observer S3 + Actor S0) + cross-session memory
- **desktop_organizer.py** — Real-world file organization with rollback
- **butler.py** — Continuous desktop monitoring and automation
- **vision_engine.py** — MCP screenshot + DeepSeek V4 vision analysis
- **cascade_capture.py** — Multi-backend screenshot with auto-degradation
- **visual_fusion.py** — SOM + vision dual-channel UI understanding

## Requirements

- Windows 10+
- Python 3.10+
- cua-driver 0.6.8+
- Tabbit browser (for multi-model inference)
- DeepSeek V4 (for native vision)

## License

MIT
