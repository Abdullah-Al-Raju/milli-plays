"""
The Sentinel Fortress WAF & Anti-Bot Gateway.
Orchestrates 5-layer bot classification, password protection, and clearance token signing.
"""

import time
import os
import hmac
import hashlib
from typing import Dict, Any, Optional, List

from .ja4_analyzer import JA4Analyzer
from .runtime_integrity import RuntimeIntegrityVerifier
from .biometrics import BiometricKinematicClassifier
from .pow_engine import ProofOfWorkEngine


class SentinelFortress:
    """
    Multi-Layered Anti-Bot Scoring Gateway.
    Computes weighted bot probability scores and issues cryptographically signed clearance passes.
    """

    def __init__(self, master_password: str = "SENTINEL_WAR_2026"):
        self.master_password = os.environ.get("SENTINEL_ADMIN_KEY", master_password)
        self.secret_key = b"sentinel-waf-crypto-core-2026"
        self.ja4 = JA4Analyzer()
        self.integrity = RuntimeIntegrityVerifier()
        self.biometrics = BiometricKinematicClassifier()
        self.pow = ProofOfWorkEngine()

        # Telemetry ring buffer for live dashboard
        self.audit_log: List[Dict[str, Any]] = []
        self.enabled = True

    def check_unconditional_admin(self, auth_header: Optional[str] = None, cookie_token: Optional[str] = None) -> bool:
        """
        Grants unconditional access if the master password matches.
        Allows unconditional bypass for the developer/operator.
        """
        if auth_header and auth_header == self.master_password:
            return True
        if cookie_token and cookie_token == self.master_password:
            return True
        return False

    def issue_clearance_token(self, client_id: str, bot_score: float, ttl_seconds: float = 600.0) -> str:
        """Issues HMAC-signed clearance token when client passes all anti-bot layers."""
        expiry = time.time() + ttl_seconds
        payload = f"{client_id}:{bot_score:.3f}:{expiry:.3f}"
        sig = hmac.new(self.secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload}:{sig}"

    def verify_clearance_token(self, token: str) -> bool:
        """Verifies integrity and expiration of a clearance token."""
        if not token:
            return False
        try:
            parts = token.split(":")
            if len(parts) != 4:
                return False
            client_id, score_str, expiry_str, sig = parts
            expiry = float(expiry_str)
            if time.time() > expiry:
                return False
            payload = f"{client_id}:{score_str}:{expiry_str}"
            expected_sig = hmac.new(self.secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
            return hmac.compare_digest(sig, expected_sig)
        except Exception:
            return False

    def evaluate_request(
        self,
        raw_headers: List[tuple],
        telemetry: Optional[Dict[str, Any]] = None,
        trajectory: Optional[List[Dict[str, Any]]] = None,
        pow_token: Optional[str] = None,
        pow_nonce: Optional[int] = None,
        auth_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end multi-layer evaluation.
        """
        t0 = time.perf_counter()

        # Check for unconditional admin bypass
        if self.check_unconditional_admin(auth_key):
            log_entry = {
                "timestamp": time.time(),
                "action": "ALLOW",
                "reason": "Unconditional Master Password Bypass",
                "bot_score": 0.0,
                "latency_us": round((time.perf_counter() - t0) * 1000000.0, 1)
            }
            self._record_audit(log_entry)
            return {
                "decision": "ALLOW",
                "bot_probability": 0.0,
                "clearance_token": self.issue_clearance_token("admin", 0.0),
                "unconditional_access": True,
                "details": log_entry
            }

        # 1. Layer 1: Network & Header JA4 Analysis
        l1 = self.ja4.evaluate_headers(raw_headers)

        # 2. Layer 2: Runtime Integrity
        l2 = self.integrity.verify_telemetry(telemetry or {})

        # 3. Layer 3: Behavioral Biometrics
        l3 = self.biometrics.evaluate_trajectory(trajectory or [])

        # 4. Layer 4: Proof-of-Work
        l4_valid = False
        l4_error = None
        if pow_token and pow_nonce is not None:
            l4_res = self.pow.verify_solution(pow_token, pow_nonce)
            l4_valid = l4_res.get("valid", False)
            l4_error = l4_res.get("error")
        else:
            l4_error = "PoW challenge not submitted"

        # Compute weighted composite bot probability
        # Weights: L1 (Headers): 0.25 | L2 (Integrity): 0.35 | L3 (Biometrics): 0.25 | L4 (PoW): 0.15
        s1 = l1["bot_score"]
        s2 = l2["bot_score"]
        s3 = l3["bot_score"]
        s4 = 0.0 if l4_valid else 1.0

        composite_score = round((0.25 * s1) + (0.35 * s2) + (0.25 * s3) + (0.15 * s4), 3)

        decision = "ALLOW" if composite_score < 0.25 else ("CHALLENGE" if composite_score < 0.65 else "BLOCK")
        clearance_token = self.issue_clearance_token("client", composite_score) if decision == "ALLOW" else None

        elapsed_us = (time.perf_counter() - t0) * 1000000.0

        log_entry = {
            "timestamp": time.time(),
            "action": decision,
            "bot_score": composite_score,
            "latency_us": round(elapsed_us, 1),
            "layer_scores": {
                "L1_headers": s1,
                "L2_integrity": s2,
                "L3_biometrics": s3,
                "L4_pow": s4
            },
            "anomalies": l1["reasons"] + l2["anomalies"] + l3["anomalies"] + ([l4_error] if l4_error else [])
        }
        self._record_audit(log_entry)

        return {
            "decision": decision,
            "bot_probability": composite_score,
            "clearance_token": clearance_token,
            "unconditional_access": False,
            "details": log_entry
        }

    def _record_audit(self, entry: Dict[str, Any]):
        self.audit_log.append(entry)
        if len(self.audit_log) > 200:
            self.audit_log.pop(0)


# Global singleton instance
fortress_instance = SentinelFortress()
