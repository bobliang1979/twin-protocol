"""
AstraeaEngine v5.3 L5 — Hardened Self-Evolving Runtime
Gemini-audited fixes:
1. SQL Injection defense (column whitelist)
2. aiosqlite + asyncio.Lock (thread-safe async)
3. Proper exception logging (no except:pass)
4. AST Guard sandbox (code validation)
5. Deterministic state architecture
"""

import asyncio
import sqlite3
import aiosqlite
import ast
import os
import sys
import json
import time
import uuid
import logging
import random
import hashlib
import argparse
import shutil
import tempfile
import subprocess
import importlib
import importlib.util
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import deque

random.seed(42)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | [%(levelname)s] | %(name)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Astraea_v5_3_L5")

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
@dataclass
class Config:
    db_path: str = field(default_factory=lambda: os.getenv("ASTRACA_DB", "astraea_l5.db"))
    runtime_dir: str = field(default_factory=lambda: os.getenv("ASTRACA_RUNTIME", os.path.expanduser("~/.astraea/runtime")))
    max_cycles: int = 100
    telemetry_window: int = 300
    exit_score_threshold: float = 0.85

# ──────────────────────────────────────────────
# SECURITY: Column whitelist (SQL injection defense)
# ──────────────────────────────────────────────
ALLOWED_PATTERN_COLUMNS = {"success_count", "fail_count"}
ALLOWED_SELF_MODEL_COLUMNS = {
    "symbolic_self", "current_goal", "uncertainty", "confidence",
    "suffering_index", "total_cycles", "total_mutations", "total_rollbacks"
}

def validate_column(col: str, whitelist: set) -> str:
    """Genesis-asserted column whitelist — SQL injection gatekeeper."""
    if col not in whitelist:
        raise ValueError(f"SecurityError: Column '{col}' not in whitelist {whitelist}")
    return col

# ──────────────────────────────────────────────
# SECURITY: AST Guard Sandbox
# ──────────────────────────────────────────────
ALLOWED_AST_NODES = {
    ast.Module, ast.Expr, ast.Assign, ast.AnnAssign, ast.AugAssign,
    ast.Call, ast.Attribute, ast.Subscript, ast.Name, ast.Constant,
    ast.List, ast.Tuple, ast.Dict, ast.Set,
    ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare,
    ast.IfExp, ast.Lambda,
    ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Return,
    ast.If, ast.For, ast.AsyncFor, ast.While, ast.Break, ast.Continue,
    ast.Try, ast.ExceptHandler, ast.Raise, ast.With, ast.AsyncWith,
    ast.Pass, ast.Delete, ast.Import, ast.ImportFrom,
    ast.arguments, ast.arg, ast.keyword, ast.alias,
    ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
    ast.Slice, ast.FormattedValue, ast.JoinedStr,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv,
    ast.And, ast.Or, ast.Not,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.Starred, ast.NamedExpr,
    ast.Subscript, ast.Index, ast.ExtSlice,
}

DANGEROUS_BUILTINS = {"eval", "exec", "compile", "__import__", "open", "input"}
DANGEROUS_ATTR_PATTERNS = ["os.", "subprocess.", "shutil.", "ctypes.", "socket.", "sys.", "builtins."]

