#!/usr/bin/env python3
"""
生成200个Windows桌面操作评测任务

从OSWorld论文提取任务框架，适配Windows环境。
5大类 × 40任务 = 200个标准化测试。
"""
import json, os, random

random.seed(42)

TASKS = {
    "file_operations": {
        "prefix": "F",
        "icon": "📁",
        "count": 40,
        "templates": [
            "Create a text file named {name}.txt with content '{content}'",
            "Copy file {src} to {dst}",
            "Rename file {old} to {new}",
            "Delete file {name}.{ext}",
            "Create directory {dirname}",
            "List files in {path} with extension {ext}",
            "Find all files larger than {size}KB",
            "Move file {src} from {from_dir} to {to_dir}",
            "Create a backup of {filename} as {filename}.bak",
            "Compress {dirname} into a zip archive",
            "Extract archive {archive}.zip to {output_dir}",
            "Search for text '{keyword}' in all .txt files",
            "Count total files in {path} and subdirectories",
            "Create a symbolic link {link} pointing to {target}",
            "Change file {filename} permissions to read-only",
            "Sort files in {dir} by modification date",
            "Merge {file1}.txt and {file2}.txt into merged.txt",
            "Split {largefile}.csv into chunks of {n} lines",
            "Rename all .jpg files in {dir} to image_0001.jpg format",
            "Create a folder structure: {a}/{b}/{c}",
            "Copy only .pdf files from {src} to {dst}",
            "Delete empty directories in {path}",
            "Generate a checksum for {filename}",
            "Find duplicate files in {dir1} and {dir2}",
            "Replace text '{old_text}' with '{new_text}' in {file}",
            "Append line '{line}' to {file}.txt",
            "Create a CSV file with columns: {col1}, {col2}, {col3}",
            "Convert {file}.txt to uppercase and save as {file}.upper.txt",
            "Remove the first {n} lines from {file}.log",
            "Sort the contents of {file}.txt alphabetically",
        ]
    },
    "application_control": {
        "prefix": "A",
        "icon": "🪟",
        "count": 40,
        "templates": [
            "Launch Notepad and type '{text}'",
            "Open Calculator and compute {expression}",
            "Start Paint and create a 100x100 image",
            "Open Command Prompt and run 'dir'",
            "Launch Task Manager",
            "Open File Explorer to {path}",
            "Start a PowerShell session and run 'Get-Process'",
            "Open the Snipping Tool",
            "Launch {app_name} from the Start menu",
            "Open the Character Map utility",
            "Start Registry Editor (regedit)",
            "Open Device Manager",
            "Launch Disk Cleanup utility",
            "Open System Information (msinfo32)",
            "Start Resource Monitor",
            "Launch Event Viewer",
            "Open Windows Update settings",
            "Start the On-Screen Keyboard",
            "Launch the Magnifier tool",
            "Open Narrator settings",
            "Start {browser} in incognito/private mode",
            "Open Windows Security center",
            "Launch Remote Desktop Connection",
            "Start the Snipping Tool and take a screenshot",
        ]
    },
    "system_settings": {
        "prefix": "S",
        "icon": "⚙️",
        "count": 40,
        "templates": [
            "Open Display Settings",
            "Change desktop background to solid color",
            "Open Sound settings",
            "Check available disk space on C: drive",
            "View current IP address configuration",
            "Open Bluetooth settings",
            "Check Windows Update status",
            "Open Privacy settings",
            "View installed applications list",
            "Open Date and Time settings",
            "Check system architecture (32/64-bit)",
            "View environment variable PATH",
            "Open Power & sleep settings",
            "Check Windows activation status",
            "View recently added hardware",
            "Open Network & Internet settings",
            "Check available memory (RAM)",
            "Open Ease of Access settings",
            "View startup programs list",
            "Open Default Apps settings",
            "Check Windows Firewall status",
            "Open Storage settings",
            "View system protection (restore point) status",
            "Open Accounts settings",
            "Check for driver updates",
        ]
    },
    "browser_operations": {
        "prefix": "B",
        "icon": "🌐",
        "count": 40,
        "templates": [
            "Open {url} in the default browser",
            "Search for '{query}' on Google",
            "Navigate to {site} and read the page title",
            "Find the OSWorld benchmark GitHub page",
            "Open the NeurIPS 2026 website",
            "Search for '{topic}' and open the first result",
            "Check the weather in {city}",
            "Search for '{product}' on Amazon",
            "Look up '{term}' on Wikipedia",
            "Search YouTube for '{video_topic}'",
            "Open Gmail and check for new emails",
            "Search for '{news_topic}' in Google News",
            "Open Google Maps and search for {location}",
            "Search for '{research_paper}' on arXiv",
            "Look up '{company}' stock price",
            "Search for '{recipe}' recipes",
            "Open Google Translate and translate '{word}' to {lang}",
            "Search for '{job_title}' jobs on LinkedIn",
            "Find '{document_name}' on Google Docs",
            "Open GitHub and search for '{repo_name}'",
        ]
    },
    "multi_step": {
        "prefix": "M",
        "icon": "🔗",
        "count": 40,
        "templates": [
            "Create a file → type content → save → verify content",
            "Launch Notepad → type text → close with saving → reopen → verify",
            "Open browser → search → download result → open downloaded file",
            "Take a screenshot → save to Desktop → rename → verify",
            "Open calculator → compute → copy result → paste into Notepad",
            "Create a folder → open in Explorer → create file inside → verify",
            "Open settings → change wallpaper → revert to original → verify",
            "Search for file → copy to new location → delete original → verify",
            "Launch app → minimize → restore → close → verify app is closed",
            "Open command prompt → run command → save output to file → view result",
            "Find file by extension → move to folder → rename → verify new path",
            "Open browser → login to site → perform action → logout → verify",
            "Download file → extract archive → organize contents → clean up",
            "Compare two files → identify differences → create diff report",
            "Create spreadsheet → add data → save as CSV → verify CSV content",
        ]
    }
}

