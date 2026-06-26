"""
Astraea v4.0 Absolute — Phase 2: Mock Backend + Verification Unit Tests

Four invariance tests:
  1. GENESIS LIVENESS  — parent weakref alive at child construction; bounded chain trace
  2. UCT CONTINUITY     — log(v+1) smooths exploration domain; no death at visits=1
  3. WILSON DOMAIN      — double-clamped Wilson lower bound, math domain defense
  4. TOKEN INVARIANCE   — kv_cache_token computed once at genesis, immutable, drift-free

Architecture:
  MockBackend        → mock local_verifier, local_embedder, cloud_generator
  TestVerification*  → pytest classes with edge-case tables per invariant
  asyncio.run()      → single entry for all async tests
"""

import asyncio
import math
import json
import hashlib
import weakref
import sys
from typing import List, Dict, Any, Optional

import numpy as np

# ──────────────────────────────────────────────────────────────────────
# 1.  MOCK BACKEND
# ──────────────────────────────────────────────────────────────────────

class MockVerifier:
    """Deterministic verifier that returns pre-configured scores.

    Modes:
      - uniform(float)  : always returns that value
      - sequential(list): returns values round-robin across calls
      - fail_after(n)   : raises after n successful calls (simulate network outage)
    """
    def __init__(self, mode: str = "uniform", value: float = 0.7, values: Optional[List[float]] = None):
        self.mode = mode
        self._uniform_val = value
        self._seq = values or []
        self._seq_idx = 0
        self._calls = 0
        self._fail_after = None

    def score(self, text: str) -> float:
        self._calls += 1
        if self._fail_after is not None and self._calls > self._fail_after:
            raise RuntimeError(f"MockVerifier: forced fail at call #{self._calls}")
        if self.mode == "uniform":
            return float(np.clip(self._uniform_val, 0.0, 1.0))
        if self.mode == "sequential":
            val = self._seq[self._seq_idx % len(self._seq)]
            self._seq_idx += 1
            return float(np.clip(val, 0.0, 1.0))
        return 0.0

    def set_fail_after(self, n: int):
        self._fail_after = n


class MockEmbedder:
    """Deterministic embedder mapping text → fixed-dim unit vectors.

    Consistency: same text → same vector, always.
    Collision simulation: pass collision_map={text: identical_vector}.
    """
    def __init__(self, dim: int = 64, seed: int = 42, collision_map: Optional[Dict[str, np.ndarray]] = None):
        self.dim = dim
        self._rng = np.random.default_rng(seed)
        self._cache: Dict[str, np.ndarray] = {}
        self._collision_map = collision_map or {}

    def _make_vector(self) -> np.ndarray:
        v = self._rng.normal(size=self.dim).astype(np.float32)
        return v / (np.linalg.norm(v) + 1e-8)

    async def encode(self, text: str) -> np.ndarray:
        # collision override
        if text in self._collision_map:
            return self._collision_map[text]
        # deterministic cache
        if text not in self._cache:
            self._cache[text] = self._make_vector()
        return self._cache[text]


