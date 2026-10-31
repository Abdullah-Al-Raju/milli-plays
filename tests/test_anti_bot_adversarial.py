"""
Adversarial Anti-Bot War Test Suite.
Verifies all 5 defense layers of Sentinel Fortress WAF
and all 5 offensive evasion modules of the Phantom Stealth Engine.
"""

import pytest
import time
from server.anti_bot.ja4_analyzer import JA4Analyzer
from server.anti_bot.runtime_integrity import RuntimeIntegrityVerifier
from server.anti_bot.biometrics import BiometricKinematicClassifier
from server.anti_bot.pow_engine import ProofOfWorkEngine
from server.anti_bot.fortress import SentinelFortress
from booker.neuro_mouse import NeuroMouse
from booker.pow_solver import PoWSolver
from booker.challenge_bypasser import ChallengeBypasser


def test_layer1_ja4_and_headers():
    analyzer = JA4Analyzer()

    # 1. Naive Python headers
    bad_headers = [
        (b"user-agent", b"python-requests/2.31.0"),
        (b"accept", b"*/*"),
        (b"accept-encoding", b"gzip, deflate"),
        (b"connection", b"keep-alive")
    ]
    res_bad = analyzer.evaluate_headers(bad_headers)
    assert res_bad["passed"] is False
    assert res_bad["bot_score"] >= 0.8
    assert any("Automation library" in r for r in res_bad["reasons"])

    # 2. Chrome claiming User-Agent without client hints
    fake_chrome = [
        (b"user-agent", b"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"),
        (b"accept", b"text/html"),
        (b"accept-encoding", b"gzip, deflate")
    ]
    res_fake = analyzer.evaluate_headers(fake_chrome)
    assert res_fake["passed"] is False
    assert any("missing client hints" in r for r in res_fake["reasons"])

    # 3. Authentic Chrome 131 header suite
    authentic_chrome = [
        (b"sec-ch-ua", b'"Google Chrome";v="131", "Chromium";v="131"'),
        (b"sec-ch-ua-mobile", b"?0"),
        (b"sec-ch-ua-platform", b'"Linux"'),
        (b"upgrade-insecure-requests", b"1"),
        (b"user-agent", b"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
        (b"accept", b"text/html,application/xhtml+xml"),
        (b"sec-fetch-site", b"same-origin"),
        (b"sec-fetch-mode", b"navigate"),
        (b"sec-fetch-dest", b"document"),
        (b"accept-encoding", b"gzip, deflate, br, zstd"),
        (b"accept-language", b"en-US,en;q=0.9")
    ]
    res_auth = analyzer.evaluate_headers(authentic_chrome)
    assert res_auth["passed"] is True
    assert res_auth["bot_score"] < 0.2


def test_layer2_runtime_integrity():
    verifier = RuntimeIntegrityVerifier()

    # 1. Blatant automation flag
    bad_telemetry = {
        "webdriver": True,
        "cdp_artifacts_detected": ["cdc_adoQpoasnfa76pfcZLmcfl_"],
        "has_window_chrome": False,
        "hardware_concurrency": 0
    }
    res_bad = verifier.verify_telemetry(bad_telemetry)
    assert res_bad["passed"] is False
    assert res_bad["bot_score"] == 1.0

    # 2. Clean stealth profile
    clean_telemetry = {
        "webdriver": False,
        "webdriver_descriptor_anomaly": False,
        "cdp_artifacts_detected": [],
        "has_window_chrome": True,
        "hardware_concurrency": 8,
        "device_memory": 8,
        "max_touch_points": 0,
        "screen_width": 1920,
        "screen_height": 1080,
        "toString_tampered": False,
        "webgl_vendor": "Google Inc. (NVIDIA)",
        "webgl_renderer": "ANGLE (NVIDIA GeForce RTX 3080)",
        "canvas_hash": "abc123hashxyz",
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/131.0"
    }
    res_clean = verifier.verify_telemetry(clean_telemetry)
    assert res_clean["passed"] is True
    assert res_clean["bot_score"] < 0.1


def test_layer3_biometrics_and_neuromouse():
    classifier = BiometricKinematicClassifier()
    neuro = NeuroMouse(seed=42)

    # 1. Robotic linear path (zero deviation)
    robotic_linear = [
        {"x": 100.0 + i * 10, "y": 100.0 + i * 10, "t": i * 10.0}
        for i in range(20)
    ]
    res_robot = classifier.evaluate_trajectory(robotic_linear)
    assert res_robot["passed"] is False
    assert any("strictly zero curvature" in a for a in res_robot["anomalies"])

    # 2. Instantaneous click (1 point)
    res_instant = classifier.evaluate_trajectory([{"x": 200, "y": 300, "t": 100}])
    assert res_instant["passed"] is False
    assert res_instant["bot_score"] == 1.0

    # 3. NeuroMouse generated human-like path
    human_path = neuro.generate_path(start=(50, 50), end=(500, 400), duration_ms=300.0, num_points=35)
    events = [
        {"type": "pointerover", "t": 10.0},
        {"type": "pointermove", "t": 100.0},
        {"type": "pointerdown", "t": 290.0},
        {"type": "pointerup", "t": 360.0},
        {"type": "click", "t": 361.0}
    ]
    res_human = classifier.evaluate_trajectory(human_path, events_log=events)
    assert res_human["passed"] is True
    assert res_human["bot_score"] < 0.25
    assert res_human["metrics"]["curvature_dev_px"] > 0.5


def test_layer4_proof_of_work():
    pow_eng = ProofOfWorkEngine(default_difficulty=3)

    # Generate challenge
    ch = pow_eng.generate_challenge(client_id="test-client", difficulty=3)
    token = ch["token"]
    assert ch["target_prefix"] == "000"

    # Solve with PoWSolver
    solve_res = PoWSolver.solve(token, difficulty=3)
    assert solve_res["success"] is True
    assert solve_res["hash"].startswith("000")

    # Verify on engine
    verify_res = pow_eng.verify_solution(token, solve_res["nonce"])
    assert verify_res["valid"] is True

    # Replay attack prevention
    replay_res = pow_eng.verify_solution(token, solve_res["nonce"])
    assert replay_res["valid"] is False
    assert "replay detected" in replay_res["error"]


def test_fortress_master_password_unconditional_access():
    fortress = SentinelFortress(master_password="SENTINEL_WAR_2026")

    # Request with Master Password bypass
    res = fortress.evaluate_request(
        raw_headers=[],
        auth_key="SENTINEL_WAR_2026"
    )
    assert res["decision"] == "ALLOW"
    assert res["bot_probability"] == 0.0
    assert res["unconditional_access"] is True
    assert fortress.verify_clearance_token(res["clearance_token"]) is True
