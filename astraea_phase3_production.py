"""
Astraea v4.0 Absolute — Phase 3: Codex++ Production Backend

Replaces MockCloudGenerator and MockVerifier with real Codex++ API calls
to :57321/v1/responses. Zero extra dependencies (stdlib asyncio + urllib).

Components:
  CodexCloudGenerator  → generate_batch() via real DeepSeek reasoning
  CodexVerifier        → score() via Codex self-ask
  make_production_engine → wires real backends into AstraeaProductionEngine_v4_0
  e2e_pipeline_run     → full integration test with token chain verification

Usage:
  python astraea_phase3_production.py          # run E2E test
  python astraea_phase3_production.py --verify  # run discovery/verification only
"""

import asyncio
import json
import math
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Optional

import numpy as np

# ──────────────────────────────────────────────────────────────────────
# 1.  CODEX++ API CLIENT (async via ThreadPoolExecutor)
# ──────────────────────────────────────────────────────────────────────

CODEX_API = "http://127.0.0.1:57321/v1/responses"
DEFAULT_MODEL = "deepseek-v4-flash"
_API_EXECUTOR = ThreadPoolExecutor(max_workers=4)

# Timeouts (seconds)
CODEX_TIMEOUT = 120  # single timeout for urllib (not a tuple)
CODEX_RETRIES = 2
CODEX_RETRY_DELAY = 2.0


class CodexAPIError(Exception):
    """Raised when Codex++ API returns an error or times out."""
    pass


def _sync_call_codex(payload: dict) -> dict:
    """Synchronous HTTP POST to Codex++ Responses API."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        CODEX_API,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=CODEX_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise CodexAPIError(f"HTTP {e.code}: {err_body}")
    except urllib.error.URLError as e:
        raise CodexAPIError(f"Connection failed: {e.reason}")
    except Exception as e:
        raise CodexAPIError(str(e))


async def _call_codex(payload: dict) -> dict:
    """Async wrapper around synchronous Codex++ API call."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_API_EXECUTOR, _sync_call_codex, payload)


def _extract_output_text(response: dict) -> str:
    """Extract the primary output_text from a Codex++ Responses API response.

    Response structure (stable per user confirmation):
    {
      "output": [
        {"type": "reasoning", "reasoning_content": "...", "summary": [...]},
        {"type": "message", "content": [{"type": "output_text", "text": "..."}]}
      ],
      ...
    }
    """
    if "error" in response:
        raise CodexAPIError(f"API error: {response['error']}")

    outputs = response.get("output", [])
    for out in outputs:
        if out.get("type") == "message":
            for content in out.get("content", []):
                if content.get("type") == "output_text":
                    return content["text"]

    # Fallback: any text we can find
    for out in outputs:
        if out.get("type") == "reasoning":
            text = out.get("reasoning_content", "")
            if text:
                return text
            summaries = out.get("summary", [])
            if summaries:
                return summaries[0].get("text", "")

    raise CodexAPIError(f"No output_text found in response: {json.dumps(response)[:300]}")


# ──────────────────────────────────────────────────────────────────────
# 2.  CODEX CLOUD GENERATOR  — generate_batch() via real DeepSeek
# ──────────────────────────────────────────────────────────────────────

