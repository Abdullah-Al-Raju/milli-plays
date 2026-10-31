"""
Module 5: Autonomous Challenge Bypasser.
Coordinates JA4 TLS client, PoW solver, and NeuroMouse biometrics
to solve Cloudflare Turnstile and Sentinel Fortress interstitials in sub-second time.
"""

import time
from typing import Dict, Any, Optional

from .phantom_tls import PhantomTLSClient
from .pow_solver import PoWSolver
from .neuro_mouse import NeuroMouse


class ChallengeBypasser:
    """
    Automated solver for Cloudflare Turnstile & Sentinel Fortress WAF challenges.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.tls_client = PhantomTLSClient(base_url=base_url)
        self.neuro = NeuroMouse()
        self.clearance_token: Optional[str] = None

    def bypass(self) -> Dict[str, Any]:
        """
        Executes end-to-end multi-layer challenge clearance:
        1. Fetches challenge token
        2. Solves cryptographic Proof-of-Work
        3. Generates realistic neuromuscular pointer trajectory
        4. Submits payload with Chrome 131 JA4 TLS fingerprint
        5. Extracts and stores sentinel_clearance token
        """
        t0 = time.perf_counter()

        # Step 1: Issue challenge
        res_issue = self.tls_client.get("/api/challenge/issue")
        if res_issue["status_code"] != 200:
            return {"success": False, "error": "Failed to fetch challenge token"}

        import json
        try:
            ch_data = json.loads(res_issue["text"])
        except Exception:
            return {"success": False, "error": "Invalid challenge response JSON"}

        token = ch_data["token"]
        diff = ch_data.get("difficulty", 4)

        # Step 2: Solve PoW
        pow_res = PoWSolver.solve(token, difficulty=diff)
        if not pow_res["success"]:
            return {"success": False, "error": "Failed to mine PoW solution"}

        # Step 3: Generate authentic Neuro-Kinetic trajectory (e.g. from (200, 300) to (450, 480))
        trajectory = self.neuro.generate_path(
            start=(210.0, 340.0),
            end=(460.0, 480.0),
            duration_ms=280.0,
            num_points=30
        )

        events = [
            {"type": "pointerover", "t": 10.0},
            {"type": "pointermove", "t": 120.0},
            {"type": "pointerdown", "t": 285.0},
            {"type": "pointerup", "t": 355.0},
            {"type": "click", "t": 356.0}
        ]

        # Step 4: Authentic environment telemetry (coherent with Chrome 131 on Linux)
        telemetry = {
            "webdriver": False,
            "webdriver_descriptor_anomaly": False,
            "cdp_artifacts_detected": [],
            "has_window_chrome": True,
            "hardware_concurrency": 8,
            "device_memory": 8,
            "max_touch_points": 0,
            "languages": ["en-US", "en"],
            "screen_width": 1920,
            "screen_height": 1080,
            "toString_tampered": False,
            "webgl_vendor": "Google Inc. (NVIDIA)",
            "webgl_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
            "canvas_hash": "a1b2c3d4e5f67890123456789abcdef0",
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }

        # Step 5: Verify challenge with Chrome 131 TLS and headers
        verify_payload = {
            "pow_token": token,
            "pow_nonce": pow_res["nonce"],
            "telemetry": telemetry,
            "trajectory": trajectory,
            "events": events
        }

        verify_res = self.tls_client.post("/api/challenge/verify", json_data=verify_payload)
        data = verify_res.get("data", {})

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        if data.get("success"):
            self.clearance_token = data.get("clearance_token")
            return {
                "success": True,
                "clearance_token": self.clearance_token,
                "bot_probability": data.get("bot_probability", 0.0),
                "pow_duration_ms": pow_res["duration_ms"],
                "total_bypass_ms": round(elapsed_ms, 2),
                "unconditional_access": data.get("unconditional_access", False)
            }
        else:
            return {
                "success": False,
                "bot_probability": data.get("bot_probability", 1.0),
                "anomalies": data.get("anomalies", []),
                "total_bypass_ms": round(elapsed_ms, 2)
            }
