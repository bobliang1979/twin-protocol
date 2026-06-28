"""CognitiveHealthField"""
from collections import deque
from typing import Dict

class CognitiveHealthField:
    """Multi-dimensional cognitive health monitor (from cognitive-circuit-breaker)."""

    def __init__(self):
        self.metrics: Dict[str, deque] = {
            k: deque(maxlen=1000) for k in
            ["response_time", "error_rate", "throughput",
             "coherence", "uncertainty", "energy"]
        }

    def record(self, metric: str, value: float):
        if metric in self.metrics:
            self.metrics[metric].append(value)

    def report(self) -> Dict:
        return {
            k: {
                "mean": sum(v) / len(v) if v else 0,
                "last": v[-1] if v else 0,
                "trend": "rising" if len(v) > 1 and v[-1] > sum(v) / len(v) else "falling"
            }
            for k, v in self.metrics.items() if v
        }

    def health_score(self) -> float:
        c = list(self.metrics["coherence"]) or [1]
        e = list(self.metrics["energy"]) or [0]
        u = list(self.metrics["uncertainty"]) or [0]
        return (c[-1] * 0.4 + e[-1] * 0.4 + (1 - u[-1]) * 0.2)

