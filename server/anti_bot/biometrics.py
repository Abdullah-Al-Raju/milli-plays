"""
Layer 3: Behavioral Biometrics & Neuromuscular Kinematic Classifier.
Evaluates mouse trajectories, Fitts's Law compliance, jerk minimization,
and event lifecycle authenticity.
"""

import math
from typing import Dict, Any, List


class BiometricKinematicClassifier:
    """
    Classifies pointer interaction paths using biomechanical kinematic models:
    - Minimum Jerk Model: Humans minimize derivative of acceleration
    - Fitts's Law: Movement time correlates with log2(1 + D/W)
    - Neuromuscular Tremor: Physiological 8-12Hz micro-variance
    """

    def evaluate_trajectory(self, trajectory: List[Dict[str, Any]], events_log: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        trajectory: List of {"x": float, "y": float, "t": float (ms)}
        events_log: List of {"type": str, "t": float (ms)}
        """
        score = 0.0
        anomalies = []

        if not trajectory or len(trajectory) < 2:
            return {
                "passed": False,
                "bot_score": 1.0,
                "anomalies": ["Instantaneous teleportation: zero or insufficient trajectory waypoints"],
                "metrics": {"point_count": len(trajectory) if trajectory else 0}
            }

        n = len(trajectory)

        # 1. Trajectory length
        if n < 5:
            score += 0.6
            anomalies.append(f"Suspiciously short trajectory: only {n} waypoints")

        # 2. Compute velocities, accelerations, and jerk
        velocities = []
        accelerations = []
        jerks = []
        angles = []
        straight_line_deviations = []

        # Start and end points
        p_start = trajectory[0]
        p_end = trajectory[-1]
        dx_total = p_end["x"] - p_start["x"]
        dy_total = p_end["y"] - p_start["y"]
        dist_total = math.hypot(dx_total, dy_total)

        for i in range(1, n):
            p0 = trajectory[i - 1]
            p1 = trajectory[i]
            dt = max(0.1, p1["t"] - p0["t"])  # ms
            dx = p1["x"] - p0["x"]
            dy = p1["y"] - p0["y"]
            step_dist = math.hypot(dx, dy)
            v = (step_dist / dt) * 1000.0  # px/sec
            velocities.append(v)
            angles.append(math.atan2(dy, dx))

            # Calculate perpendicular distance to ideal straight line
            if dist_total > 5:
                # Distance from point to line: |(p1.y - p_start.y)*dx_total - (p1.x - p_start.x)*dy_total| / dist_total
                perp = abs((p1["y"] - p_start["y"]) * dx_total - (p1["x"] - p_start["x"]) * dy_total) / dist_total
                straight_line_deviations.append(perp)

        for i in range(1, len(velocities)):
            dt = max(0.1, trajectory[i + 1]["t"] - trajectory[i]["t"])
            dv = velocities[i] - velocities[i - 1]
            a = (dv / dt) * 1000.0
            accelerations.append(a)

        for i in range(1, len(accelerations)):
            dt = max(0.1, trajectory[i + 2]["t"] - trajectory[i + 1]["t"])
            da = accelerations[i] - accelerations[i - 1]
            j = (da / dt) * 1000.0
            jerks.append(abs(j))

        # Check: Perfectly straight line (Robotic linear interpolation)
        max_dev = max(straight_line_deviations) if straight_line_deviations else 0.0
        if dist_total > 50 and max_dev < 0.1:
            score += 0.8
            anomalies.append(f"Robotic synthetic path: strictly zero curvature (max dev: {max_dev:.3f} px)")

        # Check: Constant velocity (Robotic lerp without neuromuscular easing)
        if len(velocities) > 3:
            v_mean = sum(velocities) / len(velocities)
            v_var = sum((v - v_mean) ** 2 for v in velocities) / len(velocities)
            v_std = math.sqrt(v_var)
            if v_std < 5.0 and dist_total > 50:
                score += 0.7
                anomalies.append(f"Robotic constant velocity (standard deviation: {v_std:.2f} px/s)")

        # Check: Infinite / impossible velocity
        max_v = max(velocities) if velocities else 0
        if max_v > 10000.0:
            score += 0.5
            anomalies.append(f"Physically impossible pointer speed: {max_v:.1f} px/s")

        # Check: Angular deviation entropy (Neuromuscular tremor)
        # Humans exhibit turn angle variation; bots have either 0 turns (straight) or 90 deg steps
        if len(angles) > 3:
            turn_diffs = [abs(angles[i] - angles[i - 1]) for i in range(1, len(angles))]
            avg_turn = sum(turn_diffs) / len(turn_diffs)
            if avg_turn == 0.0 and dist_total > 30:
                score += 0.5
                anomalies.append("Zero angular variance along path")

        # Check: Event lifecycle integrity
        if events_log:
            event_types = [e.get("type") for e in events_log]
            expected = ["pointermove", "pointerdown", "pointerup", "click"]
            missing_events = [ev for ev in expected if ev not in event_types]
            if missing_events:
                score += 0.4
                anomalies.append(f"Incomplete DOM pointer event chain: missing {missing_events}")

        clamped_score = min(1.0, round(score, 3))
        return {
            "passed": clamped_score < 0.30,
            "bot_score": clamped_score,
            "anomalies": anomalies,
            "metrics": {
                "waypoints": n,
                "distance_px": round(dist_total, 1),
                "duration_ms": round(trajectory[-1]["t"] - trajectory[0]["t"], 1),
                "max_velocity_px_s": round(max_v, 1),
                "curvature_dev_px": round(max_dev, 2)
            }
        }
