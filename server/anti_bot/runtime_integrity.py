"""
Layer 2: Browser Runtime & Device Integrity Verifier.
Validates client-side execution environment fingerprints, CDP automation artifacts,
and prototype integrity.
"""

from typing import Dict, Any, List


class RuntimeIntegrityVerifier:
    """
    Validates browser environment telemetry submitted by the client-side probe.
    """

    VALID_HARDWARE_CONCURRENCY = {2, 4, 6, 8, 12, 16, 24, 32, 64}
    VALID_DEVICE_MEMORY = {1, 2, 4, 8, 16, 32}

    def verify_telemetry(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates client telemetry dict.
        Returns: {passed: bool, bot_score: float, anomalies: List[str]}
        """
        score = 0.0
        anomalies = []

        if not telemetry:
            return {
                "passed": False,
                "bot_score": 1.0,
                "anomalies": ["Missing browser runtime telemetry payload"]
            }

        # 1. WebDriver flag check
        if telemetry.get("webdriver") is True:
            score += 1.0
            anomalies.append("navigator.webdriver is TRUE")

        if telemetry.get("webdriver_descriptor_anomaly") is True:
            score += 0.6
            anomalies.append("navigator.webdriver descriptor tampered or patched clumsily")

        # 2. Automation & CDP hooks check
        cdp_detected = telemetry.get("cdp_artifacts_detected", [])
        if cdp_detected:
            score += 1.0
            anomalies.append(f"CDP automation artifacts detected: {cdp_detected}")

        # 3. window.chrome check (on Chrome / Chromium)
        user_agent = telemetry.get("user_agent", "").lower()
        if "chrome" in user_agent and not telemetry.get("has_window_chrome", False):
            score += 0.7
            anomalies.append("Chrome User-Agent without window.chrome object")

        # 4. Hardware profile consistency
        cores = telemetry.get("hardware_concurrency")
        if cores is not None and cores not in self.VALID_HARDWARE_CONCURRENCY:
            score += 0.4
            anomalies.append(f"Anomalous CPU core count: {cores}")

        mem = telemetry.get("device_memory")
        if mem is not None and mem not in self.VALID_DEVICE_MEMORY:
            score += 0.4
            anomalies.append(f"Anomalous device memory: {mem} GB")

        # 5. Screen dimensions
        screen_w = telemetry.get("screen_width", 0)
        screen_h = telemetry.get("screen_height", 0)
        if screen_w <= 0 or screen_h <= 0 or (screen_w == 800 and screen_h == 600):
            score += 0.35
            anomalies.append(f"Suspicious screen dimensions: {screen_w}x{screen_h} (default headless)")

        # 6. Function.prototype.toString tampering
        if telemetry.get("toString_tampered") is True:
            score += 0.8
            anomalies.append("Function.prototype.toString inspection reveals patched proxy hooks")

        # 7. WebGL & Canvas checks
        webgl_vendor = telemetry.get("webgl_vendor", "")
        webgl_renderer = telemetry.get("webgl_renderer", "")
        if "llvmpipe" in webgl_renderer.lower() or "swiftshader" in webgl_renderer.lower():
            score += 0.85
            anomalies.append(f"Software emulation graphics driver detected: {webgl_renderer}")

        if not telemetry.get("canvas_hash"):
            score += 0.3
            anomalies.append("Missing Canvas 2D fingerprint hash")

        clamped_score = min(1.0, round(score, 3))
        return {
            "passed": clamped_score < 0.25,
            "bot_score": clamped_score,
            "anomalies": anomalies,
            "device_profile": {
                "cores": cores,
                "memory": mem,
                "webgl": webgl_renderer[:40] if webgl_renderer else "unknown"
            }
        }