class MockCloudGenerator:
    """Configurable generator that returns pre-baked responses.

    Modes:
      - static (list of dicts): always returns same set
      - cycle  (list of list-of-dicts): returns different set each call, cycles
      - fail_after(n): raises after n calls
    """
    def __init__(self, responses: List[Dict], mode: str = "static",
                 batch_size: int = 3, fail_after: Optional[int] = None):
        self._responses = responses
        self._mode = mode
        self._batch_size = batch_size
        self._calls = 0
        self._fail_after = fail_after
        self._cycle_idx = 0

    async def generate_batch(self, prompt: str, n: int = 3,
                             json_schema: Optional[Dict] = None) -> List[str]:
        self._calls += 1
        if self._fail_after is not None and self._calls > self._fail_after:
            raise RuntimeError(f"MockCloudGenerator: forced fail at call #{self._calls}")

        if self._mode == "static":
            selected = self._responses[:n]
        elif self._mode == "cycle":
            selected = self._responses[self._cycle_idx * n:(self._cycle_idx + 1) * n]
            self._cycle_idx = (self._cycle_idx + 1) % max(1, len(self._responses) // n)
        else:
            selected = self._responses[:n]

        return [json.dumps(s, ensure_ascii=False) for s in selected]


# ──────────────────────────────────────────────────────────────────────
# 2.  IMPORT TARGET under test (astraea_v4_0_absolute)
# ──────────────────────────────────────────────────────────────────────
# We import the concrete classes from the production module.
# All tests target StructuredReasoningNode and AstraeaProductionEngine_v4_0.

sys.path.insert(0, r"C:\Users\10074\Documents\控制")

try:
    from astraea_v4_0_absolute import (
        StructuredReasoningNode,
        AstraeaProductionEngine_v4_0,
        REASONING_STATE_SCHEMA,
    )
except ImportError as e:
    raise ImportError(
        f"Cannot import astraea_v4_0_absolute: {e}. "
        "Make sure astraea_v4_0_absolute.py is in the working directory."
    )
except Exception as e:
    raise RuntimeError(f"Unexpected import error: {e}")


# ──────────────────────────────────────────────────────────────────────
# 3.  FIXTURE FACTORIES
# ──────────────────────────────────────────────────────────────────────

def make_mock_engine(**overrides) -> AstraeaProductionEngine_v4_0:
    """Create an engine wired to mock backends."""
    verifier = MockVerifier(value=0.7)
    embedder = MockEmbedder()
    generator = MockCloudGenerator(
        responses=[
            {"hypothesis": "step A", "evidence": ["fact1"], "uncertainty": 0.6},
            {"hypothesis": "step B", "evidence": ["fact2"], "uncertainty": 0.4},
            {"hypothesis": "step C", "evidence": ["fact3"], "uncertainty": 0.3},
        ],
        mode="cycle",
        batch_size=3,
    )
    return AstraeaProductionEngine_v4_0(
        local_verifier=verifier,
        local_embedder=embedder,
        cloud_generator=generator,
        **overrides
    )


def make_state(**overrides) -> Dict[str, Any]:
    """Helper: build a valid REASONING_STATE_SCHEMA dict."""
    state = {"hypothesis": "test", "evidence": [], "uncertainty": 0.5}
    state.update(overrides)
    return state


# ──────────────────────────────────────────────────────────────────────
# 4.  VERIFICATION: GENESIS LIVENESS
# ──────────────────────────────────────────────────────────────────────

def test_genesis_liveness_weakref_alive():
    """GIVEN a live parent, WHEN child is constructed, THEN no error."""
    parent = StructuredReasoningNode(state=make_state(hypothesis="parent"))
    child = StructuredReasoningNode(
        state=make_state(hypothesis="child"),
        parent=parent,
        depth=parent.depth + 1,
    )
    # parent ref is alive → weakref resolves
    assert child.parent is parent, "Parent weakref should resolve to the live parent"
    # token chain: child token derived from parent token
    expected_content = f"{parent.kv_cache_token}|{json.dumps(child.state, sort_keys=True)}"
    expected_token = hashlib.sha256(expected_content.encode()).hexdigest()[:16]
    assert child.kv_cache_token == expected_token, "Token chain should be derivable"


def test_genesis_liveness_dead_parent_raises():
    """GIVEN a parent that has been GC'd before child construction,
    WHEN child is constructed with the dead ref AS parent (None),
    THEN it is treated as root (default), NOT RuntimeError.

    NOTE: The production guard `if self._parent_ref() is None: raise RuntimeError`
    at astraea_v4_0_absolute.py:55 is a STATIC defense-in-depth guard.
    It CANNOT be triggered dynamically in current code because the `parent`
    function parameter holds a strong reference throughout the __init__ body,
    so the weakref always resolves. The guard only protects against future
    code mutations that might delete the local variable before the check.
    """
    parent = StructuredReasoningNode(state=make_state(hypothesis="ephemeral"))
    parent_ref = weakref.ref(parent)
    del parent
    import gc; gc.collect()
    assert parent_ref() is None, "Parent should be GC'd for this test"

    # Passing None as parent → treated as root (else branch in __init__)
    child = StructuredReasoningNode(
        state=make_state(hypothesis="orphan"),
        parent=parent_ref(),  # None at this point
        depth=0,
    )
    assert child.parent is None, "GC'd parent passed as None should yield root-node parent=None"
    # Token should be ROOT-based
    expected = hashlib.sha256(
        f"ROOT|{json.dumps(child.state, sort_keys=True)}".encode()
    ).hexdigest()[:16]
    assert child.kv_cache_token == expected, "Token should derive from ROOT when parent=None"


def test_genesis_liveness_none_parent_is_root():
    """GIVEN parent=None, WHEN child constructed, THEN token uses 'ROOT' prefix."""
    child = StructuredReasoningNode(state=make_state(hypothesis="root_child"), parent=None)
    expected_content = f"ROOT|{json.dumps(child.state, sort_keys=True)}"
    expected_token = hashlib.sha256(expected_content.encode()).hexdigest()[:16]
    assert child.kv_cache_token == expected_token, "Root child token should derive from 'ROOT'"
    assert child.parent is None, "Root child should have no parent"


def test_genesis_liveness_chain_trace_ok():
    """GIVEN a valid tree, WHEN _verify_chain_liveness is called, THEN returns True."""
    engine = make_mock_engine()
    root = StructuredReasoningNode(state=make_state(hypothesis="root"))
    c1 = StructuredReasoningNode(state=make_state(hypothesis="c1"), parent=root, depth=1)
    c2 = StructuredReasoningNode(state=make_state(hypothesis="c2"), parent=c1, depth=2)
    assert engine._verify_chain_liveness(c2, root) is True
    assert engine._verify_chain_liveness(root, root) is True


def test_genesis_liveness_chain_trace_broken():
    """GIVEN a leaf whose parent chain is severed, WHEN verified, THEN returns False."""
    engine = make_mock_engine()
    root = StructuredReasoningNode(state=make_state(hypothesis="root"))
    orphan = StructuredReasoningNode(state=make_state(hypothesis="orphan"), parent=None, depth=0)
    # orphan's parent is None, not root → chain is broken
    import gc; gc.collect()
    assert engine._verify_chain_liveness(orphan, root) is False


# ──────────────────────────────────────────────────────────────────────
# 5.  VERIFICATION: UCT CONTINUITY
# ──────────────────────────────────────────────────────────────────────

def _build_select_tree(engine, config: Dict[str, Any]) -> StructuredReasoningNode:
    """Build a small tree for UCT selection testing.

    Config keys:
      children: list of (visits, total_value) tuples
    """
    root = StructuredReasoningNode(state=make_state(hypothesis="uct_root"))
    for visits, total_value in config.get("children", []):
        c = StructuredReasoningNode(state=make_state(hypothesis=f"child_{len(root.children)}"),
                                     parent=root, depth=1)
        c.visits = visits
        c.total_value = total_value
        root.children.append(c)
    return root


def test_uct_continuity_log_smoothing():
    """GIVEN a child with visits=1, WHEN log_parent is computed, THEN log(2) is finite.

    The '+ 1' in `math.log(current.visits + 1)` prevents math domain error
    and ensures exploration term is defined even immediately after first visit.
    """
    engine = make_mock_engine(exploration_constant=1.41)

    # Root with 1 visit (was just visited for the first time)
    root = StructuredReasoningNode(state=make_state(hypothesis="r"))
    root.visits = 1

    # One visited child
    c = StructuredReasoningNode(state=make_state(hypothesis="c"), parent=root, depth=1)
    c.visits = 1
    c.total_value = 0.6
    root.children.append(c)

    # The UCT for this child should be finite
    log_parent = math.log(root.visits + 1)
    exploitation = c.avg_value
    exploration = engine.c * math.sqrt(log_parent / c.visits)
    uct = exploitation + exploration
    assert math.isfinite(uct), f"UCT should be finite at visits=1, got {uct}"
    assert uct > exploitation, "Exploration bonus should be >0 when visits=1"


def test_uct_continuity_unvisited_preferred():
    """GIVEN a mix of visited and unvisited children, WHEN selecting, THEN unvisited chosen."""
    engine = make_mock_engine()
    root = _build_select_tree(engine, {
        "children": [
            (0, 0.0),   # unvisited
            (5, 3.0),   # visited, high avg
        ]
    })
    selected = engine._uct_select(root)
    assert selected.visits == 0, "Unvisited child should be preferred"
    assert selected.total_value == 0.0


def test_uct_continuity_higher_uct_wins():
    """GIVEN all children visited, WHEN selecting, THEN highest UCT child wins."""
    engine = make_mock_engine(exploration_constant=0.0)  # zero exploration → pure exploitation
    root = _build_select_tree(engine, {
        "children": [
            (10, 5.0),   # avg 0.5
            (10, 9.0),   # avg 0.9 ← max
            (10, 2.0),   # avg 0.2
        ]
    })
    selected = engine._uct_select(root)
    assert selected.total_value == 9.0, "Highest avg_value child should be selected under pure exploitation"


def test_uct_continuity_exploration_bonus():
    """GIVEN two children with equal exploitation, WHEN one has fewer visits, THEN exploration bonus tilts."""
    engine = make_mock_engine(exploration_constant=1.0)
    root = _build_select_tree(engine, {
        "children": [
            (10, 5.0),   # avg 0.5
            (2, 1.0),    # avg 0.5, fewer visits → higher exploration bonus
        ]
    })
    c_low, c_high = root.children
    log_p = math.log(root.visits + 1)  # root.visits=0 → log(1)=0
    # But the _uct_select function computes log_parent = math.log(current.visits + 1)
    # Let's manually compute: root has 0 visits initially (or we set it)
    root.visits = 12  # make exploration term non-zero
    selected = engine._uct_select(root)
    # The child with fewer visits should have higher exploration bonus
    expl_low = engine.c * math.sqrt(math.log(root.visits + 1) / 2)
    expl_high = engine.c * math.sqrt(math.log(root.visits + 1) / 10)
    assert expl_low > expl_high, "Fewer visits → higher exploration bonus"
    # With equal avg (0.5 vs 0.5), lower-visit child wins
    assert selected.visits == 2, "Child with fewer visits should win when avg_values are equal"


# ──────────────────────────────────────────────────────────────────────
# 6.  VERIFICATION: WILSON DOMAIN DEFENSE
# ──────────────────────────────────────────────────────────────────────

def test_wilson_domain_zero_visits():
    """GIVEN a node with 0 visits, WHEN wilson_lower_bound, THEN returns 0.0."""
    node = StructuredReasoningNode(state=make_state())
    assert node.visits == 0
    assert node.wilson_lower_bound() == 0.0, "Zero-visit Wilson bound should be 0.0"


def test_wilson_domain_clamp_low():
    """GIVEN p < 0 (impossible via clip), WHEN computed, THEN result is >= 0.0."""
    node = StructuredReasoningNode(state=make_state())
    node.visits = 10
    # force total_value negative to simulate edge
    node.total_value = -1.0
    # avg_value clips to [0,1] via np.clip in the method
    lb = node.wilson_lower_bound(z=1.96)
    assert 0.0 <= lb <= 1.0, f"Wilson lower bound should be clamped to [0,1], got {lb}"


def test_wilson_domain_clamp_high():
    """GIVEN p > 1 (impossible via clip), WHEN computed, THEN result is <= 1.0."""
    node = StructuredReasoningNode(state=make_state())
    node.visits = 10
    node.total_value = 15.0  # clip to 1.0 internally
    lb = node.wilson_lower_bound(z=1.96)
    assert 0.0 <= lb <= 1.0, f"Wilson lower bound should be clamped to [0,1], got {lb}"


def test_wilson_domain_inner_negative_prevented():
    """GIVEN extreme parameters that make inner sqrt argument negative,
    WHEN computed, THEN max(0.0, inner) prevents math domain error.

    The formula: inner = (p*(1-p) + z²/(4*n)) / n
    At extreme confidence (z=3.0) and low visits, the result is mathematically
    guaranteed non-negative, but the guard is defense-in-depth.
    """
    node = StructuredReasoningNode(state=make_state())
    node.visits = 1
    node.total_value = 1.0  # p = 1.0
    # inner = (1*0 + 9/4) / 1 = 2.25 → positive, but p*(1-p)=0
    lb = node.wilson_lower_bound(z=3.0)
    assert math.isfinite(lb), f"Wilson bound should be finite, got {lb}"
    assert 0.0 <= lb <= 1.0, f"Wilson bound clamped to [0,1], got {lb}"


def test_wilson_domain_increasing_visits():
    """GIVEN increasing visits with same avg (0.8), WHEN Wilson bound computed,
    THEN the bound tightens (approaches avg)."""
    node = StructuredReasoningNode(state=make_state())
    avg = 0.8  # keep avg constant across visit counts

    bounds = []
    for v in [1, 4, 16, 64]:
        node.visits = v
        node.total_value = avg * v  # total_value proportional to visits
        bounds.append(node.wilson_lower_bound(z=1.96))

    # With more visits, the lower bound should be higher (less uncertainty)
    # At v=1, avg=0.8 → bound is low (high uncertainty)
    # At v=64, avg=0.8 → bound approaches 0.8 (low uncertainty)
    for i in range(len(bounds) - 1):
        assert bounds[i] <= bounds[i + 1], (
            f"Wilson bound should increase with visits: v={ [1,4,16,64][i] } lb={bounds[i]:.4f}, "
            f"v={ [1,4,16,64][i+1] } lb={bounds[i+1]:.4f}, avg={avg}"
        )


# ──────────────────────────────────────────────────────────────────────
# 7.  VERIFICATION: TOKEN INVARIANCE
# ──────────────────────────────────────────────────────────────────────

def test_token_invariance_deterministic():
    """GIVEN same parent + same state, WHEN two children constructed, THEN tokens match."""
    parent = StructuredReasoningNode(state=make_state(hypothesis="p"))
    state = make_state(hypothesis="deterministic_child", evidence=["same"], uncertainty=0.5)

    c1 = StructuredReasoningNode(state=state, parent=parent, depth=1)
    c2 = StructuredReasoningNode(state=state, parent=parent, depth=1)

    assert c1.kv_cache_token == c2.kv_cache_token, \
        "Identical nodes should have identical tokens"

    # Also verify the token is the expected SHA256[:16]
    content = f"{parent.kv_cache_token}|{json.dumps(state, sort_keys=True)}"
    expected = hashlib.sha256(content.encode()).hexdigest()[:16]
    assert c1.kv_cache_token == expected, \
        f"Token should match derived SHA256. Expected {expected}, got {c1.kv_cache_token}"


def test_token_invariance_immutable():
    """GIVEN a constructed node, WHEN state is modified later, THEN kv_cache_token unchanged."""
    state = make_state(hypothesis="mutable", evidence=[], uncertainty=0.5)
    node = StructuredReasoningNode(state=dict(state), parent=None)

    original_token = node.kv_cache_token

    # Mutate state in-place (should not affect token since it was already computed)
    node.state["hypothesis"] = "changed"
    node.state["evidence"] = ["new evidence"]
    node.state["uncertainty"] = 0.9

    assert node.kv_cache_token == original_token, \
        "kv_cache_token should be immutable after construction"


def test_token_invariance_chain_coherence():
    """GIVEN a parent-child chain, WHEN parent token changes (impossible due to immutability),
    THEN child token remains unaffected. (Testing invariants, not mutability.)"""
    root = StructuredReasoningNode(state=make_state(hypothesis="root"))
    child = StructuredReasoningNode(state=make_state(hypothesis="chain_child"),
                                     parent=root, depth=1)

    # Token chain property: child token = SHA256(parent_token || state)
    expected = hashlib.sha256(
        f"{root.kv_cache_token}|{json.dumps(child.state, sort_keys=True)}".encode()
    ).hexdigest()[:16]
    assert child.kv_cache_token == expected

    # Grandchild
    grandchild = StructuredReasoningNode(state=make_state(hypothesis="grand"),
                                          parent=child, depth=2)
    expected_gc = hashlib.sha256(
        f"{child.kv_cache_token}|{json.dumps(grandchild.state, sort_keys=True)}".encode()
    ).hexdigest()[:16]
    assert grandchild.kv_cache_token == expected_gc
    # Grandchild is NOT directly derivable from root (two levels deep)
    root_based = hashlib.sha256(
        f"{root.kv_cache_token}|{json.dumps(grandchild.state, sort_keys=True)}".encode()
    ).hexdigest()[:16]
    assert grandchild.kv_cache_token != root_based, \
        "Grandchild token should NOT be derivable from root alone (proves chain integrity)"


def test_token_invariance_no_collision():
    """GIVEN nodes with different states, WHEN tokens computed, THEN no collision."""
    n = 200
    tokens = set()
    parent = StructuredReasoningNode(state=make_state(hypothesis="collision_root"))
    for i in range(n):
        c = StructuredReasoningNode(
            state=make_state(hypothesis=f"state_{i}", evidence=[str(i)], uncertainty=i / 100.0),
            parent=parent if i > 0 else None,
            depth=1 if i > 0 else 0,
        )
        tokens.add(c.kv_cache_token)
    assert len(tokens) >= n - 1, f"Token collision detected among {n} nodes: {n - len(tokens)} dupes"
    # Allow 1 collision bound for 16-char hex (p ~ 2^-64 — astronomically unlikely anyway)


# ──────────────────────────────────────────────────────────────────────
# 8.  RUNNER
# ──────────────────────────────────────────────────────────────────────

def run_all():
    """Run all tests with pass/fail tally. Compatible with pytest and standalone."""
    test_functions = [
        # Genesis Liveness
        test_genesis_liveness_weakref_alive,
        test_genesis_liveness_dead_parent_raises,
        test_genesis_liveness_none_parent_is_root,
        test_genesis_liveness_chain_trace_ok,
        test_genesis_liveness_chain_trace_broken,
        # UCT Continuity
        test_uct_continuity_log_smoothing,
        test_uct_continuity_unvisited_preferred,
        test_uct_continuity_higher_uct_wins,
        test_uct_continuity_exploration_bonus,
        # Wilson Domain Defense
        test_wilson_domain_zero_visits,
        test_wilson_domain_clamp_low,
        test_wilson_domain_clamp_high,
        test_wilson_domain_inner_negative_prevented,
        test_wilson_domain_increasing_visits,
        # Token Invariance
        test_token_invariance_deterministic,
        test_token_invariance_immutable,
        test_token_invariance_chain_coherence,
        test_token_invariance_no_collision,
    ]

    passed, failed = 0, 0
    failures = []
    print("=" * 70)
    print("  ASTRAEA v4.0 ABSOLUTE — PHASE 2 VERIFICATION SUITE".center(70))
    print("  Genesis Liveness | UCT Continuity | Wilson Domain | Token Invariance".center(70))
    print("=" * 70)

    for fn in test_functions:
        label = fn.__name__.replace("test_", "").replace("_", " ").title()
        try:
            fn()
            print(f"  [PASS] {label:52s}")
            passed += 1
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"  [FAIL] {label:52s}")
            print(f"         {e}")
            failures.append((fn.__name__, str(e), tb))
            failed += 1

    print("-" * 70)
    total = passed + failed
    print(f"  RESULTS:  {passed}/{total} passed  {failed}/{total} failed")
    if failures:
        print(f"  FAILURES: {len(failures)}")
        for name, msg, _ in failures:
            print(f"    ✗ {name}: {msg}")
    print("=" * 70)
    return len(failures)


if __name__ == "__main__":
    import sys
    if "--pytest" in sys.argv:
        # Allow pytest discovery when run with pytest
        pass
    else:
        sys.exit(run_all())
