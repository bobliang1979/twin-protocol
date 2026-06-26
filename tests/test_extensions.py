"""Test review.py and standby.py modules"""
import sys, json, tempfile, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from twin_protocol.test_suite import test

# ── Review Tests ──
try:
    from twin_protocol.review import ReviewRequest, ReviewResult, ReviewIssue, auto_review

    req = ReviewRequest(source="a", target="b", code="def hello(): pass", language="python")
    j = req.to_json()
    test("ReviewRequest serialization", "review_request" in j and "def hello" in j)

    result = auto_review("def bad():\n    pass\nexcept:\n    x = 1\n", "python")
    test("auto_review finds bare except", any("bare except" in i.get("message", "").lower() for i in result.issues))
    test("auto_review returns issues", len(result.issues) > 0)

    result2 = auto_review("def hello() -> None:\n    print('ok')\n", "python")
    test("auto_review clean code approved", result2.approved)

    print("  ✅ Code review tests passed")
except Exception as e:
    test("Code review tests", False, str(e))

# ── Standby Tests ──
try:
    from twin_protocol.standby import HotStandby

    tmp = Path(tempfile.mkdtemp())
    hb = tmp / "test_heartbeat"
    hb.write_text("alive")
    outbox = tmp / "test_outbox.jsonl"

    standby = HotStandby("agent-b", "agent-a", outbox_path=str(outbox))

    alive = standby.check_heartbeat(str(hb), max_age=60)
    test("HotStandby detects alive heartbeat", alive)

    msg = standby.send_takeover_request(reason="Test")
    test("takeover_request type", msg.get("type") == "takeover_request")
    test("takeover_request source", msg.get("source") == "agent-b")
    test("takeover_request has reason", "reason" in msg.get("payload", {}))
    test("takeover written to outbox", outbox.exists() and outbox.stat().st_size > 0)

    ack = standby.send_takeover_ack(request_id=msg.get("id", ""), accepted=True)
    test("takeover_ack type", ack.get("type") == "takeover_ack")
    test("takeover_ack accepted", ack.get("payload", {}).get("accepted") is True)

    shutil.rmtree(tmp)
    print("  ✅ Hot Standby tests passed")
except Exception as e:
    test("Hot Standby tests", False, str(e))