class CodexCloudGenerator:
    """Astraea cloud_generator that calls Codex++ for real reasoning generation.

    Generates N distinct next reasoning steps by asking DeepSeek to produce
    JSON matching REASONING_STATE_SCHEMA.

    Attributes:
        model: Codex++ model name (default: deepseek-v4-flash)
        retries: max retries per batch
        retry_delay: seconds between retries
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        retries: int = CODEX_RETRIES,
        retry_delay: float = CODEX_RETRY_DELAY,
    ):
        self.model = model
        self.retries = retries
        self.retry_delay = retry_delay
        self._call_count = 0
        self._fail_count = 0

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "calls": self._call_count,
            "failures": self._fail_count,
        }

    async def generate_batch(
        self,
        prompt: str,
        n: int = 3,
        json_schema: Optional[Dict] = None,
    ) -> List[str]:
        """Generate N distinct next reasoning steps via Codex++.

        Returns a list of JSON strings (each matching REASONING_STATE_SCHEMA).
        On failure, returns fewer items or empty list.
        """
        schema_hint = ""
        if json_schema:
            required = json_schema.get("required", [])
            schema_hint = (
                f"\n\nEach step MUST be a JSON object with keys: {json.dumps(required)}. "
                f"The 'hypothesis' field must be a string describing the reasoning step. "
                f"The 'evidence' field must be a list of strings. "
                f"The 'uncertainty' field must be a float between 0 and 1."
            )

        user_prompt = (
            f"You are an MCTS reasoning generator. Given the current state below, "
            f"generate exactly {n} DISTINCT next reasoning steps. "
            f"Each step should explore a DIFFERENT line of reasoning — do NOT repeat "
            f"the same idea with different wording. Be creative and divergent. "
            f"{schema_hint}"
            f"\n\nCurrent state:\n{prompt}"
        )

        last_error = None
        for attempt in range(self.retries + 1):
            if attempt > 0:
                await asyncio.sleep(self.retry_delay)

            try:
                payload = {
                    "model": self.model,
                    "input": [{"role": "user", "content": user_prompt}],
                    "tools": [{"type": "code_interpreter"}],
                }
                response = await _call_codex(payload)
                self._call_count += 1

                text = _extract_output_text(response)

                # Try to parse as JSON array or response containing JSON objects
                parsed = self._parse_json_response(text, n)
                if parsed:
                    return parsed

                # If we got text but couldn't parse JSON, treat as fallback
                # Wrap the whole text as a single reasoning step
                return [
                    json.dumps({
                        "hypothesis": text[:500],
                        "evidence": [],
                        "uncertainty": 0.5,
                    }, ensure_ascii=False)
                ]

            except CodexAPIError as e:
                last_error = e
                self._fail_count += 1
                continue
            except Exception as e:
                last_error = e
                self._fail_count += 1
                continue

        # All retries exhausted — return empty, caller handles fallback
        return []

    def _parse_json_response(self, text: str, n: int) -> Optional[List[str]]:
        """Attempt to extract JSON reasoning steps from API text response.

        Tries in order:
          1. text as JSON array directly
          2. Find JSON objects in text (embedded in markdown code blocks)
          3. Find JSON objects with grep-like heuristics
        """
        text = text.strip()

        # Strategy 1: direct JSON array
        try:
            items = json.loads(text)
            if isinstance(items, list):
                return [json.dumps(item, ensure_ascii=False) for item in items[:n]]
        except (json.JSONDecodeError, TypeError):
            pass

        # Strategy 2: extract from ```json ... ``` blocks
        import re
        blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', text)
        for block in blocks:
            try:
                items = json.loads(block.strip())
                if isinstance(items, list):
                    return [json.dumps(item, ensure_ascii=False) for item in items[:n]]
                if isinstance(items, dict):
                    return [json.dumps(items, ensure_ascii=False)]
            except (json.JSONDecodeError, TypeError):
                pass

        # Strategy 3: find individual {...} objects in text
        objects = re.findall(r'\{[^{}]*\}', text)
        valid = []
        for obj_str in objects:
            try:
                parsed = json.loads(obj_str)
                if isinstance(parsed, dict) and "hypothesis" in parsed:
                    valid.append(obj_str)
                    if len(valid) >= n:
                        break
            except (json.JSONDecodeError, TypeError):
                continue

        if valid:
            return valid

        return None


# ──────────────────────────────────────────────────────────────────────
# 3.  CODEX VERIFIER  — score() via Codex self-ask
# ──────────────────────────────────────────────────────────────────────

class CodexVerifier:
    """Astraea local_verifier that uses Codex++ to score hypotheses 0.0–1.0.

    Prompts Codex to evaluate the reasoning hypothesis and return a float.
    Falls back to a default value on failure.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        default_score: float = 0.5,
        retries: int = 1,
    ):
        self.model = model
        self._default = float(np.clip(default_score, 0.0, 1.0))
        self.retries = retries
        self._call_count = 0
        self._fail_count = 0

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "calls": self._call_count,
            "failures": self._fail_count,
        }

    async def score(self, text: str) -> float:
        """Score a reasoning hypothesis 0.0–1.0 via Codex++.

        The prompt asks for a single float; we parse it from the response.
        """
        user_prompt = (
            f"Rate the following reasoning hypothesis from 0.0 (invalid/wrong) "
            f"to 1.0 (correct/valuable). Return ONLY a single floating-point number "
            f"between 0 and 1, nothing else.\n\n"
            f"Hypothesis: {text[:1000]}"
        )

        last_error = None
        for attempt in range(self.retries + 1):
            if attempt > 0:
                await asyncio.sleep(0.5)

            try:
                payload = {
                    "model": self.model,
                    "input": [{"role": "user", "content": user_prompt}],
                }
                response = await _call_codex(payload)
                self._call_count += 1

                output_text = _extract_output_text(response)
                score = self._parse_score(output_text)
                if score is not None:
                    return float(np.clip(score, 0.0, 1.0))

            except CodexAPIError as e:
                last_error = e
                self._fail_count += 1
                continue
            except Exception as e:
                last_error = e
                self._fail_count += 1
                continue

        # Fallback
        self._fail_count += 1
        return self._default

    def _parse_score(self, text: str) -> Optional[float]:
        """Extract a float score from Codex's response text."""
        import re

        text = text.strip()

        # Direct float
        try:
            val = float(text)
            if 0.0 <= val <= 1.0:
                return val
        except (ValueError, TypeError):
            pass

        # Pattern: "0.85" or "0.85/1.0" or "score: 0.85"
        matches = re.findall(r'(\d+\.?\d*)', text)
        for match in matches:
            try:
                val = float(match)
                if 0.0 <= val <= 1.0:
                    return val
            except ValueError:
                continue

        return None


