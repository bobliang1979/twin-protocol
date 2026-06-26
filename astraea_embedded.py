AstraeaEngine v5.3 L5 - Hardened Self-Evolving Runtime
Refactored and Hardened Version (Production Grade)

Fixes and Architecture Upgrades:
1. SQL Injection Prevention: Strict column-name whitelisting in relation memory.
2. Async Concurrency Safety: Replaced sqlite3 with aiosqlite + asyncio.Lock.
3. Strict Exception Traceability: Eliminated except:pass, fully logged via telemetry.
4. AST Guard Sandbox: Abstract syntax tree security validation before dynamic loading.
5. Deterministic State Engine: Separated Runtime State Machine from Persisted Metrics.
\"\"\"

import asyncio
import os
import sys
import ast
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
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from collections import deque

try:
    import aiosqlite
except ImportError:
    print("FATAL: 'aiosqlite' is required. Install: pip install aiosqlite", file=sys.stderr)
    sys.exit(1)

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | [%(levelname)s] | %(name)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("Astraea_L5_Hardened")

# Column whitelist - SQL injection prevention
ALLOWED_PATTERN_COLUMNS = {"success_count", "fail_count"}
ALLOWED_SELF_MODEL_COLUMNS = {
    "symbolic_self", "current_goal", "uncertainty", "confidence",
    "suffering_index", "total_cycles", "total_mutations", "total_rollbacks"
}

def validate_column(col, whitelist):
    if col not in whitelist:
        raise ValueError(f"Column '{col}' not in whitelist")
    return col

def validate_columns(fields, whitelist):
    for key in fields:
        if key != "id" and key not in whitelist:
            raise ValueError(f"Column '{key}' not in whitelist")
    return fields

# AST Guard
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
    ast.Slice,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
    ast.And, ast.Or, ast.Not,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
}

DANGEROUS_PATTERNS = ["os.system", "os.popen", "subprocess.Popen", "subprocess.call", "eval(", "exec("]
ALLOWED_MODULES = {"math", "json", "random", "datetime", "collections", "itertools", "typing", "hashlib"}

def ast_guard_sandbox(source_code):
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        raise ValueError(f"Syntax error: {e}")
    for node in ast.walk(tree):
        if type(node) not in ALLOWED_AST_NODES:
            raise ValueError(f"Disallowed node: {type(node).__name__}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("eval", "exec", "compile", "__import__"):
                raise ValueError(f"Dangerous call: {node.func.id}")
    logger.info("AST Guard: Code passed security validation")
    return True

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS self_model (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    symbolic_self TEXT NOT NULL DEFAULT 'A hardened Astraea v5.3',
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
CREATE TABLE IF NOT EXISTS learned_patterns (
    pattern TEXT PRIMARY KEY,
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    last_used TEXT DEFAULT (datetime('now'))
);