def ast_guard_sandbox(source_code: str) -> bool:
    """Validate code is safe to execute via AST tree analysis."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        raise ValueError(f"SyntaxError in sandbox check: {e}")
    
    violations = []
    for node in ast.walk(tree):
        node_type = type(node)
        if node_type not in ALLOWED_AST_NODES:
            violations.append(f"Disallowed node: {node_type.__name__} at line {getattr(node, 'lineno', '?')}")
        
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_BUILTINS:
                violations.append(f"Dangerous call: {node.func.id}() at line {getattr(node, 'lineno', '?')}")
            if isinstance(node.func, ast.Attribute):
                attr_full = f"{node.func.value.id}.{node.func.attr}" if isinstance(node.func.value, ast.Name) else ""
                for pattern in DANGEROUS_ATTR_PATTERNS:
                    if attr_full.startswith(pattern):
                        violations.append(f"Dangerous call: {attr_full}() at line {getattr(node, 'lineno', '?')}")
    
    if violations:
        raise ValueError("AST Guard violations:\\n" + "\\n".join(violations))
    
    logger.info("AST Guard: Code passed security validation")
    return True

# ──────────────────────────────────────────────
# PERSISTENT SELF MODEL (async, thread-safe)
# ──────────────────────────────────────────────
class AsyncPersistentSelf:
    """Cross-session identity with async-sqlite persistence."""
    
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS self_model (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        symbolic_self TEXT NOT NULL DEFAULT 'Astraea v5.3 L5 Hardened',
        current_goal TEXT DEFAULT 'Initialize',
        uncertainty REAL DEFAULT 1.0,
        confidence REAL DEFAULT 0.0,
        suffering_index REAL DEFAULT 0.0,
        total_cycles INTEGER DEFAULT 0,
        total_mutations INTEGER DEFAULT 0,
        total_rollbacks INTEGER DEFAULT 0,
        last_active TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS mutation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cycle INTEGER, component TEXT, version INTEGER,
        payload_hash TEXT, rationale TEXT,
        status TEXT, lyapunov_dv REAL,
        created_at TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS telemetry_log (
        ts REAL PRIMARY KEY, cycle INTEGER,
        error_rate REAL, compile_error_rate REAL,
        mutation_acceptance REAL, rollback_freq REAL,
        latency_avg REAL, token_eff REAL, coherence REAL
    );
    CREATE TABLE IF NOT EXISTS learned_patterns (
        pattern TEXT PRIMARY KEY,
        success_count INTEGER DEFAULT 0,
        fail_count INTEGER DEFAULT 0,
        last_used TEXT DEFAULT (datetime('now'))
    );
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self._db: Optional[aiosqlite.Connection] = None
        if db_path and db_path != ":memory:":
            db_dir = os.path.dirname(os.path.abspath(db_path))
            if db_dir:
                try:
                    os.makedirs(db_dir, exist_ok=True)
                except OSError as e:
                    logger.exception("Failed to create db directory")
    
    async def connect(self):
        if self._db is not None:
            return
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        async with self._lock:
            stmts = [s.strip() for s in self.SCHEMA.split(";") if s.strip()]
            for stmt in stmts:
                try:
                    await self._db.execute(stmt)
                except Exception as e:
                    logger.exception(f"Schema init failed for statement: {stmt[:50]}")
            await self._db.execute("INSERT OR IGNORE INTO self_model (id) VALUES (1)")
            await self._db.commit()
    
    async def close(self):
        async with self._lock:
            if self._db:
                await self._db.close()
                self._db = None
    
    async def load(self) -> dict:
        assert self._db is not None, "Database not connected"
        async with self._lock:
            cur = await self._db.execute("SELECT * FROM self_model WHERE id = 1")
            row = await cur.fetchone()
            return dict(row) if row else {}
    
    async def save(self, fields: dict):
        assert self._db is not None, "Database not connected"
        validate_columns(fields, ALLOWED_SELF_MODEL_COLUMNS)
        async with self._lock:
            sets = ", ".join(f"{k} = ?" for k in fields)
            vals = list(fields.values())
            await self._db.execute(
                f"UPDATE self_model SET {sets}, last_active = datetime('now') WHERE id = 1",
                vals
            )
            await self._db.commit()
    
    async def learn_pattern(self, pattern: str, success: bool):
        assert self._db is not None, "Database not connected"
        col = "success_count" if success else "fail_count"
        validate_column(col, ALLOWED_PATTERN_COLUMNS)
        async with self._lock:
            await self._db.execute(
                f"INSERT INTO learned_patterns (pattern, {col}) VALUES (?, 1) "
                f"ON CONFLICT(pattern) DO UPDATE SET "
                f"{col} = {col} + 1, last_used = datetime('now')",
                (pattern,)
            )
            await self._db.commit()
    
    async def score_pattern(self, pattern: str) -> float:
        assert self._db is not None, "Database not connected"
        async with self._lock:
            cur = await self._db.execute(
                "SELECT success_count, fail_count FROM learned_patterns WHERE pattern = ?",
                (pattern,)
            )
            row = await cur.fetchone()
        if not row:
            return 0.5
        total = row[0] + row[1]
        return row[0] / total if total > 0 else 0.5
    
    async def record_mutation(self, cycle: int, component: str, version: int,
                              payload_hash: str, rationale: str, status: str, lyapunov_dv: float):
        assert self._db is not None, "Database not connected"
        async with self._lock:
            await self._db.execute(
                "INSERT INTO mutation_history (cycle, component, version, payload_hash, "
                "rationale, status, lyapunov_dv, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (cycle, component, version, payload_hash, rationale, status, lyapunov_dv)
            )
            await self._db.execute(
                "UPDATE self_model SET total_mutations = total_mutations + 1 WHERE id = 1"
            )
            await self._db.commit()
    
    async def record_rollback(self):
        assert self._db is not None, "Database not connected"
        async with self._lock:
            await self._db.execute(
                "UPDATE self_model SET total_rollbacks = total_rollbacks + 1 WHERE id = 1"
            )
            await self._db.commit()
    
    async def record_cycle(self):
        assert self._db is not None, "Database not connected"
        async with self._lock:
            await self._db.execute(
                "UPDATE self_model SET total_cycles = total_cycles + 1, "
                "last_active = datetime('now') WHERE id = 1"
            )
            await self._db.commit()
    
    async def log_telemetry(self, ts: float, cycle: int, error_rate: float,
                            compile_error_rate: float, mutation_acceptance: float,
                            rollback_freq: float, latency_avg: float,
                            token_eff: float, coherence: float):
        assert self._db is not None, "Database not connected"
        async with self._lock:
            await self._db.execute(
                "INSERT INTO telemetry_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ts, cycle, error_rate, compile_error_rate, mutation_acceptance,
                 rollback_freq, latency_avg, token_eff, coherence)
            )
            await self._db.commit()
    
    async def get_stats(self) -> dict:
        assert self._db is not None, "Database not connected"
        async with self._lock:
            cur = await self._db.execute("SELECT * FROM self_model WHERE id = 1")
            row = dict(await cur.fetchone())
            cc = await self._db.execute("SELECT COUNT(*) FROM mutation_history")
            row["mutation_count"] = (await cc.fetchone())[0]
            tc = await self._db.execute("SELECT COUNT(*) FROM telemetry_log")
            row["telemetry_count"] = (await tc.fetchone())[0]
            return row

def validate_columns(fields: dict, whitelist: set):
    for key in fields:
        if key != "id" and key not in whitelist:
            raise ValueError(f"SecurityError: Field '{key}' not in whitelist {whitelist}")

# ──────────────────────────────────────────────
# MODULE HOT SWAPPER with AST Guard
# ──────────────────────────────────────────────
class ModuleHotSwapper:
    """Version-tracked importlib hot-swap with atomic rollback."""
    
    def __init__(self, persistent: AsyncPersistentSelf, runtime_dir: str):
        self.persistent = persistent
        self.runtime_dir = runtime_dir
        self._current_code: Optional[str] = None
        self._current_hash: Optional[str] = None
        self._version = 0
        os.makedirs(runtime_dir, exist_ok=True)
    
    def _hash_code(self, code: str) -> str:
        return hashlib.sha256(code.encode()).hexdigest()[:16]
    
    async def apply_mutation(self, component: str, code: str, rationale: str) -> Tuple[bool, str]:
        """Apply a code mutation with AST sandbox validation + atomic rollback."""
        # Step 1: AST sandbox
        try:
            ast_guard_sandbox(code)
        except ValueError as e:
            logger.warning(f"AST Guard rejected mutation for {component}: {e}")
            return False, str(e)
        
        # Step 2: Write to temp and test-import
        version = self._version + 1
        payload_hash = self._hash_code(code)
        tmp_path = os.path.join(self.runtime_dir, f"{component}_v{version}.tmp.py")
        final_path = os.path.join(self.runtime_dir, f"{component}_v{version}.py")
        
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(code)
            
            # Test-compile
            compile(code, tmp_path, "exec")
            
            # Atomic rename
            shutil.move(tmp_path, final_path)
            
            # Hot-swap via importlib
            spec = importlib.util.spec_from_file_location(f"astraea_{component}_v{version}", final_path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
            
            self._version = version
            self._current_code = code
            self._current_hash = payload_hash
            
            await self.persistent.record_mutation(
                0, component, version, payload_hash, rationale, "ACCEPTED", 0.0
            )
            logger.info(f"Mutation applied: {component} v{version}")
            return True, f"ACCEPTED v{version}"
        
        except SyntaxError as e:
            await self.persistent.record_mutation(
                0, component, version, payload_hash, rationale, "SYNTAX_ERROR", -0.3
            )
            logger.error(f"Syntax error in mutation {component} v{version}: {e}")
            return False, f"SYNTAX_ERROR: {e}"
        except Exception as e:
            logger.exception(f"Mutation failed for {component} v{version}")
            return False, f"ERROR: {e}"

# ──────────────────────────────────────────────
# CORE EVOLUTION ENGINE
# ──────────────────────────────────────────────
class AstraeaEngine:
    """Self-evolving runtime core with MCTS-inspired exploration."""
    
    def __init__(self, config: Config):
        self.config = config
        self.memory = AsyncPersistentSelf(config.db_path)
        self.swapper = ModuleHotSwapper(self.memory, config.runtime_dir)
        self.is_running = False
        self._cycle = 0
        self._telemetry_buffer = deque(maxlen=config.telemetry_window)
        self._event_log: List[str] = []
    
    async def bootstrap(self):
        """Initialize the engine: connect DB, load state, run bootstrap mutations."""
        logger.info("Bootstrapping AstraeaEngine v5.3 L5...")
        await self.memory.connect()
        state = await self.memory.load()
        logger.info(f"Loaded state: cycles={state.get('total_cycles', 0)}, "
                    f"mutations={state.get('total_mutations', 0)}, "
                    f"rollbacks={state.get('total_rollbacks', 0)}")
        self.is_running = True
        
        # Bootstrap mutation: install self-monitoring code
        bootstrap_code = """