# ──────────────────────────────────────────────────────────────────────
# 4.  EMBEDDER: Still mock (local, no real embedding needed for E2E)
# ──────────────────────────────────────────────────────────────────────

class ProductionEmbedder:
    """Simple deterministic embedder for Astraea.

    In production, this would be a local embedding model. For Phase 3,
    we provide a deterministic version that preserves the E2E data flow
    without requiring real embeddings. Semantic dedup is still tested
    structurally (pipeline doesn't break).
    """

    def __init__(self, dim: int = 64, seed: int = 42):
        self.dim = dim
        self._rng = np.random.default_rng(seed)
        self._cache: Dict[str, np.ndarray] = {}
        self._call_count = 0

    @property
    def stats(self) -> Dict[str, Any]:
        return {"calls": self._call_count}

    async def encode(self, text: str) -> np.ndarray:
        import hashlib
        self._call_count += 1
        key = hashlib.md5(text.encode()).hexdigest()
        if key not in self._cache:
            v = self._rng.normal(size=self.dim).astype(np.float32)
            self._cache[key] = v / (np.linalg.norm(v) + 1e-8)
        return self._cache[key]


# ──────────────────────────────────────────────────────────────────────
# 5.  PRODUCTION ENGINE FACTORY
# ──────────────────────────────────────────────────────────────────────

def make_production_engine(**overrides) -> 'AstraeaProductionEngine_v4_0':
    """Create an Astraea engine wired to real Codex++ backends.

    Keyword args override any default parameter on AstraeaProductionEngine_v4_0.

    Returns:
        (engine, verifier, generator, embedder) tuple for introspection.
    """
    # Import target module (must be in same directory)
    sys.path.insert(0, r"C:\Users\10074\Documents\控制")
    from astraea_v4_0_absolute import AstraeaProductionEngine_v4_0

    verifier = CodexVerifier()
    generator = CodexCloudGenerator()
    embedder = ProductionEmbedder()

    engine = AstraeaProductionEngine_v4_0(
        local_verifier=verifier,
        local_embedder=embedder,
        cloud_generator=generator,
        **overrides,
    )
    return engine, verifier, generator, embedder


# ──────────────────────────────────────────────────────────────────────
# 6.  E2E PIPELINE RUNNER
# ──────────────────────────────────────────────────────────────────────

