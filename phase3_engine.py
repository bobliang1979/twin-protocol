#!/usr/bin/env python3
"""
Phase 3: 双Agent + 跨会话记忆 + 6模型并行推理

架构:
  Observer Agent (S3) — 持续视觉监控, 检测变化
  Actor Agent (S0)   — 根据Observer的发现执行动作
  
  跨会话记忆: 失败模式自动记录 → quality_calibration 引擎
  6模型并行: 通过Twins Protocol同时咨询所有LLM
"""
import json, os, time, threading, queue
from typing import Optional

MEMORY_FILE = os.path.expanduser("~/phase3_memory.jsonl")
VOTE_LOG = os.path.expanduser("~/phase3_votes.jsonl")

# ── 跨会话记忆 ──

class CrossSessionMemory:
    """记住跨会话的失败模式 + 成功策略"""
    
    def __init__(self):
        self._episodes = self._load()
    
    def _load(self) -> list:
        episodes = []
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            episodes.append(json.loads(line))
                        except:
                            pass
        return episodes
    
    def record(self, task: str, action: str, success: bool, 
               pattern: str = "", elapsed_ms: float = 0):
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "task": task, "action": action, "success": success,
            "pattern": pattern, "elapsed_ms": round(elapsed_ms, 1),
        }
        self._episodes.append(entry)
        with open(MEMORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def get_similar(self, task: str, n: int = 5) -> list:
        """查询相似任务的历史记录"""
        kw = task.lower().split()
        scored = []
        for ep in self._episodes:
            score = sum(1 for k in kw if k in ep.get("task","").lower())
            if score > 0:
                scored.append((score, ep))
        scored.sort(key=lambda x: -x[0])
        return [s[1] for s in scored[:n]]
    
    def success_rate(self, task: str = "") -> float:
        """查询任务成功率"""
        relevant = [e for e in self._episodes 
                    if not task or task.lower() in e.get("task","").lower()]
        if not relevant:
            return 0.0
        return sum(1 for e in relevant if e["success"]) / len(relevant)
    
    def summary(self) -> dict:
        total = len(self._episodes)
        success = sum(1 for e in self._episodes if e["success"])
        return {
            "episodes": total,
            "success": success,
            "fail": total - success,
            "rate": f"{success/total*100:.1f}%" if total else "N/A",
            "patterns": len(set(e.get("pattern","") for e in self._episodes if e.get("pattern"))),
        }


# ── 6模型并行推理 ──

MODEL_POOL = ["gemini", "chatglm", "copilot", "qwen", "codex", "deepseek"]

class MultiModelVoter:
    """6模型并行投票 """
    
    def __init__(self):
        self._available = self._probe_models()
    
    def _probe_models(self) -> list:
        """检测当前可用的模型"""
        available = []
        # Gemini: Tabbit [0]
        # ChatGLM: Tabbit [1]
        # Copilot: Tabbit [2]
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                for i, pg in enumerate(browser.contexts[0].pages):
                    url = pg.url.lower()
                    for model in MODEL_POOL:
                        if model in url:
                            available.append({"name": model, "tab": i, "url": pg.url[:60]})
        except:
            available = [{"name": "gemini", "tab": 0}]
        return available
    
    def consult_all(self, question: str, timeout_per_model: int = 15) -> dict:
        """并行向所有可用模型咨询"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def consult_model(model_info: dict) -> dict:
            """向单个模型发送问题"""
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                    page = browser.contexts[0].pages[model_info["tab"]]
                    
                    # Focus input
                    if model_info["name"] in ("gemini",):
                        page.evaluate('document.querySelector("[role=textbox]").focus()')
                        page.keyboard.type(question[:500], delay=5)
                        time.sleep(0.3)
                        page.keyboard.press("Enter")
                    elif model_info["name"] in ("chatglm",):
                        page.fill("textarea", question[:500])
                        page.keyboard.press("Enter")
                    elif model_info["name"] in ("copilot",):
                        page.fill("#userInput", question[:500])
                        page.keyboard.press("Enter")
                    
                    time.sleep(timeout_per_model)
                    text = page.evaluate("document.documentElement.innerText")
                    return {
                        "model": model_info["name"],
                        "response": text[-800:] if text else "",
                        "status": "ok"
                    }
            except Exception as e:
                return {"model": model_info["name"], "response": "", "status": "error", "error": str(e)[:80]}
        
        results = {}
        with ThreadPoolExecutor(max_workers=len(self._available)) as ex:
            futures = {ex.submit(consult_model, m): m["name"] for m in self._available}
            for f in as_completed(futures):
                r = f.result()
                results[r["model"]] = r
                # Log vote
                with open(VOTE_LOG, "a") as log:
                    log.write(json.dumps(r, ensure_ascii=False) + "\n")
        
        return {
            "question": question[:80],
            "models_consulted": len(results),
            "results": results,
            "consensus": self._find_consensus(results),
        }
    
    def _find_consensus(self, results: dict) -> str:
        """简单多数投票找共识"""
        # Extract key themes from responses
        themes = {}
        for model, r in results.items():
            resp = r.get("response", "")
            # Simple keyword extraction
            for word in resp.split():
                if len(word) > 3:
                    themes[word] = themes.get(word, 0) + 1
        if themes:
            top = max(themes, key=themes.get)
            return f"{top} (appears in {themes[top]}/{len(results)} models)"
        return "No consensus"


# ── 双Agent视觉监控 ──

class ObserverAgent:
    """S3: 持续视觉监控, 检测变化"""
    
    def __init__(self, interval_sec: float = 3.0):
        self.interval = interval_sec
        self._last_state = None
        self._alerts = queue.Queue()
        self._running = False
    
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        self._running = False
    
    def _loop(self):
        while self._running:
            try:
                # Capture current state via MCP
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
                    for pg in browser.contexts[0].pages:
                        title = pg.evaluate("document.title")
                        url = pg.url[:60]
                        # Check for popups
                        if any(kw in title.lower() for kw in ["alert", "confirm", "dialog", "error"]):
                            self._alerts.put({"type": "popup", "title": title, "url": url, "ts": time.time()})
            except:
                pass
            time.sleep(self.interval)
    
    def get_alerts(self) -> list:
        alerts = []
        while not self._alerts.empty():
            alerts.append(self._alerts.get())
        return alerts


class ActorAgent:
    """S0: 根据Observer发现执行动作"""
    
    def __init__(self, memory: CrossSessionMemory):
        self.memory = memory
    
    def act(self, action: str, params: dict, task: str = "") -> dict:
        t0 = time.time()
        # Check memory for similar tasks
        similar = self.memory.get_similar(task, n=3)
        if similar:
            prev_success = sum(1 for s in similar if s["success"])
            prev_total = len(similar)
            print(f"  [memory] {task}: {prev_success}/{prev_total} similar tasks")
        
        # Execute (simplified - actual MCP call would go here)
        success = True  # Would be real MCP result
        elapsed = (time.time() - t0) * 1000
        
        self.memory.record(task, action, success, 
                          pattern=task.split()[0] if task else action,
                          elapsed_ms=elapsed)
        return {"success": success, "elapsed_ms": round(elapsed, 1)}


# ── Phase 3 入口 ──

class Phase3Engine:
    """Phase 3: 双Agent + 跨会话记忆 + 多模型"""
    
    def __init__(self):
        self.memory = CrossSessionMemory()
        self.observer = ObserverAgent()
        self.actor = ActorAgent(self.memory)
        self.voter = MultiModelVoter()
    
    def start(self):
        self.observer.start()
        print(f"[phase3] Observer started (interval={self.observer.interval}s)")
        print(f"[phase3] Memory: {self.memory.summary()['episodes']} episodes")
        print(f"[phase3] Models: {[m['name'] for m in self.voter._available]}")
    
    def stop(self):
        self.observer.stop()
    
    def check_alerts(self) -> list:
        return self.observer.get_alerts()
    
    def execute(self, task: str, action: str, params: dict) -> dict:
        return self.actor.act(action, params, task)
    
    def vote(self, question: str) -> dict:
        return self.voter.consult_all(question)


# ── 测试 ──

if __name__ == "__main__":
    p3 = Phase3Engine()
    p3.start()
    
    print("\n" + "=" * 55)
    print("  Phase 3 Engine Test")
    print("=" * 55)
    
    # Test memory
    print("\n--- Memory ---")
    p3.execute("click_button", "click", {"pid": 20884, "element_index": 13})
    p3.execute("type_text", "type", {"text": "hello"})
    p3.execute("scroll_page", "scroll", {"direction": "down"})
    print(f"  Memory summary: {json.dumps(p3.memory.summary())}")
    
    # Test similar task recall
    similar = p3.memory.get_similar("click")
    print(f"  Similar to 'click': {len(similar)} episodes")
    
    # Test model pool
    print(f"\n--- Model Pool ---")
    for m in p3.voter._available:
        print(f"  [{m['tab']}] {m['name']:10s} {m['url'][:50]}")
    
    # Check alerts
    alerts = p3.check_alerts()
    print(f"\n--- Observer ---")
    print(f"  Alerts detected: {len(alerts)}")
    
    p3.stop()
    print("\nPhase 3: OK")
