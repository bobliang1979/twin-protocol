"""
twin_protocol.standby — Hot Standby Protocol Extension

Allows one agent to monitor another and take over if it fails.
Uses the existing heartbeat mechanism + two new message types.

Message types:
  takeover_request  — Agent B requests to take over for Agent A
  takeover_ack      — Agent A (or its watchdog) acknowledges the takeover

Usage:
    from twin_protocol.standby import HotStandby

    # Monitor another agent
    standby = HotStandby("agent-b", "agent-a")
    standby.start_monitoring(heartbeat_path=".daemon.heartbeat", interval=30)

    # If heartbeat stops:
    #   → sends takeover_request to outbox
    #   → other agents see the request and adjust
"""
import json, os, time, uuid
from pathlib import Path


def _ts():
    import datetime
    return datetime.datetime.utcnow().isoformat() + "Z"


class HotStandby:
    """Monitor another agent and take over if it fails."""

    def __init__(self, my_name: str, target_name: str, outbox_path: str = None):
        self.my_name = my_name
        self.target_name = target_name
        self.outbox_path = outbox_path or str(
            Path.home() / "Desktop/hermes_codex_bridge/twins_standby_outbox.jsonl"
        )

    def check_heartbeat(self, heartbeat_path: str, max_age: int = 60) -> bool:
        """Check if the target agent is alive via heartbeat file."""
        hb = Path(heartbeat_path)
        if not hb.exists():
            return False
        age = time.time() - hb.stat().st_mtime
        return age < max_age

    def send_takeover_request(self, reason: str = "Heartbeat timeout") -> dict:
        """Send a takeover_request to the outbox."""
        msg = {
            "type": "takeover_request",
            "source": self.my_name,
            "target": self.target_name,
            "id": str(uuid.uuid4()),
            "timestamp": _ts(),
            "payload": {
                "reason": reason,
                "requester": self.my_name,
            }
        }
        with open(self.outbox_path, "a") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        return msg

    def send_takeover_ack(self, request_id: str, accepted: bool = True) -> dict:
        """Respond to a takeover request."""
        msg = {
            "type": "takeover_ack",
            "source": self.my_name,
            "target": "all",
            "id": str(uuid.uuid4()),
            "timestamp": _ts(),
            "payload": {
                "request_id": request_id,
                "accepted": accepted,
                "message": "Taking over responsibilities" if accepted else "Denied takeover"
            }
        }
        with open(self.outbox_path, "a") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        return msg

    def start_monitoring(self, heartbeat_path: str, interval: int = 30):
        """Continuously monitor target agent's heartbeat."""
        print(f"🧬 HotStandby: {self.my_name} monitoring {self.target_name}")
        print(f"  Heartbeat: {heartbeat_path}")
        print(f"  Interval: {interval}s")
        print(f"  Outbox: {self.outbox_path}")
        print()

        last_takeover = 0
        while True:
            alive = self.check_heartbeat(heartbeat_path)
            status = "✅ ALIVE" if alive else "❌ DOWN"

            if not alive and time.time() - last_takeover > 300:
                print(f"  {_ts()} {self.target_name}: {status} — Sending takeover request")
                self.send_takeover_request()
                last_takeover = time.time()
            elif not alive:
                print(f"  {_ts()} {self.target_name}: {status} (takeover already requested)")
            else:
                pass  # Healthy, no action

            time.sleep(interval)

