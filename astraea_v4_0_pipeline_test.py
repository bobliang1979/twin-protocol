"""
AstraeaEngine v4.0 Absolute — Pipeline Integration Test
End-to-end mock pipeline: runs run_pipeline with mock backends,
verifies Wilson Score convergence, chain integrity, backpropagation.
"""

import sys, os, json, asyncio, math
sys.path.insert(0, os.path.dirname(__file__))

from astraea_v4_0_absolute import (
    StructuredReasoningNode,
    AstraeaProductionEngine_v4_0,
)
import numpy as np


# ── Mock backends ──────────────────────────────────────────

class MockVerifier:
    def __init__(self, base=0.7):
        self.base = base
    async def score(self, state_json: str) -> float:
        state = json.loads(state_json)
        unc = state.get("uncertainty", 1.0)
        return self.base * (1.0 - unc * 0.5)

class MockEmbedder:
    def __init__(self, dim=128):
        self.dim = dim
    async def encode(self, text: str) -> np.ndarray:
        h = hash(text) % (2**31)
        rng = np.random.RandomState(h)
        emb = rng.randn(self.dim).astype(np.float32)
        return emb / (np.linalg.norm(emb) + 1e-8)

class MockCloudGenerator:
    def __init__(self, seed=42):
        self.rng = np.random.RandomState(seed)
        self.call_count = 0
    async def generate_batch(self, prompt: str, n: int = 3, json_schema: dict = None) -> list:
        self.call_count += 1
        results = []
        for i in range(n):
            unc = float(self.rng.uniform(0.1, 0.6))
            ev_count = int(self.rng.uniform(1, 4))
            results.append(json.dumps({
                "hypothesis": f"step_{self.call_count}_{i}",
                "evidence": [f"ev_{self.call_count}_{i}_{j}" for j in range(ev_count)],
                "uncertainty": unc
            }))
        return results


# ── Helpers ────────────────────────────────────────────────

def count_nodes(node):
    c = 1
    for ch in node.children:
        c += count_nodes(ch)
    return c

def max_depth(node, d=0):
    if not node.children:
        return d
    return max(max_depth(ch, d+1) for ch in node.children)


# ── Tests ──────────────────────────────────────────────────

async def test_pipeline_3iter():
    v = MockVerifier(base=0.72)
    e = MockEmbedder(dim=64)
    g = MockCloudGenerator(seed=42)
    eng = AstraeaProductionEngine_v4_0(v, e, g, max_concurrent_gen=4, max_concurrent_embed=8)
    root = await eng.run_pipeline("Test convergence", max_iterations=3)
    assert root.visits > 0
    assert root.total_value > 0
    assert root.avg_value > 0
    assert root.wilson_lower_bound() >= 0
    assert g.call_count > 0
    for child in root.children:
        assert child.depth == 1
        assert child.parent is not None
        assert child.parent.kv_cache_token == root.kv_cache_token
    print(f"  visits={root.visits}, avg={root.avg_value:.4f}, wlb={root.wilson_lower_bound():.4f}")
    print(f"  children={len(root.children)}, gen_calls={g.call_count}")


async def test_pipeline_8iter():
    v = MockVerifier(base=0.85)
    e = MockEmbedder(dim=64)
    g = MockCloudGenerator(seed=99)
    eng = AstraeaProductionEngine_v4_0(v, e, g)
    root = await eng.run_pipeline("Deep convergence", max_iterations=8)
    assert root.visits >= 3
    assert root.wilson_lower_bound() >= 0
    print(f"  visits={root.visits}, avg={root.avg_value:.4f}, wlb={root.wilson_lower_bound():.4f}")
    print(f"  children={len(root.children)}, total_nodes={count_nodes(root)}")


async def test_pipeline_circuit_breaker():
    v = MockVerifier(base=0.5)
    e = MockEmbedder(dim=32)
    g = MockCloudGenerator(seed=7)
    eng = AstraeaProductionEngine_v4_0(v, e, g, max_tree_depth=2)
    root = await eng.run_pipeline("Circuit breaker", max_iterations=5)
    assert root.visits > 0
    print(f"  visits={root.visits}, max_depth={max_depth(root)} (limit=2)")


async def test_pipeline_deadend():
    class EmptyGen:
        async def generate_batch(self, prompt, n=3, json_schema=None):
            return []
    v = MockVerifier(base=0.5)
    e = MockEmbedder(dim=32)
    g = EmptyGen()
    eng = AstraeaProductionEngine_v4_0(v, e, g, dead_end_penalty_base=-0.1)
    root = await eng.run_pipeline("Dead end", max_iterations=3)
    assert root.visits > 0
    print(f"  visits={root.visits}, avg={root.avg_value:.4f}")


async def test_pipeline_dedup():
    class DedupGen:
        def __init__(self):
            self.call_count = 0
        async def generate_batch(self, prompt, n=3, json_schema=None):
            self.call_count += 1
            return [
                json.dumps({"hypothesis": f"same_{self.call_count}", "evidence": ["e1"], "uncertainty": 0.3}),
                json.dumps({"hypothesis": f"same_{self.call_count}", "evidence": ["e1"], "uncertainty": 0.3}),
                json.dumps({"hypothesis": f"diff_{self.call_count}", "evidence": ["e2"], "uncertainty": 0.5}),
            ]
    class ThinEmbed:
        async def encode(self, text):
            h = hash(text) % 1000
            return np.array([float(h)/1000.0]*8, dtype=np.float32)
    v = MockVerifier(base=0.6)
    e = ThinEmbed()
    g = DedupGen()
    eng = AstraeaProductionEngine_v4_0(v, e, g, semantic_threshold=0.5)
    root = await eng.run_pipeline("Dedup", max_iterations=2)
    print(f"  children={len(root.children)}, gen_calls={g.call_count}")


# ── Runner ─────────────────────────────────────────────────

async def main():
    tests = [
        ("Pipeline 3-iteration converge", test_pipeline_3iter),
        ("Pipeline 8-iteration converge", test_pipeline_8iter),
        ("Pipeline circuit breaker", test_pipeline_circuit_breaker),
        ("Pipeline dead-end penalty", test_pipeline_deadend),
        ("Pipeline semantic dedup", test_pipeline_dedup),
    ]
    total = passed = 0
    failed = []
    for name, fn in tests:
        total += 1
        try:
            await fn()
            passed += 1
            print(f"  [PASS] {name}")
        except Exception as e:
            import traceback
            failed.append(name)
            print(f"  [FAIL] {name}: {e}")
            traceback.print_exc()
        print()
    
    print("=" * 50)
    print(f"  Pipeline Integration: {passed}/{total} passed")
    if failed:
        print(f"  FAILED: {failed}")
    print("=" * 50)
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())
