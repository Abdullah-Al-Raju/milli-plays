"""
Module 3: Neuromuscular Kinetic Trajectory Generator (NeuroMouse).
Generates human-like pointer trajectories following Fitts's Law, minimum jerk polynomials,
physiological tremor, and target hunting overshoot.
"""

import math
import random
from typing import List, Dict, Any, Tuple


class NeuroMouse:
    """
    Generates authentic human arm/wrist neuromuscular pointer paths.
    """

    def __init__(self, seed: Optional_int = None):
        self.rng = random.Random(seed)

    def generate_path(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        duration_ms: float = 350.0,
        num_points: int = 35
    ) -> List[Dict[str, Any]]:
        """
        Generates array of {"x": float, "y": float, "t": float (ms)} waypoints.
        """
        x0, y0 = start
        x3, y3 = end
        dx = x3 - x0
        dy = y3 - y0
        dist = math.hypot(dx, dy)

        if dist < 2.0:
            return [
                {"x": round(x0, 2), "y": round(y0, 2), "t": 0.0},
                {"x": round(x3, 2), "y": round(y3, 2), "t": duration_ms}
            ]

        # Orthogonal unit vector
        ux = -dy / dist
        uy = dx / dist

        # 1. Cubic Bézier control points with randomized curvature
        curvature_scale = min(80.0, dist * self.rng.uniform(0.12, 0.28))
        side = 1 if self.rng.random() > 0.5 else -1

        p1_offset = side * curvature_scale * self.rng.uniform(0.6, 1.2)
        p2_offset = side * curvature_scale * self.rng.uniform(0.4, 0.9)

        x1 = x0 + dx * 0.3 + ux * p1_offset
        y1 = y0 + dy * 0.3 + uy * p1_offset

        # Slight target overshoot on control point 2
        overshoot = self.rng.uniform(1.5, 3.5)
        x2 = x0 + dx * 0.75 + ux * p2_offset + (dx / dist) * overshoot
        y2 = y0 + dy * 0.75 + uy * p2_offset + (dy / dist) * overshoot

        waypoints = []
        tremor_freq = self.rng.uniform(9.0, 11.5)  # Hz
        tremor_phase = self.rng.uniform(0, math.tau)

        for i in range(num_points):
            t_norm = i / float(num_points - 1)  # 0.0 to 1.0

            # Minimum Jerk Polynomial easing: s(t) = 10 t^3 - 15 t^4 + 6 t^5
            u = 10 * (t_norm ** 3) - 15 * (t_norm ** 4) + 6 * (t_norm ** 5)

            # Cubic Bézier evaluation
            bx = ((1 - u) ** 3) * x0 + 3 * ((1 - u) ** 2) * u * x1 + 3 * (1 - u) * (u ** 2) * x2 + (u ** 3) * x3
            by = ((1 - u) ** 3) * y0 + 3 * ((1 - u) ** 2) * u * y1 + 3 * (1 - u) * (u ** 2) * y2 + (u ** 3) * y3

            # Neuromuscular micro-tremor (amplitude drops near target for precision)
            t_sec = (t_norm * duration_ms) / 1000.0
            tremor_amp = math.sin(math.pi * t_norm) * 0.75  # Peak tremor mid-flight
            tremor_val = math.sin(math.tau * tremor_freq * t_sec + tremor_phase) * tremor_amp

            curr_x = bx + ux * tremor_val
            curr_y = by + uy * tremor_val
            curr_t = round(t_norm * duration_ms, 2)

            waypoints.append({
                "x": round(curr_x, 2),
                "y": round(curr_y, 2),
                "t": curr_t
            })

        # Ensure exact destination coordinate on final waypoint
        waypoints[-1]["x"] = round(x3, 2)
        waypoints[-1]["y"] = round(y3, 2)

        return waypoints

    def generate_browser_dispatch_script(self, waypoints: List[Dict[str, Any]], target_selector: str) -> str:
        """
        Generates in-browser async JavaScript to dispatch authentic mouse events
        along the computed waypoints with natural microsecond intervals.
        """
        pts_json = str(waypoints)
        return f"""
        (async () => {{
            const pts = {pts_json};
            const target = document.querySelector("{target_selector}");
            if (!target) return false;

            const rect = target.getBoundingClientRect();
            let lastT = 0;

            for (let i = 0; i < pts.length; i++) {{
                const pt = pts[i];
                const dt = pt.t - lastT;
                if (dt > 0) {{
                    await new Promise(r => setTimeout(r, dt));
                }}
                lastT = pt.t;

                const moveEvt = new PointerEvent("pointermove", {{
                    bubbles: true,
                    cancelable: true,
                    clientX: pt.x,
                    clientY: pt.y,
                    pointerType: "mouse",
                    pressure: 0.0
                }});
                window.dispatchEvent(moveEvt);
            }}

            // Pre-click hover dwell
            await new Promise(r => setTimeout(r, 45));

            // Pointer down
            const lastPt = pts[pts.length - 1];
            target.dispatchEvent(new PointerEvent("pointerdown", {{
                bubbles: true,
                cancelable: true,
                clientX: lastPt.x,
                clientY: lastPt.y,
                pointerType: "mouse",
                pressure: 0.5,
                buttons: 1
            }}));

            // Human click hold dwell (85ms)
            await new Promise(r => setTimeout(r, 85));

            // Pointer up
            target.dispatchEvent(new PointerEvent("pointerup", {{
                bubbles: true,
                cancelable: true,
                clientX: lastPt.x,
                clientY: lastPt.y,
                pointerType: "mouse",
                pressure: 0.0,
                buttons: 0
            }}));

            // Click
            target.dispatchEvent(new MouseEvent("click", {{
                bubbles: true,
                cancelable: true,
                clientX: lastPt.x,
                clientY: lastPt.y
            }}));

            return true;
        }})();
        """
