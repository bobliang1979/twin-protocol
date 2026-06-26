"""
twin_protocol.identity — Agent Identity with Ed25519 signing (cryptography)

Each agent has a unique key pair. Every message is signed with Ed25519.
Other agents verify the signature to confirm authenticity.

Usage:
    from twin_protocol.identity import AgentIdentity

    alice = AgentIdentity("alice")
    if not alice.load():
        alice.generate()

    signed = alice.sign({"type": "message", "payload": {"text": "hello"}})

    result = AgentIdentity.verify_message(signed, known_keys={"alice": alice.public_key})
    print(result.valid)  # True
"""
import json, base64, os, uuid
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, PublicFormat, NoEncryption,
    load_der_private_key, load_der_public_key,
)
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature


@dataclass
class VerificationResult:
    valid: bool = False
    signer: str = ""
    error: str = ""


_IDENTITY_DIR = Path.home() / ".twins"


class AgentIdentity:
    """Agent identity with Ed25519 key pair."""

    def __init__(self, agent_name: str = "default"):
        self.name = agent_name
        self._dir = _IDENTITY_DIR / agent_name
        self._pub_path = self._dir / "identity.pub"
        self._priv_path = self._dir / "identity.key"
        self.public_key: Optional[bytes] = None
        self._private_key: Optional[ed25519.Ed25519PrivateKey] = None

    def generate(self):
        """Generate a new Ed25519 key pair."""
        self._dir.mkdir(parents=True, exist_ok=True)
        self._private_key = ed25519.Ed25519PrivateKey.generate()
        self.public_key = self._private_key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )
        self._save()
        return self

    def _save(self):
        priv_der = self._private_key.private_bytes(
            Encoding.DER, PrivateFormat.PKCS8, NoEncryption()
        )
        self._pub_path.write_bytes(self.public_key)
        self._priv_path.write_bytes(priv_der)

    def load(self) -> bool:
        """Load existing key pair. Returns True if loaded."""
        if not self._priv_path.exists():
            return False
        try:
            with open(self._priv_path, "rb") as f:
                self._private_key = load_der_private_key(f.read(), None)
            self.public_key = self._private_key.public_key().public_bytes(
                Encoding.Raw, PublicFormat.Raw
            )
            return True
        except Exception:
            return False

    def exists(self) -> bool:
        return self._priv_path.exists()

    def sign(self, msg: dict) -> dict:
        """Sign a message dict with Ed25519. Returns message with 'signature' and 'signer' fields."""
        if not self._private_key:
            raise ValueError("No private key. Call generate() or load() first.")

        canonical = _canonicalize(msg, self.name)
        sig = self._private_key.sign(canonical)

        signed = dict(msg)
        signed["signature"] = base64.b64encode(sig).decode()
        signed["signer"] = self.name
        return signed

    @classmethod
    def verify_message(
        cls, msg: dict, known_keys: Dict[str, bytes] = None
    ) -> VerificationResult:
        """Verify a signed message against known public keys."""
        sig_b64 = msg.get("signature", "")
        signer = msg.get("signer", "")
        if not sig_b64 or not signer:
            return VerificationResult(False, error="Missing signature or signer")

        try:
            sig = base64.b64decode(sig_b64)
        except Exception:
            return VerificationResult(False, signer=signer, error="Invalid signature encoding")

        # Get public key
        pub = None
        if known_keys and signer in known_keys:
            pub = known_keys[signer]
        else:
            key_path = _IDENTITY_DIR / signer / "identity.pub"
            if key_path.exists():
                pub = key_path.read_bytes()

        if not pub:
            return VerificationResult(False, signer=signer, error=f"No public key for {signer}")

        canonical = _canonicalize(msg, signer, for_verify=True)

        try:
            pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub)
            pub_key.verify(sig, canonical)
            return VerificationResult(True, signer=signer)
        except InvalidSignature:
            return VerificationResult(False, signer=signer, error="Invalid signature")
        except Exception as e:
            return VerificationResult(False, signer=signer, error=str(e))


def _hash(data: bytes) -> bytes:
    d = hashes.Hash(hashes.SHA256())
    d.update(data)
    return d.finalize()


def _canonicalize(msg: dict, signer: str, for_verify: bool = False) -> bytes:
    """Build canonical representation of message for signing."""
    payload = msg.get("payload") or {}
    signable = {
        "type": msg.get("type", "message"),
        "source": signer,
        "timestamp": msg.get("timestamp", ""),
        "id": msg.get("id", ""),
    }
    if payload:
        signable["payload_hash"] = base64.b64encode(
            _hash(json.dumps(payload, sort_keys=True).encode())
        ).decode()
    if "tool" in msg:
        signable["tool"] = msg["tool"]
    if "request_id" in msg:
        signable["request_id"] = msg["request_id"]
    if "params" in msg:
        signable["params_hash"] = base64.b64encode(
            _hash(json.dumps(msg["params"], sort_keys=True).encode())
        ).decode()

    return json.dumps(signable, sort_keys=True).encode()
