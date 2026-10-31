"""
Layer 4: Cryptographic Proof-of-Work (PoW) Challenge Engine.
Generates dynamically tuned anti-replay computational puzzles.
Simulates Kasada / Cloudflare Turnstile cryptographic gate challenges.
"""

import time
import uuid
import hmac
import hashlib
from typing import Dict, Any, Optional, Set


class ProofOfWorkEngine:
    """
    Issues and verifies time-bounded cryptographic Proof-of-Work challenges.
    """

    def __init__(self, secret: str = "sentinel-fortress-secret-key-2026", default_difficulty: int = 4):
        self.secret = secret.encode("utf-8")
        self.default_difficulty = default_difficulty  # 4 hex zeros = 16-bit challenge (~65,536 hash space)
        self.used_nonces: Set[str] = set()
        self.nonce_timestamps: Dict[str, float] = {}

    def generate_challenge(self, client_id: str, difficulty: Optional[int] = None) -> Dict[str, Any]:
        """Generates cryptographically signed PoW puzzle."""
        diff = difficulty or self.default_difficulty
        salt = uuid.uuid4().hex[:12]
        timestamp = time.time()
        payload = f"{client_id}:{salt}:{timestamp:.3f}:{diff}"
        sig = hmac.new(self.secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        token = f"{payload}:{sig}"

        return {
            "token": token,
            "salt": salt,
            "difficulty": diff,
            "target_prefix": "0" * diff,
            "timestamp": timestamp,
            "expires_in_sec": 120
        }

    def verify_solution(self, challenge_token: str, nonce: int) -> Dict[str, Any]:
        """
        Verifies client's mined nonce against challenge token in microsecond time.
        """
        now = time.time()
        self._prune_expired_nonces(now)

        if not challenge_token:
            return {"valid": False, "error": "Missing challenge token"}

        try:
            parts = challenge_token.split(":")
            if len(parts) != 5:
                return {"valid": False, "error": "Malformed challenge token structure"}

            client_id, salt, ts_str, diff_str, sig = parts
            ts = float(ts_str)
            diff = int(diff_str)

            # 1. Anti-replay check
            nonce_key = f"{challenge_token}:{nonce}"
            if nonce_key in self.used_nonces:
                return {"valid": False, "error": "Challenge nonce replay detected"}

            # 2. Expiration check (120 seconds)
            if now - ts > 120.0:
                return {"valid": False, "error": "Challenge expired"}

            # 3. Signature verification
            payload = f"{client_id}:{salt}:{ts_str}:{diff_str}"
            expected_sig = hmac.new(self.secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                return {"valid": False, "error": "Invalid challenge signature"}

            # 4. Hash verification
            target_prefix = "0" * diff
            candidate = f"{challenge_token}:{nonce}".encode("utf-8")
            h = hashlib.sha256(candidate).hexdigest()

            if not h.startswith(target_prefix):
                return {
                    "valid": False,
                    "error": f"Hash {h[:8]} does not satisfy difficulty target {target_prefix}"
                }

            # Record nonce
            self.used_nonces.add(nonce_key)
            self.nonce_timestamps[nonce_key] = now

            return {
                "valid": True,
                "client_id": client_id,
                "difficulty": diff,
                "hash": h
            }
        except Exception as e:
            return {"valid": False, "error": f"Verification exception: {str(e)}"}

    def _prune_expired_nonces(self, now: float):
        """Cleans up nonces older than 180 seconds."""
        if len(self.used_nonces) > 5000:
            expired = [k for k, ts in self.nonce_timestamps.items() if now - ts > 180.0]
            for k in expired:
                self.used_nonces.discard(k)
                del self.nonce_timestamps[k]