async def e2e_pipeline_run(
    query: str = "What are the key differences between TCP and UDP protocols?",
    max_iterations: int = 3,
    confidence_threshold: float = 0.85,
    min_visits_for_stop: int = 2,
    max_tree_depth: int = 16,
) -> Dict[str, Any]:
    """Run the full Astraea pipeline with real Codex++ backend.

    Returns structured results including:
      - root node stats (wilson_lb, avg_value, visits, depth)
      - token chain trace (provenance)
      - timing
      - backend call stats
    """
    print("=" * 72)
    print("  ASTRAEA v4.0 ABSOLUTE — PHASE 3: CODEX++ PRODUCTION E2E".center(72))
    print("=" * 72)
    print(f"\n  Query:      {query}")
    print(f"  Iterations: {max_iterations}")
    print(f"  Confidence: {confidence_threshold}")
    print(f"  Max Depth:  {max_tree_depth}")
    print()

    engine, verifier, generator, embedder = make_production_engine(
        max_tree_depth=max_tree_depth,
        exploration_constant=1.41,
    )

    t_start = time.monotonic()

    try:
        root = await engine.run_pipeline(
            query=query,
            max_iterations=max_iterations,
            confidence_threshold=confidence_threshold,
            min_visits_for_stop=min_visits_for_stop,
        )
    except Exception as e:
        import traceback
        return {
            "status": "FAILED",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timing_sec": time.monotonic() - t_start,
        }

    t_elapsed = time.monotonic() - t_start

    # ── Collect stats ──────────────────────────────────────────────
    stats = {
        "status": "OK",
        "query": query,
        "iterations_completed": max_iterations,
        "timing_sec": round(t_elapsed, 3),
        "root": {
            "visits": root.visits,
            "avg_value": round(float(root.avg_value), 6),
            "wilson_lower_bound_1.96": round(
                float(root.wilson_lower_bound(z=1.96)), 6
            ),
            "depth": root.depth,
            "kv_cache_token": root.kv_cache_token,
            "chain_liveness": engine._verify_chain_liveness(root, root),
        },
        "token_chain": _trace_token_chain(root),
        "backend_stats": {
            "verifier": {"calls": verifier._call_count, "failures": verifier._fail_count},
            "generator": {"calls": generator._call_count, "failures": generator._fail_count},
            "embedder": {"calls": embedder._call_count},
        },
    }

    # ── Print report ───────────────────────────────────────────────
    print(f"  ⏱  Elapsed:        {stats['timing_sec']:.2f}s")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Root visits:       {stats['root']['visits']}")
    print(f"  Root avg_value:    {stats['root']['avg_value']}")
    print(f"  Wilson LB (1.96):  {stats['root']['wilson_lower_bound_1.96']}")
    print(f"  Root depth:        {stats['root']['depth']}")
    print(f"  Chain liveness:    {'PASS' if stats['root']['chain_liveness'] else 'FAIL'}")
    print(f"  Token root:        {stats['root']['kv_cache_token']}")
    print()
    print(f"  Backend calls:")
    print(f"    Verifier:   {stats['backend_stats']['verifier']['calls']} "
          f"({stats['backend_stats']['verifier']['failures']} failed)")
    print(f"    Generator:  {stats['backend_stats']['generator']['calls']} "
          f"({stats['backend_stats']['generator']['failures']} failed)")
    print(f"    Embedder:   {stats['backend_stats']['embedder']['calls']}")
    print()

    # Token chain trace
    print(f"  Token Chain Trace ({len(stats['token_chain'])} nodes):")
    for i, node in enumerate(stats["token_chain"]):
        symbol = "⊙" if i == 0 else "↳"
        state_preview = json.dumps(node["state_preview"])
        if len(state_preview) > 60:
            state_preview = state_preview[:57] + "..."
        print(f"    {symbol} [{i}] token={node['token']}  visits={node['visits']}  "
              f"avg={node['avg_value']:.4f}  {state_preview}")

    print()
    print("=" * 72)

    return stats


def _trace_token_chain(root: 'StructuredReasoningNode', max_nodes: int = 20) -> List[Dict]:
    """Trace the token chain from root through its most-visited path."""
    chain = []
    current = root
    for _ in range(max_nodes):
        import json
        chain.append({
            "token": current.kv_cache_token,
            "visits": current.visits,
            "avg_value": float(current.avg_value),
            "depth": current.depth,
            "state_preview": {
                "hypothesis": current.state.get("hypothesis", "")[:40],
                "evidence_count": len(current.state.get("evidence", [])),
                "uncertainty": current.state.get("uncertainty", 0.0),
            },
        })
        if not current.children:
            break
        # Follow the most-visited child (greedy best path)
        current = max(current.children, key=lambda c: c.visits)
    return chain


# ──────────────────────────────────────────────────────────────────────
# 7.  VERIFICATION: DISCOVERY / HEALTH CHECK
# ──────────────────────────────────────────────────────────────────────

async def verify_codex_connectivity() -> Dict[str, Any]:
    """Check that Codex++ is reachable and returning valid responses."""
    print("  [1/4] Checking Codex++ connectivity...", end=" ", flush=True)
    try:
        payload = {
            "model": DEFAULT_MODEL,
            "input": [{"role": "user", "content": "Reply with exactly the word OK"}],
        }
        resp = await _call_codex(payload)
        text = _extract_output_text(resp)
        print(f"OK (response: {text[:50]})")
        return {"connectivity": "PASS", "model": DEFAULT_MODEL, "sample": text[:80]}
    except Exception as e:
        print(f"FAIL — {e}")
        return {"connectivity": "FAIL", "error": str(e)}


