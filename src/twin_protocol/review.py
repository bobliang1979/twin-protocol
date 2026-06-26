"""
twin_protocol.review — Code Review Protocol Extension

Standardizes the "mutual code review" pattern as Twin Protocol message types.
Any two agents can review each other's code through the shared outbox.

Message types:
  review_request  — Agent A submits code for Agent B to review
  review_result   — Agent B returns review findings

Usage:
    from twin_protocol.review import ReviewRequest, ReviewResult

    # Agent A sends a review request
    req = ReviewRequest(
        source="agent-a",
        target="agent-b",
        code="def hello(): print('world')",
        language="python",
        context="The main greeting function"
    )
    outbox.append(req.to_json())

    # Agent B reads and responds
    result = ReviewResult(
        source="agent-b",
        target="agent-a",
        request_id=req.request_id,
        approved=False,
        issues=[
            {"severity": "LOW", "line": 1, "message": "Missing return type hint"},
            {"severity": "INFO", "message": "Consider using f-string"}
        ],
        suggested_fix="def hello() -> None: print('world')"
    )
    outbox.append(result.to_json())
"""
import json, uuid, time
from dataclasses import dataclass, field
from typing import Optional


def _ts():
    return datetime.datetime.utcnow().isoformat() + "Z" if __import__('datetime') else time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class ReviewRequest:
    """A request for another agent to review code."""
    source: str
    target: str
    code: str
    language: str = ""
    context: str = ""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: str = field(default_factory=_ts)

    def to_json(self) -> str:
        return json.dumps({
            "type": "review_request",
            "source": self.source,
            "target": self.target,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "payload": {
                "code": self.code,
                "language": self.language,
                "context": self.context,
            }
        }, ensure_ascii=False)


@dataclass
class ReviewIssue:
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    line: int = 0
    message: str = ""
    suggestion: str = ""


@dataclass
class ReviewResult:
    """Result of a code review."""
    source: str
    target: str
    request_id: str
    approved: bool = False
    issues: list = field(default_factory=list)
    summary: str = ""
    suggested_fix: str = ""
    timestamp: str = field(default_factory=_ts)

    def to_json(self) -> str:
        return json.dumps({
            "type": "review_result",
            "source": self.source,
            "target": self.target,
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "payload": {
                "approved": self.approved,
                "issues": self.issues,
                "summary": self.summary,
                "suggested_fix": self.suggested_fix,
            }
        }, ensure_ascii=False)


def auto_review(code: str, language: str = "") -> ReviewResult:
    """
    Automated code review using static analysis rules.
    Can be used by any agent without an LLM — pure rule-based.
    """
    issues = []

    lines = code.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Check for potential issues
        if stripped.startswith("def ") and ")" in stripped and ":" in stripped:
            # No return type hint?
            if "->" not in stripped:
                issues.append(ReviewIssue(
                    severity="LOW", line=i,
                    message=f"Function '{stripped.split('(')[0].replace('def ','')}' missing return type hint"
                ))

        # Bare except
        if stripped == "except:" or stripped.startswith("except :"):
            issues.append(ReviewIssue(
                severity="HIGH", line=i,
                message="Bare except clause — catches all exceptions"
            ))

        # Hardcoded secrets
        import re
        secrets = re.findall(r'(api_key|secret|password|token)\s*=\s*["\'][^"\']{8,}["\']', line, re.I)
        for s in secrets:
            issues.append(ReviewIssue(
                severity="CRITICAL", line=i,
                message=f"Possible hardcoded secret: {s}"
            ))

        # Long lines
        if len(line) > 120:
            issues.append(ReviewIssue(
                severity="INFO", line=i,
                message=f"Line too long ({len(line)} chars, max 120)"
            ))

        # TODO/FIXME
        if "TODO" in stripped or "FIXME" in stripped:
            issues.append(ReviewIssue(
                severity="INFO", line=i,
                message=f"Unresolved {'TODO' if 'TODO' in stripped else 'FIXME'}"
            ))

    critical = sum(1 for i in issues if i.severity == "CRITICAL")
    high = sum(1 for i in issues if i.severity == "HIGH")

    return ReviewResult(
        source="auto-review",
        target="author",
        request_id="",
        approved=(critical == 0 and high == 0),
        issues=[i.__dict__ for i in issues],
        summary=f"Found {len(issues)} issues ({critical} critical, {high} high)"
    )

