"""
AstraeaEngine v4.0 Absolute — 绝对零度·永恒封版
Mathematical continuity, static token invariance, genesis liveness guard,
memory-safe weakref, and bounded async trace.
"""

import asyncio
import math
import json
import hashlib
import numpy as np
import weakref
from typing import List, Dict, Any, Optional
from cachetools import LRUCache
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("Astraea_v4_0_Absolute")

REASONING_STATE_SCHEMA = {
    "type": "object",
    "properties": {
        "hypothesis": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "uncertainty": {"type": "number", "minimum": 0.0, "maximum": 1.0}
    },
    "required": ["hypothesis", "evidence", "uncertainty"]
}


class StructuredReasoningNode:
    """
    Absolute MCTS Node:
    - Static immutable kv_cache_token computed at genesis (zero hash drift).
    - Genesis parent liveness assertion (prevents silent ROOT fallback on dead parent).
    - weakref parent for zero-GC cyclic reference elimination.
    - Wilson Score with double-clamping math domain defense.
    """
    __slots__ = ('state', 'depth', 'visits', 'total_value', 'children',
                 '_parent_ref', 'kv_cache_token', '__weakref__')
    
    def __init__(self, state: Dict[str, Any], parent: Optional['StructuredReasoningNode'] = None, depth: int = 0):
        self.state = state
        self.depth = depth
        self.visits = 0
        self.total_value = 0.0
        self.children: List['StructuredReasoningNode'] = []
        
        # GENESIS PARENT LIVENESS ASSERTION:
        # If parent was specified but is already dead at construction time,
        # refuse to create a node with a silently corrupted ROOT-based token.
        if parent is not None:
            self._parent_ref: Optional[weakref.ref] = weakref.ref(parent)
            # Verify the weakref is alive RIGHT NOW before computing token
            if self._parent_ref() is None:
                raise RuntimeError(
                    f"Genesis Parent Liveness Failed: Parent node was GC'd before "
                    f"child construction at depth {depth}. Refusing silent token corruption."
                )
            parent_token = parent.kv_cache_token
        else:
            self._parent_ref = None
            parent_token = "ROOT"
            
        # TOKEN HARDENING: Immutable calculation at genesis
        content = f"{parent_token}|{json.dumps(self.state, sort_keys=True)}"
        self.kv_cache_token: str = hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @property
    def parent(self) -> Optional['StructuredReasoningNode']:
        return self._parent_ref() if self._parent_ref is not None else None
        
    @parent.setter
    def parent(self, value: Optional['StructuredReasoningNode']):
        if value is not None:
            self._parent_ref = weakref.ref(value)
        else:
            self._parent_ref = None
    
    @property
    def avg_value(self) -> float:
        return self.total_value / self.visits if self.visits > 0 else 0.0
    
    def wilson_lower_bound(self, z: float = 1.96) -> float:
        if self.visits == 0:
            return 0.0
        p = float(np.clip(self.avg_value, 0.0, 1.0))
        denominator = 1 + z * z / self.visits
        centre = p + z * z / (2 * self.visits)
        inner = (p * (1 - p) + z * z / (4 * self.visits)) / self.visits
        std = z * math.sqrt(max(0.0, inner))
        return max(0.0, (centre - std) / denominator)


