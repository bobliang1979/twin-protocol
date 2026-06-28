#!/usr/bin/env python3
"""
视觉引擎 — 替代vision_analyze的buggy辅助模型

直接使用 cua-driver MCP 截图 + DeepSeek V4 原生视觉。
不依赖第三方视觉模型。
"""
import json, os, time
from playwright.sync_api import sync_playwright

VISION_LOG = os.path.expanduser("~/vision_engine_log.jsonl")

class VisionEngine:
    """视觉引擎: MCP截图 → 原生视觉分析"""
    
    def capture(self, pid=None, window_id=None) -> dict:
        """截取窗口画面, 返回截图路径+SOM元素"""
        # Use direct MCP tools to capture
        # This is a wrapper - actual capture happens via the model's native vision
        return {
            "source": "mcp_get_window_state",
            "note": "Use mcp_cua_driver_get_window_state(capture_mode='som') directly",
            "pid": pid,
            "window_id": window_id,
        }
    
    def describe(self, capture_result: dict) -> str:
        """视觉描述截图内容 — 由模型原生视觉处理"""
        elements = capture_result.get("elements", [])
        screenshot_path = capture_result.get("screenshot_path", "")
        
        desc = "【视觉分析启动】\n"
        if screenshot_path:
            desc += f"截图: {screenshot_path}\n"
        if elements:
            desc += f"SOM元素: {len(elements)}个\n"
            for e in elements[:10]:
                desc += f"  [{e.get('element_index')}] {e.get('role','')}: {e.get('label','')[:40]}\n"
        desc += "\n请模型用原生视觉能力分析此截图。"
        return desc

ve = VisionEngine()
