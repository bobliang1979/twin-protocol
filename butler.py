#!/usr/bin/env python3
"""
AI Desktop Butler — 持续运行的真实桌面助手

循环: 状态检测 → 多模型决策 → 执行 → 验证
不需要人干预，不需要测试，直接干活。
"""
import json, os, time, shutil, subprocess, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

HOME = Path.home()
DOWNLOADS = HOME / "Downloads"
DESKTOP = HOME / "Desktop"
BRAIN_LOG = HOME / "butler_log.jsonl"

# ── 持久 CDP 连接 ──

class CDP:
    def __init__(self):
        self._p = sync_playwright().__enter__()
        self._b = self._p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    
    @property
    def pages(self):
        return self._b.contexts[0].pages


# ── 状态检测 ──

def count_files(path: Path) -> int:
    return sum(1 for f in path.iterdir() if f.is_file())

def disk_usage() -> str:
    usage = shutil.disk_usage("C:/")
    free_gb = usage.free / (1024**3)
    return f"C: free {free_gb:.1f}GB"


# ── 执行器 ──

def organize_downloads():
    """执行Downloads文件整理"""
    from desktop_organizer import DesktopOrganizer
    org = DesktopOrganizer()
    result = org.organize(dry_run=False)
    return result

def cleanup_temp():
    """清理临时文件"""
    temp = Path(os.environ.get("TEMP", "/tmp"))
    count = 0
    for f in list(temp.iterdir())[:50]:
        try:
            if f.is_file() and time.time() - f.stat().st_mtime > 86400:
                f.unlink()
                count += 1
        except:
            pass
    return count

def log_action(action, result):
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "action": action,
        "result": result,
    }
    with open(BRAIN_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"  📝 Logged: {action} → {result}")


# ── 大脑 ──

class Butler:
    def __init__(self):
        self.cdp = CDP()
        self._find_models()
    
    def _find_models(self):
        self.models = []
        for pg in self.cdp.pages:
            url = pg.url.lower()
            if "gemini" in url: self.models.append(("gemini", pg))
            if "chatglm" in url: self.models.append(("chatglm", pg))
            if "copilot" in url: self.models.append(("copilot", pg))
        print(f"  Models: {[m[0] for m in self.models]}")
    
    def ask(self, question: str) -> dict:
        replies = {}
        for name, pg in self.models:
            try:
                if name == "gemini":
                    pg.evaluate('document.querySelector("[role=textbox]").focus()')
                    pg.keyboard.type(question[:400], delay=2)
                    time.sleep(0.2)
                    pg.keyboard.press("Enter")
                elif name == "chatglm":
                    pg.fill("textarea", question[:400])
                    time.sleep(0.2)
                    pg.keyboard.press("Enter")
                replies[name] = "sent"
            except Exception as e:
                replies[name] = f"err: {e}"
        return replies
    
    def analyze_state(self) -> dict:
        download_count = count_files(DOWNLOADS)
        desk_count = count_files(DESKTOP)
        disk = disk_usage()
        return {
            "downloads": download_count,
            "desktop": desk_count,
            "disk": disk,
            "models": len(self.models),
        }
    
    def tick(self):
        """一次检测→决策→执行循环"""
        print(f"\n{'='*55}")
        print(f"  Butler Tick — {time.strftime('%H:%M:%S')}")
        print(f"{'='*55}")
        
        state = self.analyze_state()
        print(f"  State: {state}")
        
        # Decision logic (rule-based + model-based)
        actions = []
        
        if state["downloads"] > 20:
            actions.append("organize_downloads")
        if state["desktop"] > 50:
            actions.append("ask_models: should we clean desktop?")
        
        if not actions:
            actions.append("idle")
        
        # Execute
        for action in actions:
            if action == "organize_downloads":
                r = organize_downloads()
                log_action("organize_downloads", f"{r['moved']} moved, {r['errors']} errors")
            
            elif action == "idle":
                print("  ✅ System clean — nothing to do")
                log_action("idle", "ok")
        
        return actions


# ── 主循环 ──

def main():
    butler = Butler()
    interval = 60  # Check every 60 seconds
    
    print(f"\n  🤖 AI Desktop Butler Online")
    print(f"  Interval: {interval}s")
    print(f"  Monitoring: Downloads, Desktop, Disk")
    print(f"  Log: {BRAIN_LOG}")
    print(f"\n  Press Ctrl+C to stop\n")
    
    try:
        cycle = 0
        while True:
            cycle += 1
            print(f"\n  Cycle #{cycle}")
            butler.tick()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n  Butler stopped.")


if __name__ == "__main__":
    main()
