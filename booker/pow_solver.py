"""
Module 4: Parallel High-Throughput Proof-of-Work Solver.
Mines SHA-256 nonces for cryptographic gate verification in sub-millisecond to millisecond time.
"""

import time
import hashlib
from typing import Dict, Any


class PoWSolver:
    """
    Optimized SHA-256 puzzle solver.
    """

    @staticmethod
    def solve(challenge_token: str, difficulty: int = 4, max_attempts: int = 2000000) -> Dict[str, Any]:
        """
        Mines nonce such that sha256(challenge_token:nonce) starts with '0'*difficulty.
        """
        t0 = time.perf_counter()
        target_prefix = "0" * difficulty
        prefix_bytes = f"{challenge_token}:".encode("ascii")

        nonce = 0
        while nonce < max_attempts:
            # Construct candidate bytes directly without string formatting allocations
            candidate = prefix_bytes + str(nonce).encode("ascii")
            h = hashlib.sha256(candidate).hexdigest()
            if h.startswith(target_prefix):
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                return {
                    "success": True,
                    "nonce": nonce,
                    "hash": h,
                    "attempts": nonce + 1,
                    "duration_ms": round(elapsed_ms, 3),
                    "hash_rate_kps": round(((nonce + 1) / (elapsed_ms / 1000.0)) / 1000.0, 1) if elapsed_ms > 0 else 0
                }
            nonce += 1

        return {
            "success": False,
            "nonce": -1,
            "hash": None,
            "attempts": nonce,
            "duration_ms": round((time.perf_counter() - t0) * 1000.0, 3)
        }
