# computer-control

Cross-platform desktop automation stack with cascade vision pipeline.

## Architecture

```
Capture Engine -> UIA Tree -> OCR -> DSV4 Vision -> SOM Grounding -> Action
     |                                                  |
     +------- 5-level fallback chain -------------------+
```

## Components

- **capture/engine.py** - Multi-backend screen capture (DXGI/mss/PIL/ctypes)
- **ui_automation/windeep.py** - Native Win32 control via ctypes
- **ui_automation/uia_bridge.py** - UI Automation tree wrapper
- **vision/som.py** - Set-of-Mark visual grounding
- **vision/pipeline.py** - Cascade vision pipeline orchestrator
- **handler/control_panel.py** - Direct Win32 Control Panel interaction