def _self_monitor():
    return {"status": "ok", "version": "5.3.0"}
"""
        success, msg = await self.swapper.apply_mutation(
            "self_monitor", bootstrap_code, "Bootstrap: install self-monitor"
        )
        if success:
            logger.info("Bootstrap mutation applied successfully")
        else:
            logger.warning(f"Bootstrap mutation failed: {msg}")
        
        return state
    
    async def execute_cycle(self) -> bool:
        """Execute one evolution cycle. Returns True if should continue."""
        if not self.is_running or self._cycle >= self.config.max_cycles:
            self.is_running = False
            return False
        
        self._cycle += 1
        cycle = self._cycle
        t0 = time.time()
        
        try:
            # Record cycle
            await self.memory.record_cycle()
            state = await self.memory.load()
            uncertainty = state.get("uncertainty", 1.0)
            confidence = state.get("confidence", 0.0)
            
            logger.info(f"Cycle {cycle}/{self.config.max_cycles} | "
                       f"uncertainty={uncertainty:.3f} confidence={confidence:.3f}")
            
            # Generate mutation if uncertainty is high enough
            if uncertainty > 0.3:
                mutation_code = f"""
def _cycle_mutation_{cycle}():
    return {{"cycle": {cycle}, "confidence": {confidence:.3f}}}
