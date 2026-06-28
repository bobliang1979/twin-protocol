"""Failure Mode Classifier"""
from typing import List

class FailureModeClassifier:
    """ReflectionEngine 6 failure modes (from reflection-engine skill)."""

    MODES = {
        "NO_STATE_CHANGE": {
            "detect": ["state unchanged", "no change", "same state", "no effect"],
            "recovery": ["retry", "retry_with_delay", "rescan", "retry"],
            "severity": 3
        },
        "ELEMENT_MISSING": {
            "detect": ["not found", "missing", "cannot find", "no such element"],
            "recovery": ["rescan", "wait_and_rescan", "retry", "escalate"],
            "severity": 4
        },
        "WRONG_WINDOW": {
            "detect": ["focus", "window", "foreground", "wrong window"],
            "recovery": ["windeep_focus", "retry"],
            "severity": 3
        },
        "TIMEOUT": {
            "detect": ["timeout", "timed out", "time out", "too long"],
            "recovery": ["retry_with_longer_timeout", "escalate"],
            "severity": 2
        },
        "PERMISSION_DENIED": {
            "detect": ["permission", "access denied", "denied", "forbidden"],
            "recovery": ["escalate"],
            "severity": 5
        },
        "WRONG_OUTPUT": {
            "detect": ["expected", "unexpected", "mismatch", "wrong value"],
            "recovery": ["rescan", "retry", "escalate"],
            "severity": 3
        },
        "UNKNOWN": {
            "detect": [],
            "recovery": ["rescan", "retry", "escalate"],
            "severity": 3
        },
    }
    @classmethod
    def classify(cls, error_text: str, context: str = "") -> str:
        combined = (error_text + " " + context).lower()
        best_mode = "UNKNOWN"
        best_score = 0
        for mode, config in cls.MODES.items():
            score = sum(1 for kw in config["detect"] if kw in combined)
            if score > best_score:
                best_score = score
                best_mode = mode
        return best_mode

    @classmethod
    def get_recovery(cls, mode: str) -> List[str]:
        return cls.MODES.get(mode, cls.MODES["UNKNOWN"]).get("recovery", ["escalate"])


# ── Skill Parser ──
