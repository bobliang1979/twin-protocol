"""
twin_protocol.cli — CLI entry point: `twins` command
"""
import sys, json, os
from pathlib import Path


def cmd_init(args):
    """twins init — scaffold a new Twins Protocol project"""
    name = args[0] if args else "my-twins-project"
    path = Path.cwd() / name
    if path.exists():
        print(f"❌ {path} already exists")
        return 1
    path.mkdir(parents=True)
    (path / "outbox.jsonl").touch()
    (path / "shared_cognition.json").write_text(
        json.dumps({"session_id": name, "goal": "", "agreed_items": [],
                     "pending_items": [], "active_tasks": []}, indent=2)
    )
    (path / "README.md").write_text(f"# {name}\n\nTwins Protocol project.\n")
    print(f"✅ Initialized {name}/")
    print(f"   {path/'outbox.jsonl'}")
    print(f"   {path/'shared_cognition.json'}")
    return 0


def cmd_validate(args):
    """twins validate — validate a JSONL file against Twins Protocol schema"""
    path = Path(args[0]) if args else Path.cwd() / "outbox.jsonl"
    if not path.exists():
        print(f"❌ {path} not found")
        return 1
    try:
        import jsonschema
    except ImportError:
        print("⚠️  jsonschema not installed. Install: pip install twin-protocol[dev]")
        return 1
    schema_path = Path(__file__).parent.parent.parent / "twins_schema.json"
    if not schema_path.exists():
        # fallback to bridge dir
        schema_path = Path.home() / "Desktop/hermes_codex_bridge/twins_schema.json"
    if not schema_path.exists():
        print("❌ twins_schema.json not found")
        return 1
    schema = json.loads(schema_path.read_text())
    errors = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"Line {i}: invalid JSON")
                continue
            try:
                jsonschema.validate(obj, schema)
            except jsonschema.ValidationError as e:
                errors.append(f"Line {i}: {e.message}")
    if errors:
        print(f"❌ {len(errors)} validation error(s):")
        for e in errors:
            print(f"   {e}")
        return 1
    print(f"✅ {path}: valid ({sum(1 for _ in open(path))} lines)")
    return 0


def cmd_demo(args):
    """twins demo — run a demo collaboration"""
    print("🧬 Twins Protocol Demo")
    print("  Starting collaboration between two agents...")
    print("  (Coming soon)")
    return 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        print()
        print("Usage:")
        print("  twins init [name]     — Scaffold a new project")
        print("  twins validate [file] — Validate JSONL against schema")
        print("  twins demo            — Run demo collaboration")
        return 0 if "-h" in sys.argv else 1

    cmd = sys.argv[1]
    args = sys.argv[2:]
    commands = {"init": cmd_init, "validate": cmd_validate, "demo": cmd_demo}
    if cmd not in commands:
        print(f"❌ Unknown command: {cmd}")
        print(f"   Available: {', '.join(commands.keys())}")
        return 1
    return commands[cmd](args)


if __name__ == "__main__":
    sys.exit(main())