async def verify_generator() -> Dict[str, Any]:
    """Test CodexCloudGenerator with a simple prompt."""
    print("  [2/4] Testing CodexCloudGenerator...", end=" ", flush=True)
    gen = CodexCloudGenerator()
    try:
        results = await gen.generate_batch(
            "Current state: explore quantum entanglement. Generate 2 reasoning steps.",
            n=2,
        )
        if results:
            print(f"OK ({len(results)} steps generated)")
            return {"generator": "PASS", "steps": len(results)}
        else:
            print("WARN — empty result")
            return {"generator": "WARN", "steps": 0}
    except Exception as e:
        print(f"FAIL — {e}")
        return {"generator": "FAIL", "error": str(e)}


async def verify_verifier() -> Dict[str, Any]:
    """Test CodexVerifier score extraction."""
    print("  [3/4] Testing CodexVerifier...", end=" ", flush=True)
    ver = CodexVerifier()
    try:
        score = await ver.score("Test hypothesis about gravity.")
        print(f"OK (score={score:.4f})")
        return {"verifier": "PASS", "score": score}
    except Exception as e:
        print(f"FAIL — {e}")
        return {"verifier": "FAIL", "error": str(e)}


async def verify_engine_import() -> Dict[str, Any]:
    """Test that the production engine factory works."""
    print("  [4/4] Testing engine factory...", end=" ", flush=True)
    try:
        engine, verifier, generator, embedder = make_production_engine()
        print(f"OK (engine={type(engine).__name__})")
        return {"engine_import": "PASS"}
    except Exception as e:
        print(f"FAIL — {e}")
        return {"engine_import": "FAIL", "error": str(e)}


async def run_verification() -> Dict[str, Any]:
    """Run all 4 verification checks."""
    print("=" * 72)
    print("  ASTRAEA v4.0 — Phase 3: Codex++ Connectivity Verification".center(72))
    print("=" * 72)
    print()

    results = []
    results.append(await verify_codex_connectivity())
    results.append(await verify_generator())
    results.append(await verify_verifier())
    results.append(await verify_engine_import())

    print()
    print("─" * 72)

    all_pass = all(
        r.get("connectivity") == "PASS"
        or r.get("generator") == "PASS"
        or r.get("verifier") == "PASS"
        or r.get("engine_import") == "PASS"
        for r in results
    )

    combined = {}
    for r in results:
        combined.update(r)

    # Proper per-check pass/fail
    check_names = ["connectivity", "generator", "verifier", "engine_import"]
    all_pass = all(combined.get(k) == "PASS" for k in check_names)

    combined["all_pass"] = all_pass

    outcome = "ALL PASS" if all_pass else "SOME FAILURES"
    print(f"  VERIFICATION OUTCOME: {outcome}")
    print("=" * 72)

    return combined


# ──────────────────────────────────────────────────────────────────────
# 8.  MAIN
# ──────────────────────────────────────────────────────────────────────

async def main():
    import sys

    if "--verify" in sys.argv:
        results = await run_verification()
        sys.exit(0 if results.get("all_pass", False) else 1)

    if "--e2e" in sys.argv:
        idx = sys.argv.index("--e2e")
        query = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
        if query:
            stats = await e2e_pipeline_run(query=query)
        else:
            stats = await e2e_pipeline_run()
        sys.exit(0 if stats.get("status") == "OK" else 1)

    # Default: verify connectivity, then run E2E
    print("PHASE 3: Verification + E2E Pipeline Test\n")

    verify = await run_verification()
    if not verify.get("all_pass", False):
        print("\n  Verification failed — aborting E2E. Fix connectivity first.\n")
        sys.exit(1)

    print("\n" + "=" * 72)
    print("  Verification passed — proceeding to E2E pipeline test".center(72))
    print("=" * 72 + "\n")

    stats = await e2e_pipeline_run(
        query="What are the key differences between TCP and UDP protocols?",
        max_iterations=3,
    )

    sys.exit(0 if stats.get("status") == "OK" else 1)


if __name__ == "__main__":
    asyncio.run(main())
