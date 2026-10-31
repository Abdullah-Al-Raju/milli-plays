"""
Milli-Reflex 30-Second Reaction Game Auto-Player.
Streams in-loop CDP events to detect and click target balls in milliseconds over 30 seconds.
"""

import time
import asyncio
import threading
from typing import Dict, Any, List, Optional
import requests
from rich.console import Console
from rich.table import Table

from milli_agent.browser.engine import MilliBrowserEngine
from server.app import app

console = Console()


def ensure_server_running(base_url: str = "http://127.0.0.1:8000"):
    """Guarantees the ticketing & reaction server is active in background daemon thread."""
    try:
        requests.get(f"{base_url.rstrip('/')}/api/game/leaderboard", timeout=0.3)
    except Exception:
        import uvicorn
        def _run():
            config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="error")
            server = uvicorn.Server(config)
            server.run()
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        time.sleep(1.0)


class ReactionGameBot:
    """
    Automated visual reflex player for the 30-second target ball reaction arena.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        headless: bool = True,
        duration_sec: float = 30.0
    ):
        self.base_url = base_url.rstrip("/")
        self.headless = headless
        self.duration_sec = duration_sec
        self.engine: Optional[MilliBrowserEngine] = None

    async def init(self):
        """Launches browser engine and ensures server is live."""
        ensure_server_running(self.base_url)
        if self.engine is None:
            self.engine = MilliBrowserEngine(headless=self.headless, window_size=(1366, 900))
            await self.engine.start()

    async def play_round(self, show_live_hits: bool = True) -> Dict[str, Any]:
        """
        Navigates to /game, triggers the 30-second round, and fires reflex clicks
        at each newly spawned target ball as fast as possible.
        """
        await self.init()
        url = f"{self.base_url}/game"

        console.print(f"\n[cyan]🌐 Navigating to Reaction Arena at {url}...[/cyan]")
        await self.engine.cy_navigate(url)
        await self.engine.wait_until_idle(timeout=2.0)

        console.print(f"[bold yellow]⚡ Armed & Ready! Initiating {self.duration_sec:.1f}-second reaction trial...[/bold yellow]\n")

        # Start game via in-loop script
        await self.engine.cy_evaluate("window.__START_GAME__()")

        t_round_start = time.perf_counter()
        latencies = []
        hits_dispatched = 0

        # High-frequency in-loop striking
        while (time.perf_counter() - t_round_start) < (self.duration_sec + 0.3):
            t_scan = time.perf_counter()

            # Target position query (< 0.2 ms)
            info = await self.engine.cy_evaluate("""
                (() => {
                    const ball = document.getElementById("target-ball");
                    if (!ball || ball.style.display === "none") return null;
                    const r = ball.getBoundingClientRect();
                    return {
                        x: r.left + r.width / 2,
                        y: r.top + r.height / 2,
                        score: typeof score !== 'undefined' ? score : 0,
                        timeRemaining: typeof timeRemaining !== 'undefined' ? timeRemaining : 0
                    };
                })()
            """)

            if not info or info.get("timeRemaining", 1.0) <= 0.0:
                if (time.perf_counter() - t_round_start) >= self.duration_sec:
                    break
                await asyncio.sleep(0.005)
                continue

            target_x = info["x"]
            target_y = info["y"]

            # Strike the target immediately
            t_click0 = time.perf_counter()
            await self.engine.cy_click((target_x, target_y))
            reaction_ms = (time.perf_counter() - t_scan) * 1000.0
            latencies.append(reaction_ms)
            hits_dispatched += 1

            if show_live_hits and (hits_dispatched % 50 == 0 or hits_dispatched in [1, 5, 25]):
                elapsed = time.perf_counter() - t_round_start
                console.print(
                    f"  🎯 [green]Hit #{hits_dispatched:03d}[/green] | "
                    f"Reaction: [bold cyan]{reaction_ms:5.1f} ms[/bold cyan] | "
                    f"Pace: [bold yellow]{hits_dispatched / elapsed:4.1f} HPS[/bold yellow] | "
                    f"Timer: [dim]{max(0.0, self.duration_sec - elapsed):4.1f}s[/dim]"
                )

            await asyncio.sleep(0.005)

        # Retrieve verified scorecard from client DOM
        scorecard = await self.engine.cy_evaluate("""
            (() => {
                return {
                    total_hits: typeof score !== 'undefined' ? score : 0,
                    hps: typeof score !== 'undefined' ? (score / 30.0).toFixed(2) : 0,
                    latencies: typeof reactionTimes !== 'undefined' ? reactionTimes : []
                };
            })()
        """)

        total_hits = scorecard.get("total_hits", hits_dispatched)
        all_lats = scorecard.get("latencies", latencies)
        avg_ms = round(sum(all_lats) / len(all_lats), 1) if all_lats else 0.0
        best_ms = round(min(all_lats), 1) if all_lats else 0.0
        hps = round(total_hits / self.duration_sec, 2)

        return {
            "total_hits": total_hits,
            "duration_sec": self.duration_sec,
            "hits_per_second": hps,
            "avg_latency_ms": avg_ms,
            "fastest_latency_ms": best_ms,
            "latencies": all_lats
        }

    async def close(self):
        """Closes browser session."""
        if self.engine:
            await self.engine.aclose()
            self.engine = None