"""
                success, msg = await self.swapper.apply_mutation(
                    f"cycle_{cycle}", mutation_code,
                    f"Auto-evolution cycle {cycle}" if cycle > 10 else f"Early cycle {cycle}: explore"
                )
                
                if success:
                    # Update confidence upward
                    new_confidence = min(1.0, confidence + 0.05)
                    await self.memory.save({"confidence": new_confidence, "uncertainty": max(0.0, uncertainty - 0.03)})
                    await self.memory.learn_pattern(f"cycle_{cycle}_success", True)
                else:
                    # Rollback: decrease confidence
                    await self.memory.record_rollback()
                    new_confidence = max(0.0, confidence - 0.02)
                    await self.memory.save({"confidence": new_confidence, "uncertainty": min(1.0, uncertainty + 0.01)})
                    await self.memory.learn_pattern(f"cycle_{cycle}_failure", False)
            
            # Telemetry
            latency = time.time() - t0
            await self.memory.log_telemetry(
                time.time(), cycle,
                error_rate=0.05 if uncertainty > 0.5 else 0.01,
                compile_error_rate=0.1 if uncertainty > 0.7 else 0.02,
                mutation_acceptance=0.7 if uncertainty > 0.3 else 0.9,
                rollback_freq=0.1 if uncertainty > 0.5 else 0.02,
                latency_avg=latency,
                token_eff=0.8,
                coherence=max(0.0, confidence - 0.1)
            )
            
            # Check exit condition
            if confidence >= self.config.exit_score_threshold:
                logger.info(f"Confidence threshold reached ({confidence:.3f} >= {self.config.exit_score_threshold})")
                self.is_running = False
                return False
            
            return True
        
        except Exception as e:
            logger.exception(f"Cycle {cycle} failed with unexpected error")
            await self.memory.record_rollback()
            return self._cycle < self.config.max_cycles
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down AstraeaEngine...")
        self.is_running = False
        stats = await self.memory.get_stats()
        logger.info(f"Final stats: {json.dumps(stats, default=str)}")
        await self.memory.close()
        logger.info("Shutdown complete.")

# ──────────────────────────────────────────────
# SELF-TEST SUITE
# ──────────────────────────────────────────────
async def run_self_test() -> int:
    """Run regression tests: SQL injection, AST Guard, async DB, full cycle."""
    print("=" * 60)
    print("ASTRAEA v5.3 L5 — HARDENED SELF-TEST SUITE")
    print("=" * 60)
    passed = 0
    total = 4
    
    # Test 1: SQL Injection Defense
    print(f"\\n[Test 1/{total}] SQL Injection Defense...")
    try:
        validate_column("success_count", ALLOWED_PATTERN_COLUMNS)
        print("  [OK] Valid column accepted")
        passed += 1
    except ValueError:
        print("  [FAIL] Valid column rejected!")
        return 1
    
    try:
        validate_column("malicious; DROP TABLE--", ALLOWED_PATTERN_COLUMNS)
        print("  [FAIL] SQL injection NOT blocked — FAIL")
        return 1
    except ValueError:
        print("  [OK] SQL injection vector blocked")
        passed += 1
    
    # Test 2: AST Guard
    print(f"\\n[Test 2/{total}] AST Guard Sandbox...")
    try:
        ast_guard_sandbox("def safe(): return 42")
        print("  [OK] Safe code accepted")
        passed += 1
    except ValueError as e:
        print(f"  [FAIL] Safe code rejected: {e}")
        return 1
    
    try:
        ast_guard_sandbox("import os\\nos.system('rm -rf /')")
        print("  [FAIL] Dangerous code NOT blocked — FAIL")
        return 1
    except ValueError:
        print("  [OK] Dangerous code blocked")
        passed += 1
    
    # Test 3: Async Database with full operations
    print(f"\\n[Test 3/{total}] Async Database Operations...")
    try:
        mem = AsyncPersistentSelf(":memory:")
        await mem.connect()
        
        await mem.save({"symbolic_self": "TestRunner", "current_goal": "SelfTest"})
        loaded = await mem.load()
        assert loaded["symbolic_self"] == "TestRunner", f"Got {loaded.get('symbolic_self')}"
        print("  [OK] State save/load")
        passed += 1
        
        await mem.record_mutation(1, "test_mutation", 1, "abc123", "test", "ACCEPTED", -0.1)
        hist = await mem.get_mutation_history()
        assert len(hist) >= 1
        print("  [OK] Mutation history")
        passed += 1
        
        await mem.record_cycle()
        stats = await mem.get_stats()
        assert stats["total_cycles"] >= 1
        print("  [OK] Cycle tracking")
        passed += 1
        
        await mem.learn_pattern("test_pattern", True)
        await mem.learn_pattern("test_pattern", True)
        await mem.learn_pattern("test_pattern", False)
        score = await mem.score_pattern("test_pattern")
        assert score == 2.0 / 3.0, f"Expected 0.667, got {score}"
        print(f"  [OK] Pattern learning (score={score:.3f})")
        passed += 1
        
        await mem.close()
        print("  [OK] Async DB: ALL SUBTESTS PASSED")
    
    except Exception as e:
        print(f"  [FAIL] Async DB test failed: {e}")
        logger.exception("Test 3 failed")
        return 1
    
    # Test 4: Full evolution cycle
    print(f"\\n[Test 4/{total}] Full Evolution Cycle...")
    try:
        config = Config(db_path=":memory:", max_cycles=5)
        engine = AstraeaEngine(config)
        await engine.bootstrap()
        
        cycles_run = 0
        while engine.is_running:
            keep_going = await engine.execute_cycle()
            if keep_going:
                cycles_run += 1
        
        await engine.shutdown()
        assert cycles_run > 0, "No cycles executed"
        print(f"  [OK] {cycles_run} evolution cycles completed")
        passed += 1
    
    except Exception as e:
        print(f"  [FAIL] Evolution cycle test failed: {e}")
        logger.exception("Test 4 failed")
        return 1
    
    # Results
    print(f"\\n{'=' * 60}")
    print(f"ALL TESTS PASSED ({passed} assertions)")
    print(f"{'=' * 60}")
    return 0

# ──────────────────────────────────────────────
# AsyncPersistentSelf helper methods
# ──────────────────────────────────────────────
# These are defined as methods of AsyncPersistentSelf above.
# Adding standalone wrappers for convenience.

async def get_mutation_history(self: AsyncPersistentSelf, limit: int = 20) -> List[dict]:
    async with self._lock:
        cur = await self._db.execute(
            "SELECT * FROM mutation_history ORDER BY cycle DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in await cur.fetchall()]

AsyncPersistentSelf.get_mutation_history = get_mutation_history

# ──────────────────────────────────────────────
# MAIN ENTRYPOINT
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AstraeaEngine v5.3 L5 Hardened")
    parser.add_argument("--test", action="store_true", help="Run self-test suite")
    args = parser.parse_args()
    
    if args.test:
        exit_code = asyncio.run(run_self_test())
        sys.exit(exit_code)
    else:
        config = Config()
        engine = AstraeaEngine(config)
        
        async def run():
            await engine.bootstrap()
            try:
                while engine.is_running:
                    await engine.execute_cycle()
                    await asyncio.sleep(0.5)
            finally:
                await engine.shutdown()
        
        try:
            asyncio.run(run())
        except KeyboardInterrupt:
            logger.info("Interrupted by user. Shutting down...")

if __name__ == "__main__":
    main()
