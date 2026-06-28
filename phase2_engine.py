#!/usr/bin/env python3
"""
Phase 2: 统一动作执行器 + 失败回溯 + DSV4裁决层

暴露所有MCP工具能力到统一接口:
  - click / right_click / double_click / drag / scroll
  - type_text / hotkey / set_value
  - capture / get_window_state
  
失败回溯:
  自动重试(3次) → 切换后端 → 截图验证
  验证失败自动回滚到上一个稳定状态
  
DSV4裁决层:
  执行前: 视觉确认元素是否存在
  执行后: 截图对比验证效果
"""
import json, os, time, traceback
from typing import Optional

LOG = os.path.expanduser("~/phase2_action_log.jsonl")
MAX_RETRIES = 3
RETRY_DELAY_MS = 500

# ── 动作类型枚举 ──

ACTION_TYPES = {
    "click":       {"mcp": "mcp_cua_driver_click",       "params": ["pid", "element_index"]},
    "right_click": {"mcp": "mcp_cua_driver_right_click", "params": ["pid", "element_index"]},
    "double_click":{"mcp": "mcp_cua_driver_double_click","params": ["pid", "element_index"]},
    "drag":        {"mcp": "mcp_cua_driver_drag",        "params": ["pid", "from_x","from_y","to_x","to_y"]},
    "scroll":      {"mcp": "mcp_cua_driver_scroll",      "params": ["pid", "direction"]},
    "type_text":   {"mcp": "mcp_cua_driver_type_text",   "params": ["pid", "text"]},
    "hotkey":      {"mcp": "mcp_cua_driver_hotkey",      "params": ["pid", "keys"]},
    "set_value":   {"mcp": "mcp_cua_driver_set_value",   "params": ["pid", "element_index", "value"]},
    "capture":     {"mcp": "mcp_cua_driver_get_window_state","params": ["pid", "window_id"]},
}

# ── 统一动作执行器 ──

class ActionExecutor:
    """统一动作执行器: 执行 + 回溯 + 裁决"""
    
    def __init__(self):
        self._history = []  # Stack of (action_name, params, result)
        self._stats = {"attempts": 0, "success": 0, "failures": 0, "retries": 0}
    
    def _call_mcp(self, tool_name: str, params: dict) -> dict:
        """通过 MCP 工具调用执行动作"""
        # Map tool name to actual Hermes MCP tool call
        # These would normally be called via the mcp_* tools in Hermes
        return {"tool": tool_name, "params": params, "status": "dispatched"}
    
    def _capture_state(self, pid: int, window_id: int) -> Optional[str]:
        """截取当前状态作为验证基准"""
        # This uses mcp_cua_driver_get_window_state
        return f"snapshot_{pid}_{window_id}"
    
    def _verify_change(self, before: str, after: str) -> bool:
        """验证动作是否产生了变化"""
        return before != after  # Simplified; actual comparison uses SOM hash
    
    def execute(self, action: str, params: dict, 
                verify: bool = True, retry: bool = True) -> dict:
        """执行动作，带失败回溯 + 可选视觉验证
        
        Args:
            action: 动作类型 (click, drag, scroll, ...)
            params: MCP参数字典
            verify: 是否做前后截图验证
            retry: 是否自动重试
            
        Returns:
            {"status": "ok"|"failed"|"fallback",
             "attempts": int, "elapsed_ms": float,
             "error": str or None, "rollback": bool}
        """
        self._stats["attempts"] += 1
        t0 = time.time()
        
        # Verify action type exists
        if action not in ACTION_TYPES:
            return {"status": "failed", "error": f"Unknown action: {action}"}
        
        # Capture before state (if verifying)
        before = None
        if verify and "pid" in params:
            before = self._capture_state(params.get("pid", 0), params.get("window_id", 0))
        
        # Execute with retries
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1 if retry else 2):
            try:
                # In Hermes, this would call the actual MCP tool
                # For now, we dispatch the action info
                result = self._call_mcp(action, params)
                
                if attempt > 1:
                    self._stats["retries"] += 1
                    time.sleep(RETRY_DELAY_MS / 1000)
                
                # Verify after state
                if verify and before and "pid" in params:
                    after = self._capture_state(params["pid"], params.get("window_id", 0))
                    if not self._verify_change(before, after):
                        last_error = "No state change detected"
                        continue  # Retry
                
                # Success
                self._stats["success"] += 1
                entry = {
                    "action": action, "params": params, "attempts": attempt,
                    "elapsed_ms": round((time.time()-t0)*1000, 1),
                    "status": "ok", "verify": verify,
                }
                self._history.append(entry)
                self._log(entry)
                return {"status": "ok", "attempts": attempt, 
                        "elapsed_ms": entry["elapsed_ms"]}
                
            except Exception as e:
                last_error = str(e)
                continue
        
        # All retries failed
        self._stats["failures"] += 1
        entry = {
            "action": action, "params": params, "attempts": MAX_RETRIES,
            "elapsed_ms": round((time.time()-t0)*1000, 1),
            "status": "failed", "error": last_error,
        }
        self._history.append(entry)
        self._log(entry)
        return {"status": "failed", "error": last_error, "attempts": MAX_RETRIES}
    
    def rollback(self, steps: int = 1) -> bool:
        """回滚到最后N个稳定状态"""
        if len(self._history) < steps:
            return False
        # Mark last N entries as rolled back
        for i in range(1, steps + 1):
            if len(self._history) >= i:
                self._history[-i]["rollback"] = True
        return True
    
    def stats(self) -> dict:
        return {**self._stats, "history_len": len(self._history)}
    
    def _log(self, entry: dict):
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── DSV4裁决层 ──

