#!/usr/bin/env python3
"""
大脑 v2 — Gemini 审校修复版

修复: 多线程Playwright死锁, 模型发现泛化, 输入框自动探测, JSON结构化输出
"""
import json, os, time, re, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright
from collections import Counter

BRAIN_LOG = os.path.expanduser("~/brain_decision_log.jsonl")

class Brain:
    def __init__(self):
        self._lock = threading.Lock()
        self._p = sync_playwright().__enter__()
        self._browser = self._p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        self.models = {}  # name -> page
        self._discover()
    
    def _discover(self):
        """自动扫描标签页, 检测所有AI模型 (带超时防死锁)"""
        self.models = {}
        for pg in self._browser.contexts[0].pages:
            try:
                url = pg.url if hasattr(pg, 'url') else pg.evaluate("window.location.href", timeout=2000)
                title = pg.title(timeout=2000) if hasattr(pg, 'title') else ""
            except:
                continue
            url, title = (url or "").lower(), (title or "").lower()
            if "gemini" in url or "gemini" in title:
                self.models["Gemini"] = pg
            elif "qianwen" in url or "tongyi" in url or "通义" in title:
                self.models["通义千问"] = pg
            elif "chatglm" in url or "智谱" in title:
                self.models["ChatGLM"] = pg
            elif "copilot" in url or "bing.com" in url:
                self.models["Copilot"] = pg
        print(f"  Models: {list(self.models.keys())}")
        # 定时重扫: 每30秒检测新标签页 (仅首次启动)
        if not hasattr(self, '_rescan_started'):
            self._rescan_started = True
            t = threading.Thread(target=self._rescan_loop, daemon=True)
            t.start()
    
    def _rescan_loop(self):
        while True:
            time.sleep(30)
            try:
                self._rescan()
            except:
                pass
    
    def _rescan(self):
        """重新扫描标签页 (不启动新线程)"""
        for pg in self._browser.contexts[0].pages:
            try:
                url = pg.url if hasattr(pg, 'url') else pg.evaluate("window.location.href", timeout=1000)
                title = pg.title(timeout=1000) if hasattr(pg, 'title') else ""
            except:
                continue
            url, title = (url or "").lower(), (title or "").lower()
            name = None
            if "gemini" in url or "gemini" in title: name = "Gemini"
            elif "qianwen" in url or "tongyi" in url: name = "通义千问"
            elif "chatglm" in url or "智谱" in title: name = "ChatGLM"
            elif "copilot" in url or "bing.com" in url: name = "Copilot"
            if name and name not in self.models:
                self.models[name] = pg
                print(f"  [discover] New model: {name}")
    
    def _find_input(self, page):
        """自动探测输入框 (5种选择器)"""
        for sel in ["[contenteditable=true]", "textarea", "#userInput",
                     "div#prompt-textarea", "[role=textbox]"]:
            try:
                el = page.locator(sel).first
                if el.is_visible():
                    return el
            except:
                continue
        return None
    
    def ask_model(self, name: str, question: str) -> dict:
        """向单个模型提问 (线程安全)"""
        with self._lock:
            try:
                page = self.models[name]
                inp = self._find_input(page)
                if not inp:
                    return {"model": name, "status": "error", "error": "no input found"}
                
                inp.click()
                page.keyboard.press("Control+A")
                page.keyboard.press("Backspace")
                page.keyboard.type(question[:500], delay=2)
                time.sleep(0.2)
                page.keyboard.press("Enter")
                
                return {"model": name, "status": "sent", "ts": time.time()}
            except Exception as e:
                return {"model": name, "status": "error", "error": str(e)[:80]}
    
    def ask_all(self, question: str) -> dict:
        """并行向所有模型提问 (ThreadPoolExecutor + Lock)"""
        if not self.models:
            return {"error": "no models available"}
        
        results = {}
        with ThreadPoolExecutor(max_workers=len(self.models)) as ex:
            fut = {ex.submit(self.ask_model, n, question): n for n in self.models}
            for f in as_completed(fut):
                r = f.result()
                results[r["model"]] = r
                print(f"  [{r['model']}] {r['status']}")
        return results
    
    def collect(self, wait_sec: int = 12) -> dict:
        """收集所有模型回复"""
        time.sleep(wait_sec)
        replies = {}
        for name, page in self.models.items():
            try:
                text = page.evaluate("document.documentElement.innerText")
                # Extract latest reply
                markers = {"Gemini": "Gemini said", "ChatGLM": "ChatGLM",
                          "Copilot": "Copilot", "通义千问": "通义"}
                marker = markers.get(name, name)
                idx = text.rfind(marker)
                reply = text[idx:idx+2000] if idx >= 0 else text[-500:]
                replies[name] = reply[:500]
            except Exception as e:
                replies[name] = f"error: {str(e)[:60]}"
        return replies
    
    def decide(self, question: str, wait: int = 15) -> dict:
        """完整决策: 问→等→收→决定"""
        print(f"\n🧠 Brain deciding: {question[:60]}...")
        self.ask_all(question)
        print(f"  Waiting {wait}s...")
        replies = self.collect(wait)
        
        decisions = {}
        for name, reply in replies.items():
            rl = reply.lower()
            decisions[name] = {
                "reply": reply[:200],
                "approval": any(w in rl for w in ["yes","同意","可以","确认","执行","好"]),
                "rejection": any(w in rl for w in ["no","不行","拒绝","不同","不要"]),
            }
        
        entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "question": question[:100],
                 "replies": {k: v["reply"] for k,v in decisions.items()}}
        with open(BRAIN_LOG, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        return {"question": question, "replies": replies, "decisions": decisions}


if __name__ == "__main__":
    brain = Brain()
    print(f"  🧠 Brain v2 — Models: {list(brain.models.keys())}")
    r = brain.decide("桌面整理完成。下一步做什么？")
    for name, d in r["decisions"].items():
        m = "✅" if d["approval"] else "❌" if d["rejection"] else "🟡"
        print(f"  {m} {name}: {d['reply'][:80]}")
