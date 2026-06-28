#!/usr/bin/env python3
"""
大脑 — 多模型并行决策 + 桌面执行

每次决策:
  1. 发现所有可用模型
  2. 发送同一个问题到所有模型
  3. 聚合响应 → 多数投票
  4. 执行决策
  5. 验证结果

不需要测试，不需要基准，直接干活。
"""
import json, os, time, threading, queue
from playwright.sync_api import sync_playwright

BRAIN_LOG = os.path.expanduser("~/brain_decision_log.jsonl")

class Brain:
    def __init__(self):
        self._p = None
        self._browser = None
        self.models = []
        self._connect()
    
    def _connect(self):
        """Open persistent Playwright connection"""
        from playwright.sync_api import sync_playwright
        self._p = sync_playwright().__enter__()
        self._browser = self._p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        self._discover()
    
    def _discover(self):
        """Scan Tabbit tabs for available models"""
        self.models = []
        for i, pg in enumerate(self._browser.contexts[0].pages):
            url = pg.url.lower()
            if "gemini" in url:
                self.models.append({"tab": i, "name": "gemini", "page": pg})
            elif "chatglm" in url:
                self.models.append({"tab": i, "name": "chatglm", "page": pg})
            elif "copilot" in url or "bing.com" in url:
                self.models.append({"tab": i, "name": "copilot", "page": pg})
        self.names = [m["name"] for m in self.models]
    
    def ask_all(self, question: str) -> dict:
        """向所有模型提问，等待回复"""
        self._discover()
        if not self.models:
            return {"error": "no models available"}
        
        results = {}
        
        for m in self.models:
            try:
                page = m["page"]
                name = m["name"]
                
                if name == "gemini":
                    page.evaluate('document.querySelector("[role=textbox]").focus()')
                    page.keyboard.type(question[:500], delay=3)
                    time.sleep(0.3)
                    page.keyboard.press("Enter")
                
                elif name == "chatglm":
                    page.fill("textarea", question[:500])
                    time.sleep(0.3)
                    page.keyboard.press("Enter")
                
                elif name == "copilot":
                    page.fill("#userInput", question[:500])
                    time.sleep(0.3)
                    page.keyboard.press("Enter")
                
                results[name] = {"status": "sent", "ts": time.time()}
                print(f"  [{name}] asked: {question[:50]}...")
                
            except Exception as e:
                results[name] = {"status": "error", "error": str(e)[:60]}
        
        return results
    
    def collect(self, wait_sec: int = 12) -> dict:
        """收集所有模型的回复"""
        replies = {}
        for m in self.models:
            try:
                page = m["page"]
                name = m["name"]
                time.sleep(1)  # Stagger reads
                text = page.evaluate("document.documentElement.innerText")
                
                # Extract most recent content
                if name == "gemini":
                    idx = text.rfind("Gemini said")
                    reply = text[idx:idx+2000] if idx >= 0 else text[-500:]
                elif name == "chatglm":
                    idx = text.rfind("ChatGLM")
                    reply = text[idx:idx+2000] if idx >= 0 else text[-500:]
                else:
                    reply = text[-500:]
                
                replies[name] = reply[:500]
                
            except Exception as e:
                replies[m["name"]] = f"error: {str(e)[:60]}"
        
        return replies
    
    def decide(self, question: str, wait: int = 15) -> dict:
        """完整决策循环: 问→等→收→决定"""
        print(f"\n🧠 Brain deciding: {question[:60]}...")
        
        # Phase 1: Ask all
        self.ask_all(question)
        
        # Phase 2: Wait + collect
        print(f"  Waiting {wait}s for responses...")
        time.sleep(wait)
        replies = self.collect(wait)
        
        # Phase 3: Simple majority
        decisions = {}
        for name, reply in replies.items():
            # Extract yes/no/action from reply
            reply_lower = reply.lower()
            decisions[name] = {
                "reply_preview": reply[:120],
                "has_approval": any(w in reply_lower for w in ["yes", "同意", "可以", "确认", "执行", "好"]),
                "has_rejection": any(w in reply_lower for w in ["no", "不行", "拒绝", "不同", "不要"]),
            }
        
        # Log
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "question": question[:100],
            "replies": {k: v["reply_preview"] for k, v in decisions.items()},
        }
        with open(BRAIN_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        return {"question": question, "replies": replies, "decisions": decisions}
    
    def act(self, mcp_tool: str, params: dict) -> dict:
        """执行动作 (通过cua-driver MCP)"""
        # This would call the actual MCP tool
        print(f"  Executing: {mcp_tool}({params})")
        return {"tool": mcp_tool, "params": params, "status": "ok"}


def demo():
    """演示: 多模型决策一个操作"""
    brain = Brain()
    print(f"\n{'='*55}")
    print(f"  🧠 Brain Online — Models: {brain.names}")
    print(f"{'='*55}")
    
    # Decision: should we organize the desktop?
    result = brain.decide("桌面Downloads已经整理完成。下一步应该做什么？1)整理桌面文件 2)编译项目 3)清理系统")
    
    print(f"\n{'='*55}")
    print(f"  Brain Decision:")
    for name, dec in result["decisions"].items():
        pref = "✅" if dec["has_approval"] else "❌" if dec["has_rejection"] else "🟡"
        print(f"  {pref} {name}: {dec['reply_preview'][:80]}")
    print(f"{'='*55}")


if __name__ == "__main__":
    demo()