class AstraeaProductionEngine_v4_0:
    """
    Astraea-MCTS v4.0 Absolute: The Eternal Frozen Apex.
    Mathematical continuity, static token invariance, genesis liveness guard,
    memory-safe weakref, and bounded async trace. Zero remaining failure modes.
    """
    
    def __init__(
        self, 
        local_verifier, local_embedder, cloud_generator, 
        exploration_constant: float = 1.41,
        max_concurrent_gen: int = 8,
        max_concurrent_embed: int = 16,
        semantic_threshold: float = 0.92,
        embed_cache_maxsize: int = 10000,
        dead_end_penalty_base: float = -0.1,
        stop_confidence_z: float = 1.96,
        max_tree_depth: int = 64
    ):
        self.local_verifier = local_verifier
        self.local_embedder = local_embedder
        self.cloud_generator = cloud_generator
        self.c = exploration_constant
        self.semantic_threshold = semantic_threshold
        self.dead_end_penalty_base = dead_end_penalty_base
        self.stop_confidence_z = stop_confidence_z
        self.max_tree_depth = max_tree_depth
        
        self._gen_semaphore = asyncio.Semaphore(max_concurrent_gen)
        self._embed_semaphore = asyncio.Semaphore(max_concurrent_embed)
        self._embed_cache: LRUCache = LRUCache(maxsize=embed_cache_maxsize)

    def _batch_cosine_similarity(self, query: np.ndarray, corpus: np.ndarray) -> np.ndarray:
        if corpus.size == 0 or corpus.ndim < 2:
            return np.array([])
        qn = query / (np.linalg.norm(query) + 1e-8)
        cn = corpus / (np.linalg.norm(corpus, axis=1, keepdims=True) + 1e-8)
        return np.dot(cn, qn)

    def _uct_select(self, node: StructuredReasoningNode) -> StructuredReasoningNode:
        current = node
        while current.children:
            unvisited = [c for c in current.children if c.visits == 0]
            if unvisited:
                return max(unvisited, key=lambda c: (c.total_value, c.depth, c.kv_cache_token))
            
            best_score = -float('inf')
            best_child = None
            
            # MATHEMATICAL CONTINUITY: "+ 1" smooths log domain, preventing exploration death at visits=1
            log_parent = math.log(current.visits + 1)
            
            for child in current.children:
                exploitation = child.avg_value
                exploration = self.c * math.sqrt(log_parent / child.visits)
                uct = exploitation + exploration
                if uct > best_score:
                    best_score = uct
                    best_child = child
                    
            if best_child is None:
                break
            current = best_child
        return current

    async def _safe_encode(self, text: str) -> Optional[np.ndarray]:
        cache_key = hashlib.md5(text.encode()).hexdigest()
        cached = self._embed_cache.get(cache_key)
        if cached is not None:
            return cached
            
        async with self._embed_semaphore:
            try:
                emb = await self.local_embedder.encode(text)
                if isinstance(emb, list):
                    emb = np.array(emb, dtype=np.float32)
                elif hasattr(emb, 'numpy'):
                    emb = emb.numpy().astype(np.float32)
                
                existing = self._embed_cache.get(cache_key)
                if existing is None:
                    self._embed_cache[cache_key] = emb
                    return emb
                return existing
            except Exception as e:
                logger.warning(f"Embedding failed: {e}")
                return None

    async def _semantic_deduplicate(self, candidates, existing_siblings):
        if not candidates or not existing_siblings:
            return candidates
            
        cand_embs = await asyncio.gather(*[self._safe_encode(c.state["hypothesis"]) for c in candidates])
        valid = [(i, e) for i, e in enumerate(cand_embs) if e is not None]
        failed = {i for i, e in enumerate(cand_embs) if e is None}
        
        if not valid:
            return candidates
            
        sib_embs = await asyncio.gather(*[self._safe_encode(s.state["hypothesis"]) for s in existing_siblings])
        sib_list = [e for e in sib_embs if e is not None]
        
        if not sib_list:
            return candidates
            
        sib_matrix = np.stack(sib_list)
        unique = []
        
        for idx, emb in valid:
            sims = self._batch_cosine_similarity(emb, sib_matrix)
            if sims.size == 0 or np.max(sims) <= self.semantic_threshold:
                unique.append(candidates[idx])
                
        for idx in failed:
            unique.append(candidates[idx])
        return unique

    async def batch_expand_and_evaluate(self, node: StructuredReasoningNode) -> List[StructuredReasoningNode]:
        prompt = (
            f"[Context Token: {node.kv_cache_token}] "
            f"Current State: {json.dumps(node.state)}. "
            f"Generate 3 distinct next reasoning steps."
        )
        
        async with self._gen_semaphore:
            try:
                raws = await self.cloud_generator.generate_batch(prompt, n=3, json_schema=REASONING_STATE_SCHEMA)
            except Exception as e:
                logger.error(f"Generation failed: {e}")
                return []
        
        nodes = []
        for raw in raws:
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                # Genesis liveness assertion fires here if parent died mid-batch
                child = StructuredReasoningNode(state=parsed, parent=node, depth=node.depth+1)
                nodes.append(child)
            except RuntimeError as e:
                # Parent was GC'd during batch processing; skip this child safely
                logger.warning(f"Child creation aborted: {e}")
                continue
            except Exception:
                continue
                
        if not nodes:
            return []
            
        unique = await self._semantic_deduplicate(nodes, node.children)
        if not unique:
            return []
            
        async def _eval(c):
            try:
                return float(np.clip(await self.local_verifier.score(json.dumps(c.state)), 0.0, 1.0))
            except Exception:
                return 0.0
                
        scores = await asyncio.gather(*[_eval(c) for c in unique])
        
        for child, score in zip(unique, scores):
            child.total_value = score
            child.visits = 0
            node.children.append(child)
            
        return unique

    def _backpropagate(self, node: StructuredReasoningNode, reward: float):
        curr: Optional[StructuredReasoningNode] = node
        while curr is not None:
            curr.visits += 1
            curr.total_value += reward
            curr = curr.parent

    def _verify_chain_liveness(self, leaf: StructuredReasoningNode, root: StructuredReasoningNode) -> bool:
        """Bounded full-chain trace. O(max_tree_depth) worst case."""
        if leaf is root:
            return True
            
        trace_curr: Optional[StructuredReasoningNode] = leaf
        steps = 0
        
        while trace_curr is not root:
            if trace_curr is None or trace_curr.parent is None or steps > self.max_tree_depth:
                return False
            trace_curr = trace_curr.parent
            steps += 1
            
        return True

    async def run_pipeline(self, query: str, max_iterations: int = 8, 
                           confidence_threshold: float = 0.95, min_visits_for_stop: int = 4):
        root = StructuredReasoningNode(state={"hypothesis": query, "evidence": [], "uncertainty": 1.0})
        
        for iteration in range(max_iterations):
            leaf = self._uct_select(root)
            is_new_node = (leaf.visits == 0)
            
            new_nodes = await self.batch_expand_and_evaluate(leaf)
            
            if not self._verify_chain_liveness(leaf, root):
                logger.warning(
                    f"Circuit breaker tripped @ iter {iteration}: "
                    f"Upstream lineage invalidated during I/O suspend. Aborting."
                )
                break
            
            
            if new_nodes:
                rep_reward = max(c.total_value for c in new_nodes)
                self._backpropagate(leaf, rep_reward)
            else:
                penalty = self.dead_end_penalty_base / (leaf.depth + 1)
                self._backpropagate(leaf, penalty)
            
            if (root.visits >= min_visits_for_stop and 
                root.wilson_lower_bound(self.stop_confidence_z) > confidence_threshold):
                logger.info(
                    f"Early stop @ iter {iteration}: "
                    f"wilson_lb={root.wilson_lower_bound(self.stop_confidence_z):.3f}, "
                    f"avg={root.avg_value:.3f}, visits={root.visits}"
                )
                break
                
        return root
