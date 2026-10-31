"""
V8 In-Memory Hyper-Reflex Sniper Engine.
Injects zero-clamp microsecond observer harness directly into the Chromium V8 JavaScript runtime.
Obliterates Chrome DevTools Protocol (CDP) WebSocket roundtrip bottlenecks to achieve
sub-millisecond (< 1.0 ms) visual reaction speeds.
"""

import time
import asyncio
from typing import Dict, Any, Optional
import requests
from rich.console import Console
from rich.table import Table

from milli_agent.browser.engine import MilliBrowserEngine
from .reaction_player import ensure_server_running

console = Console()


class V8HyperReflexSniper:
    """
    Sub-millisecond visual reflex bot that runs natively in Chromium V8 memory.
    Bypasses CDP IPC serialization overhead using MessageChannel zero-clamp macro-tasks.
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
        """Initializes browser engine and verifies server."""
        ensure_server_running(self.base_url)
        if self.engine is None:
            self.engine = MilliBrowserEngine(headless=self.headless, window_size=(1366, 900))
            await self.engine.start()

    async def arm_v8_sniper(self) -> bool:
        """
        Injects the zero-latency MessageChannel mutation listener directly into V8.
        When targetBall appears, it fires pointerdown immediately with 0ms clamping.
        """
        script = """
        (() => {
            const ball = document.getElementById("target-ball");
            if (!ball) return false;

            // Clean up existing observer if any
            if (window.__HYPER_SNIPER_OBSERVER__) {
                window.__HYPER_SNIPER_OBSERVER__.disconnect();
            }

            // MessageChannel provides true zero-delay macro-task execution
            // avoiding HTML5 setTimeout 4ms nested clamping
            const channel = new MessageChannel();
            channel.port1.onmessage = () => {
                if (ball.style.display === "none") return;
                const r = ball.getBoundingClientRect();
                const evt = new PointerEvent("pointerdown", {
                    bubbles: true,
                    cancelable: true,
                    clientX: r.left + r.width / 2,
                    clientY: r.top + r.height / 2
                });
                ball.dispatchEvent(evt);
            };

            const observer = new MutationObserver((mutations) => {
                for (const m of mutations) {
                    if (m.attributeName === "style" && ball.style.display !== "none") {
                        // Immediately schedule zero-delay macro-task
                        channel.port2.postMessage(null);
                        break;
                    }
                }
            });

            observer.observe(ball, { attributes: true, attributeFilter: ["style"] });
            window.__HYPER_SNIPER_OBSERVER__ = observer;
            window.__HYPER_SNIPER_ARMED__ = true;
            return true;
        })()
        """
        res = await self.engine.cy_evaluate(script)
        return bool(res)

    async def run_trial(self, show_live: bool = True) -> Dict[str, Any]:
        """
        Runs the hyper-reflex trial and streams microsecond telemetry.
        """
        await self.init()
        url = f"{self.base_url}/game"

        console.print(f"\n[cyan]🌐 Connecting to Reaction Arena at {url}...[/cyan]")
        await self.engine.cy_navigate(url)
        await self.engine.wait_until_idle(timeout=2.0)

        # Arm the in-memory engine
        armed = await self.arm_v8_sniper()
        if not armed:
            raise RuntimeError("Failed to arm in-memory V8 reflex sniper")

        console.print("[bold red]⚡ [V8 IN-MEMORY HYPER-REFLEX SNIPER ARMED][/bold red]")
        console.print("[dim]→ Mechanism: Zero-clamp MessageChannel + V8 Mutation Observer[/dim]")
        console.print(f"[bold yellow]🚀 Initiating {self.duration_sec:.1f}-second trial at maximum silicon speed...[/bold yellow]\n")

        # Start game asynchronously
        await self.engine.cy_evaluate("setTimeout(() => window.__START_GAME__(), 10)")

        t_start = time.perf_counter()
        last_reported_hits = 0

        while (time.perf_counter() - t_start) < (self.duration_sec + 0.5):
            await asyncio.sleep(1.0)
            elapsed = time.perf_counter() - t_start

            # Read live stats from client DOM
            stats = await self.engine.cy_evaluate("""
            (() => {
                const lats = typeof reactionTimes !== 'undefined' ? reactionTimes : [];
                return {
                    hits: typeof score !== 'undefined' ? score : 0,
                    remaining: typeof timeRemaining !== 'undefined' ? timeRemaining : 0,
                    avg: lats.length ? (lats.reduce((a, b) => a + b, 0) / lats.length).toFixed(2) : "0",
                    best: lats.length ? Math.min(...lats).toFixed(2) : "0",
                    last: lats.length ? lats[lats.length - 1].toFixed(2) : "0"
                };
            })()
            """)

            hits = stats.get("hits", 0)
            avg_ms = stats.get("avg", "0")
            best_ms = stats.get("best", "0")
            last_ms = stats.get("last", "0")
            hps = (hits / elapsed) if elapsed > 0 else 0

            if show_live:
                console.print(
                    f"  ⚡ [bold green]Hits: {hits:4d}[/bold green] | "
                    f"Pace: [bold yellow]{hps:5.1f} HPS[/bold yellow] | "
                    f"Last: [cyan]{last_ms:5s} ms[/cyan] | "
                    f"Avg: [bold magenta]{avg_ms:5s} ms[/bold magenta] | "
                    f"Best: [bold red]{best_ms:5s} ms[/bold red] | "
                    f"Remaining: [dim]{max(0.0, self.duration_sec - elapsed):4.1f}s[/dim]"
                )

            if stats.get("remaining", 1.0) <= 0.0 and elapsed > 2.0:
                break

        # Final scorecard
        final_card = await self.engine.cy_evaluate("""
        (() => {
            const lats = typeof reactionTimes !== 'undefined' ? reactionTimes : [];
            return {
                total_hits: typeof score !== 'undefined' ? score : 0,
                duration: typeof gameDuration !== 'undefined' ? gameDuration : 30,
                latencies: lats
            };
        })()
        """)

        total_hits = final_card.get("total_hits", 0)
        lats = final_card.get("latencies", [])
        avg_ms = round(sum(lats) / len(lats), 2) if lats else 0.0
        best_ms = round(min(lats), 2) if lats else 0.0
        hps = round(total_hits / self.duration_sec, 2)

        return {
            "mode": "V8 In-Memory Hyper-Reflex",
            "total_hits": total_hits,
            "duration_sec": self.duration_sec,
            "hits_per_second": hps,
            "avg_latency_ms": avg_ms,
            "best_latency_ms": best_ms,
            "latencies": lats
        }

    async def close(self):
        """Closes browser session."""
        if self.engine:
            await self.engine.aclose()
            self.engine = None