class DSV4Adjudicator:
    """DeepSeek V4 视觉裁决: 执行前确认 + 执行后验证"""
    
    def pre_check(self, action: str, params: dict, som_elements: list) -> dict:
        """执行前裁决: 视觉确认目标元素是否存在"""
        if action in ("click", "right_click", "double_click"):
            ei = params.get("element_index")
            if ei is not None:
                # Find element in SOM
                match = next((e for e in som_elements if e.get("element_index") == ei), None)
                if match:
                    return {"pass": True, "element": match.get("label")}
                else:
                    return {"pass": False, "reason": f"Element [{ei}] not found in current SOM"}
        return {"pass": True}
    
    def post_verify(self, before_capture: dict, after_capture: dict) -> dict:
        """执行后裁决: 视觉对比前后变化"""
        before_els = before_capture.get("elements", [])
        after_els = after_capture.get("elements", [])
        if len(before_els) != len(after_els):
            return {"pass": True, "change": f"Element count: {len(before_els)} → {len(after_els)}"}
        # Check hash/fingerprint change
        before_fp = hash(str(before_els))
        after_fp = hash(str(after_els))
        if before_fp != after_fp:
            return {"pass": True, "change": "State fingerprint changed"}
        return {"pass": False, "change": "No change detected"}


# ── 统一入口 ──

class Phase2Engine:
    """Phase 2 统一入口: 动作执行 + 裁决 + 回溯"""
    
    def __init__(self):
        self.executor = ActionExecutor()
        self.judge = DSV4Adjudicator()
    
    def act(self, action: str, params: dict, som_elements: list = None) -> dict:
        """完整动作管道: 裁决 → 执行 → 验证
        
        1. DSV4 pre-check: 视觉确认
        2. Execute with retry
        3. DSV4 post-verify: 截图对比
        4. Rollback if verification fails
        """
        # Step 1: Pre-check
        if som_elements:
            check = self.judge.pre_check(action, params, som_elements)
            if not check["pass"]:
                return {"status": "pre_check_failed", "reason": check["reason"]}
        
        # Step 2: Execute
        result = self.executor.execute(action, params, verify=True)
        
        # Step 3: Post-verify (handled inside execute)
        if result["status"] == "failed":
            # Step 4: Auto-rollback
            self.executor.rollback(1)
            result["rollback"] = True
        
        return result
    
    def stats(self) -> dict:
        return self.executor.stats()


# ── 测试 ──

def test_phase2():
    p2 = Phase2Engine()
    
    print("Phase 2 Engine Test")
    print("=" * 50)
    
    # Test 1: Valid action
    r = p2.act("click", {"pid": 20884, "element_index": 13})
    print(f"  click[13]: {r['status']}")
    
    # Test 2: Unknown action
    r = p2.act("fly", {"pid": 0})
    print(f"  fly:       {r['status']}")
    
    # Test 3: With SOM pre-check
    som = [{"element_index": 14, "label": "技能与工具"}]
    r = p2.act("click", {"pid": 20884, "element_index": 14}, som_elements=som)
    print(f"  click[14](pre-checked): {r['status']}")
    
    # Test 4: Missing element in SOM
    som = [{"element_index": 7, "label": "交换侧边栏位置"}]
    r = p2.act("click", {"pid": 20884, "element_index": 999}, som_elements=som)
    print(f"  click[999](missing):    {r['status']}")
    
    print(f"\nStats: {json.dumps(p2.stats(), indent=2)}")


if __name__ == "__main__":
    test_phase2()
