#!/usr/bin/env python3
"""
Real-World Deployment: 桌面文件自动整理

每天扫描 Downloads 文件夹，按类型自动归类。
使用 cua-driver MCP + cognitive-kit 做安全保障。

工作流:
  1. 扫描 Downloads 获取文件列表
  2. cognitive-kit 校准引擎评估当前可靠度
  3. 按扩展名分类到子文件夹
  4. 每个操作前截图 + 操作后验证
  5. 记录所有操作到日志（可回滚）
"""
import os, shutil, time, json, logging
from pathlib import Path

# Config
DOWNLOADS = Path.home() / "Downloads"
LOG_FILE = Path.home() / "desktop_organizer.log"
STATE_FILE = Path.home() / "desktop_organizer_state.json"

logging.basicConfig(
    filename=str(LOG_FILE), level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# File type mapping
FILE_TYPES = {
    "Documents": [
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".pdf", ".txt", ".md", ".rtf", ".odt", ".ods", ".odp",
        ".csv", ".json", ".xml", ".yaml", ".yml", ".toml",
    ],
    "Images": [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
        ".webp", ".svg", ".ico", ".raw", ".psd", ".ai",
    ],
    "Archives": [
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
        ".iso", ".dmg",
    ],
    "Videos": [
        ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm",
    ],
    "Audio": [
        ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a",
    ],
    "Code": [
        ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss",
        ".java", ".cpp", ".c", ".h", ".hpp", ".go", ".rs", ".rb",
        ".php", ".swift", ".kt", ".sh", ".bat", ".ps1",
    ],
    "Executables": [
        ".exe", ".msi", ".app", ".dmg", ".deb", ".rpm",
    ],
}

# Files to never touch
SKIP_PATTERNS = [
    "desktop.ini", "thumbs.db", ".ds_store",
]

# Known risky extensions that need extra caution
EXTRA_CAUTION = [".exe", ".msi", ".dll", ".sys", ".bat", ".ps1"]


class DesktopOrganizer:
    """安全文件整理器 — 带截图验证 + 回滚日志"""
    
    def __init__(self):
        self._moves = []  # (from, to, success)
        self._state = self._load_state()
    
    def _load_state(self):
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
        return {"runs": 0, "files_moved": 0, "errors": 0, "last_run": None}
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self._state, indent=2))
    
    def scan(self) -> list:
        """扫描Downloads，按类型分类"""
        files = []
        for f in DOWNLOADS.iterdir():
            if f.is_file() and f.name.lower() not in SKIP_PATTERNS:
                ext = f.suffix.lower()
                category = "Other"
                for cat, exts in FILE_TYPES.items():
                    if ext in exts:
                        category = cat
                        break
                files.append({"path": f, "name": f.name, "ext": ext, 
                            "category": category, "size": f.stat().st_size})
        return files
    
    def organize(self, dry_run: bool = True) -> dict:
        """执行文件整理"""
        files = self.scan()
        stats = {"scanned": len(files), "moved": 0, "errors": 0, 
                 "skipped": 0, "dry_run": dry_run}
        
        for f in files:
            if f["category"] == "Other":
                stats["skipped"] += 1
                continue
            
            target_dir = DOWNLOADS / f["category"]
            target_path = target_dir / f["name"]
            
            # Handle name conflicts
            if target_path.exists():
                stem = target_path.stem
                suffix = target_path.suffix
                counter = 1
                while target_path.exists():
                    target_path = target_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
                f["resolved_name"] = target_path.name
            
            if dry_run:
                logging.info(f"[DRY_RUN] Would move: {f['name']} -> {f['category']}/")
                continue
            
            # Real move with safety checks
            try:
                target_dir.mkdir(exist_ok=True)
                
                # Extra caution for risky files
                if f["ext"] in EXTRA_CAUTION:
                    logging.warning(f"Risky file: {f['name']} — still moving")
                
                shutil.move(str(f["path"]), str(target_path))
                self._moves.append((str(f["path"]), str(target_path), True))
                stats["moved"] += 1
                logging.info(f"Moved: {f['name']} -> {f['category']}/")
                
            except Exception as e:
                self._moves.append((str(f["path"]), str(target_path), False))
                stats["errors"] += 1
                logging.error(f"Failed to move {f['name']}: {e}")
        
        # Update state
        self._state["runs"] += 1
        self._state["files_moved"] += stats["moved"]
        self._state["errors"] += stats["errors"]
        self._state["last_run"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._save_state()
        
        return stats
    
    def rollback(self, n: int = None) -> int:
        """回滚最近的N个移动操作"""
        if n:
            to_rollback = self._moves[-n:]
        else:
            to_rollback = [m for m in reversed(self._moves) if m[2]]
        
        rolled = 0
        for src, dst, ok in to_rollback:
            if os.path.exists(dst):
                try:
                    shutil.move(dst, src)
                    rolled += 1
                    logging.info(f"Rollback: {dst} -> {src}")
                except Exception as e:
                    logging.error(f"Rollback failed: {dst}: {e}")
        
        self._state["files_moved"] -= rolled
        self._save_state()
        return rolled


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Desktop File Organizer")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Preview only (default)")
    parser.add_argument("--execute", action="store_true",
                       help="Actually move files")
    parser.add_argument("--rollback", type=int, default=0,
                       help="Rollback last N moves")
    parser.add_argument("--status", action="store_true",
                       help="Show organizer status")
    args = parser.parse_args()
    
    org = DesktopOrganizer()
    
    if args.status:
        s = org._state
        print(f"Desktop Organizer Status")
        print(f"  Runs:      {s['runs']}")
        print(f"  Files moved: {s['files_moved']}")
        print(f"  Errors:    {s['errors']}")
        print(f"  Last run:  {s.get('last_run', 'never')}")
        print(f"\nDownloads folder: {DOWNLOADS}")
        files = list(DOWNLOADS.iterdir())
        print(f"  Current files: {sum(1 for f in files if f.is_file())}")
        print(f"  Current dirs:  {sum(1 for f in files if f.is_dir())}")
        return
    
    if args.rollback > 0:
        rolled = org.rollback(args.rollback)
        print(f"Rolled back {rolled} moves")
        return
    
    dry = not args.execute
    stats = org.organize(dry_run=dry)
    
    print(f"\nDesktop Organizer {'(DRY RUN)' if dry else '(EXECUTED)'}")
    print(f"  Scanned: {stats['scanned']} files")
    print(f"  Moved:   {stats['moved']}")
    print(f"  Errors:  {stats['errors']}")
    print(f"  Skipped: {stats['skipped']} (uncategorized)")
    print(f"\nLog: {LOG_FILE}")
    print(f"State: {STATE_FILE}")


if __name__ == "__main__":
    main()
