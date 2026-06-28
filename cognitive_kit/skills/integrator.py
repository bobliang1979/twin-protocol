"""Skill Integration Engine"""
from pathlib import Path
from typing import Dict, List, Optional, Any
import json, re, time

class SkillParser:
    """Parse SKILL.md frontmatter and extract patterns."""

    @staticmethod
    def parse_skill(path: Path) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return None

        # Extract YAML frontmatter
        match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
        if not match:
            return {"name": path.parent.name, "description": "", "path": str(path)}

        meta = {}
        for line in match.group(1).strip().split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip().strip('"').strip("'")

        # Extract code blocks for patterns
        patterns = re.findall(r"```python\n(.*?)```", text, re.DOTALL)

        return {
            "name": meta.get("name", path.parent.name),
            "description": meta.get("description", ""),
            "path": str(path),
            "size": len(text),
            "patterns": len(patterns),
            "loaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    @staticmethod
    def scan_all() -> Dict[str, Dict]:
        skills = {}
        for subdir in SKILL_DIR.iterdir():
            if subdir.is_dir():
                skill_file = subdir / "SKILL.md"
                parsed = SkillParser.parse_skill(skill_file)
                if parsed:
                    skills[subdir.name] = parsed
        return skills


# ── Integration Engine ──

class SkillIntegrationEngine:
    """Main integration engine. Loads skills and applies patterns to runtime."""

    def __init__(self):
        self.registry: Dict[str, Dict] = {}
        self.breaker = DHGCircuitBreaker()
        self.health = CognitiveHealthField()
        self._load_registry()

    def _load_registry(self):
        if REGISTRY.exists():
            try:
                self.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
            except Exception:
                self.registry = {}

    def _save_registry(self):
        REGISTRY.write_text(
            json.dumps(self.registry, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def scan_and_register(self) -> Dict[str, Dict]:
        """Scan all skills and register new ones."""
        scanned = SkillParser.scan_all()
        for key, val in scanned.items():
            if key not in self.registry:
                self.registry[key] = val
                self.registry[key]["status"] = "registered"
            else:
                self.registry[key].update(val)
                self.registry[key]["status"] = "updated"
        self._save_registry()
        return self.registry

    def ensure_priority_skills(self) -> List[str]:
        """Ensure priority skills are registered."""
        loaded = []
        for skill_name in PRIORITY_SKILLS:
            skill_path = SKILL_DIR / skill_name / "SKILL.md"
            if skill_path.exists() and skill_name not in self.registry:
                parsed = SkillParser.parse_skill(skill_path)
                if parsed:
                    parsed["status"] = "priority"
                    self.registry[skill_name] = parsed
                    loaded.append(skill_name)
            elif skill_name in self.registry:
                self.registry[skill_name]["status"] = "priority"
                loaded.append(skill_name)
        if loaded:
            self._save_registry()
        return loaded

    def get_health_report(self) -> Dict:
        health = self.health.report()
        health["health_score"] = self.health.health_score()
        health["breaker_tripped"] = self.breaker.tripped
        health["breaker_trip_count"] = self.breaker.trip_count
        health["registered_skills"] = len(self.registry)
        health["priority_skills"] = len([s for s in self.registry.values()
                                          if s.get("status") == "priority"])
        return health

    def get_skills_by_priority(self) -> Dict[str, List[Dict]]:
        """Group skills by priority (parsed from name hints or status)."""
        result = {"P0": [], "P1": [], "P2": [], "unclassified": []}
        for name, skill in self.registry.items():
            priority = "unclassified"
            if skill.get("status") == "priority":
                priority = "P0"
            elif "P0" in name or "production" in name or "kernel" in name:
                priority = "P0"
            result[priority].append(skill)
        return result

    def summary(self) -> str:
        by_pri = self.get_skills_by_priority()
        lines = [f"Skills: {len(self.registry)} registered"]
        for pri in ["P0", "P1", "P2", "unclassified"]:
            if by_pri[pri]:
                names = [s.get("name", k) for k, s in self.registry.items()
                         if s in by_pri[pri]]
                lines.append(f"  {pri}: {', '.join(names[:10])}")
        lines.append(f"Health: {self.health.health_score():.2f}")
        lines.append(f"Breaker: {'TRIPPED' if self.breaker.tripped else 'OK'} ({self.breaker.trip_count} trips)")
        return "\n".join(lines)


# ── CLI ──

def cmd_scan():
    engine = SkillIntegrationEngine()
    count = len(engine.scan_and_register())
    priority = engine.ensure_priority_skills()
    print(f"Registered: {count} total, {len(priority)} priority")
    print(engine.summary())

def cmd_status():
    engine = SkillIntegrationEngine()
    print(engine.summary())
    print(f"\nRegistry file: {REGISTRY}")
    if REGISTRY.exists():
        print(f"Registry size: {REGISTRY.stat().st_size} bytes")

def cmd_integrate():
    engine = SkillIntegrationEngine()
    engine.scan_and_register()
    engine.ensure_priority_skills()

    # Write integration manifest for daemon
    manifest = {
        "breaker": {
            "threshold": 0.15,
            "window": 100,
            "active": True
        },
        "failure_modes": list(FailureModeClassifier.MODES.keys()),
        "health_dimensions": list(engine.health.metrics.keys()),
        "priority_skills_loaded": PRIORITY_SKILLS,
        "integrated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    manifest_path = BASE / ".skill_integration_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Integration manifest written.")
    print(engine.summary())

if __name__ == "__main__":
    if "--scan" in sys.argv:
        cmd_scan()
    elif "--status" in sys.argv:
        cmd_status()
    elif "--integrate" in sys.argv:
        cmd_integrate()
    else:
        cmd_integrate()