all_tasks = []

# Generate random but reproducible parameters
NAMES = ["test", "sample", "welcome", "readme", "notes", "draft", "config", "backup", "index", "data"]
EXTS = ["txt", "csv", "log", "json", "xml", "html", "md", "py", "bat", "ini"]
DIRS = ["Documents", "Desktop", "Downloads", "Temp", "Archive", "Backup", "Projects", "Reports"]
SITES = ["google.com", "github.com", "wikipedia.org", "arxiv.org", "youtube.com", "stackoverflow.com", "reddit.com"]

for category, cfg in TASKS.items():
    for i in range(cfg["count"]):
        t = random.choice(cfg["templates"])
        # Fill in parameters
        t = t.replace("{name}", random.choice(NAMES))
        t = t.replace("{ext}", random.choice(EXTS))
        t = t.replace("{src}", random.choice(NAMES))
        t = t.replace("{dst}", random.choice(NAMES) + "_copy")
        t = t.replace("{old}", random.choice(NAMES))
        t = t.replace("{new}", random.choice(NAMES) + "_v2")
        t = t.replace("{dirname}", random.choice(DIRS) + "_" + str(random.randint(1,99)))
        t = t.replace("{path}", random.choice(DIRS))
        t = t.replace("{size}", str(random.randint(10, 10000)))
        t = t.replace("{content}", f"Test content {random.randint(1000,9999)}")
        t = t.replace("{keyword}", random.choice(["TODO", "IMPORTANT", "DEBUG", "ERROR", "DONE"]))
        t = t.replace("{url}", random.choice(SITES))
        t = t.replace("{query}", random.choice(["python automation", "windows desktop", "AI agent", "NeurIPS 2026", "computer control"]))
        t = t.replace("{site}", random.choice(SITES))
        t = t.replace("{topic}", random.choice(["machine learning", "cognition", "robotics", "computer vision"]))
        t = t.replace("{app_name}", random.choice(["Notepad", "Calculator", "Paint", "WordPad"]))
        t = t.replace("{browser}", random.choice(["Chrome", "Edge", "Firefox"]))
        
        all_tasks.append({
            "id": f"{cfg['prefix']}{i+1:03d}",
            "category": category,
            "description": t,
        })

# Save
OUTPUT = os.path.expanduser("~/osworld_200_tasks.json")
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump({
        "total": len(all_tasks),
        "categories": {k: v["icon"] for k, v in TASKS.items()},
        "tasks": all_tasks,
    }, f, indent=2, ensure_ascii=False)

print(f"Generated {len(all_tasks)} tasks")
print(f"  File operations:    {sum(1 for t in all_tasks if t['category']=='file_operations')}")
print(f"  Application control: {sum(1 for t in all_tasks if t['category']=='application_control')}")
print(f"  System settings:    {sum(1 for t in all_tasks if t['category']=='system_settings')}")
print(f"  Browser operations: {sum(1 for t in all_tasks if t['category']=='browser_operations')}")
print(f"  Multi-step:         {sum(1 for t in all_tasks if t['category']=='multi_step')}")
print(f"Saved: {OUTPUT}")
