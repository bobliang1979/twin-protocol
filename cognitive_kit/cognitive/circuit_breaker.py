"""DHG Circuit Breaker"""
from collections import deque

class DHGCircuitBreaker:
    """Hash entropy circuit breaker (from cognitive-circuit-breaker skill).
    Detects system degradation via state hash collision frequency."""

    def __init__(self, threshold: float = 0.15, window: int = 100):
        self.threshold = threshold
        self.history: deque = deque(maxlen=window)
        self.tripped = False
        self.trip_count = 0

    def feed(self, state_hash: str) -> bool:
        bits = bin(int(state_hash, 16))[2:].zfill(len(state_hash) * 4)
        ones = bits.count("1")
        entropy = min(ones / len(bits), 1.0 - ones / len(bits)) * 2
        self.history.append(entropy)

        if len(self.history) == self.history.maxlen:
            mean_entropy = sum(self.history) / len(self.history)
            if mean_entropy < self.threshold:
                self.tripped = True
                self.trip_count += 1
                return True
        self.tripped = False
        return False

    def reset(self):
        self.history.clear()
        self.tripped = False

