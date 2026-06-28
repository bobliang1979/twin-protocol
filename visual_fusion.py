#!/usr/bin/env python3
"""
cua-driver + DeepSeek V4 视觉融合管线

双通道分析:
  通道1: SOM (Set-of-Marks) → 元素索引/坐标/角色 — 快速、结构化
  通道2: DeepSeek V4 视觉 → 语义理解/文字识别/布局分析 — 深度、灵活

输出: 融合后的"这是什么，在哪里，怎么操作"
"""
import json, os, base64, io, time
from typing import Optional

# ── SOM 通道 ──

def extract_som_elements(capture_result: dict) -> list:
    """从 cua-driver capture 结果中提取结构化元素列表."""
    elements = capture_result.get("elements", [])
    if not elements and "image" in capture_result:
        # 只有图片没有 SOM 元素
        return []
    
    parsed = []
    for e in elements:
        parsed.append({
            "index": e.get("element_index", e.get("index")),
            "role": e.get("role", ""),
            "label": e.get("label", "") or e.get("name", ""),
            "bounds": e.get("frame") or e.get("bounds") or e.get("rect"),
        })
    return parsed


# ── 视觉分析提示词模板 ──

VISION_ANALYSIS_PROMPT = """分析这个桌面截图。请输出 JSON 格式的回答：

{
  "summary": "整体画面一句话描述",
  "windows": [
    {"title": "窗口标题", "is_active": true/false, "area": "屏幕占比"}
  ],
  "elements": [
    {"text": "看到的文字内容", "type": "button/input/dialog/等", "location": "在画面中的区域"}
  ],
  "popups": ["检测到的弹窗/对话框描述"],
  "attention": "当前最应该关注的UI元素是什么",
  "readable_content": "画面中所有可读的文本内容"
}

只输出 JSON，不要额外文字。"""


def analyze_screenshot_with_vision(capture_result: dict) -> dict:
    """使用 DeepSeek V4 视觉分析截图.
    
    当模型有原生视觉能力时，capture_result 中包含可直接查看的截图。
    此函数构造分析提示词并让模型自身视觉能力处理。
    """
    elements = extract_som_elements(capture_result)
    
    # 如果有 SOM 元素，作为额外上下文
    som_context = ""
    if elements:
        som_context = "\nUX元素索引:\n" + json.dumps(elements[:20], indent=2, ensure_ascii=False)
        if len(elements) > 20:
            som_context += f"\n... 以及 {len(elements)-20} 个更多元素"
    
    prompt = VISION_ANALYSIS_PROMPT + som_context
    return prompt  # 返回提示词，模型自身视觉能力会处理截图


# ── 动作决策 ──

SOM_VS_VISION_PRIORITY = {
    "Button": "som",        # 按钮用 SOM 索引点击更准
    "CheckBox": "som",
    "RadioButton": "som",
    "MenuItem": "som",
    "Tab": "som",
    "Link": "vision",       # 链接文字需要用视觉确认
    "Text": "vision",       # 文本内容需要用视觉读取
    "Edit": "vision",       # 输入框位置用 SOM，但内容用视觉
    "Dialog": "vision",     # 弹窗检测靠视觉
    "Image": "vision",      # 图片内容靠视觉
    "Custom": "vision",     # 自定义控件靠视觉
    "unknown": "vision",    # 默认用视觉
}


def decide_action(vision_analysis: dict, som_elements: list) -> dict:
    """融合视觉和 SOM 分析结果，决定下一步动作.
    
    返回:
      {"action": "click/type/scroll/wait", "target": "元素描述", 
       "element_index": int 或 None, "coordinate": [x,y] 或 None}
    """
    # 检查是否有弹窗
    popups = vision_analysis.get("popups", [])
    if popups:
        return {
            "action": "handle_popup",
            "popups": popups,
            "priority": "high",
            "detail": f"检测到弹窗: {popups[0]}",
        }
    
    # 检查注意力焦点
    attention = vision_analysis.get("attention", "")
    if attention and som_elements:
        # 尝试在 SOM 中找到匹配元素
        for e in som_elements:
            label = (e.get("label") or "").lower()
            if attention.lower() in label:
                return {
                    "action": "click",
                    "target": attention,
                    "element_index": e["index"],
                    "coordinate": None,
                    "confidence": "high",
                }
    
    return {
        "action": "analyze_only",
        "detail": "视觉分析完成，等待进一步指令",
        "elements_detected": len(som_elements),
        "windows_detected": vision_analysis.get("windows", []),
    }


# ── 视觉循环监控 ──

class VisualMonitor:
    """持续视觉监控：定期截屏 + 视觉分析 + 事件检测."""
    
    def __init__(self, interval_sec: float = 2.0):
        self.interval = interval_sec
        self._last_analysis = None
        self._popup_history = []

    def analyze_frame(self, capture_result: dict) -> dict:
        """分析单帧截图."""
        prompt = analyze_screenshot_with_vision(capture_result)
        # DeepSeek V4 视觉能力会在此处处理截图
        # 返回模型视觉分析的结果
        self._last_analysis = prompt
        return {"prompt": prompt, "timestamp": time.time()}

    def detect_change(self, new_analysis: dict) -> Optional[str]:
        """检测画面是否有重要变化."""
        if self._last_analysis is None:
            return "first_frame"
        
        popups = new_analysis.get("popups", [])
        if popups:
            for p in popups:
                if p not in self._popup_history:
                    self._popup_history.append(p)
                    return f"new_popup: {p}"
        
        return None


# ── 使用示例 ──

"""
使用方式:

  1. 捕获画面:
     computer_use(action='capture', mode='som')
  
  2. 当模型有视觉能力时，画面可见。使用分析提示词:
     [分析此截图] + VISION_ANALYSIS_PROMPT
  
  3. 结合 SOM 元素索引进行精确操作:
     SOM 给出元素索引 → 视觉确认是什么 → 点击/输入

示例流程:
  # 1. 捕获
  cap = computer_use(action='capture', mode='som')
  
  # 2. 视觉分析 (模型自身视觉能力处理)
  analysis = analyze_screenshot(cap)
  
  # 3. 决策
  action = decide_action(analysis, cap.get('elements', []))
  
  # 4. 执行
  if action['element_index']:
      computer_use(action='click', element=action['element_index'])
  elif action['coordinate']:
      computer_use(action='click', coordinate=action['coordinate'])
"""
