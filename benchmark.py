"""
Head-to-Head Benchmark Arena:
Ultra-Raw TCP Socket vs Protocol API Bot vs Milli-Scrapes Reflex vs Human Consumer.
Demonstrates latency divergence, race condition handling, and sub-millisecond execution.
"""

import time
import asyncio
from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from server.inventory import SeatInventory
from server.queue_manager import QueueManager
from booker.ultra_raw_booker import UltraRawSocketBooker
from booker.api_booker import FastApiBooker
from booker.reflex_booker import MilliReflexBooker
from booker.human_simulator import HumanBrowserSimulator
from booker.reaction_player import ensure_server_running

console = Console()


async def run_head_to_head_race(base_url: str = "http://localhost:8000", event_id: str = "grand-concert-2026"):
    """
    Executes a 4-tier head-to-head drop competition across disparate architectures:
    1. Ultra-Raw Zero-Copy TCP Socket Booker (Sub-millisecond wire execution)
    2. Pre-warmed Protocol API Booker (aiohttp persistent pooling)
    3. Milli-Scrapes Reflex Optical/DOM Booker (Browser CDP in-loop)
    4. Human Browser Simulator (Full DOM perception + cognitive hesitation)
    """
    ensure_server_running(base_url)
    console.print(Panel.fit(
        "[bold cyan]⚡ MILLI-BOOKER 4-TIER ULTIMATE SPEED SHOWDOWN ⚡[/bold cyan]\n"
        "[dim]Simulating high-demand ticket drop competition across disparate architectures[/dim]",
        border_style="cyan"
    ))

    # Clients
    raw_bot = UltraRawSocketBooker(host="127.0.0.1", port=8000, client_id="hft-ultra-raw-01")
    api_bot = FastApiBooker(base_url=base_url, client_id="bot-protocol-alpha")
    milli_bot = MilliReflexBooker(base_url=base_url, client_id="bot-milli-reflex", mode="dom")
    human = HumanBrowserSimulator(base_url=base_url, client_id="human-consumer-jane")

    try:
        # Pre-warm phase
        console.print("\n[yellow]⏳ Phase 1: Pre-Warming & Connection Pooling...[/yellow]")
        raw_warmup = raw_bot.pre_warm_and_join_queue()
        console.print(f"  • Raw TCP Socket (TCP_NODELAY): [bold green]Active[/bold green] ({raw_warmup.get('warmup_time_us')} µs)")

        warmup = await api_bot.pre_warm(event_id=event_id)
        console.print(f"  • API Bot TCP socket pre-warmed: [green]Active[/green] (RTT: {warmup.get('rtt_ms')} ms)")
        console.print(f"  • Queue pass tokens pre-acquired: [green]True[/green]")

        console.print("\n[bold red]🚨 Phase 2: THE DROP IS LIVE! Firing all clients simultaneously...[/bold red]\n")

        # Function to run synchronous raw socket in thread pool
        loop = asyncio.get_running_loop()
        raw_task = loop.run_in_executor(None, raw_bot.snipe_seat, event_id)

        # Launch all 4 concurrently
        results = await asyncio.gather(
            raw_task,
            api_bot.snipe_fastest_seat(event_id=event_id),
            milli_bot.snipe_event(event_id=event_id),
            human.simulate_human_checkout(event_id=event_id),
            return_exceptions=True
        )

        res_raw, res_api, res_milli, res_human = results

        # Process results
        table = Table(title="🏆 Head-to-Head Drop Results", header_style="bold magenta")
        table.add_column("Rank", justify="center", style="bold")
        table.add_column("Competitor", style="cyan")
        table.add_column("Architecture", style="dim")
        table.add_column("Outcome", justify="center")
        table.add_column("Seat Claimed", justify="center", style="bold yellow")
        table.add_column("Total Latency (ms)", justify="right", style="bold green")
        table.add_column("Reaction Latency", justify="right")

        # Compile rows
        runs = []

        if isinstance(res_raw, dict):
            runs.append({
                "name": "Ultra-Raw TCP Booker",
                "arch": "Zero-Copy TCP Wire Frames",
                "success": res_raw.get("success", False),
                "seat": res_raw.get("seat_id", "None"),
                "total_ms": res_raw.get("total_ttf_ms", 9999.0),
                "react_ms": f"{res_raw.get('wire_rtt_us', 0)} µs wire"
            })
        else:
            runs.append({"name": "Ultra-Raw TCP Booker", "arch": "Raw TCP", "success": False, "seat": "None", "total_ms": 9999, "react_ms": "Error"})

        if isinstance(res_api, dict):
            runs.append({
                "name": "Protocol API Bot",
                "arch": "Persistent JSON / aiohttp",
                "success": res_api.get("success", False),
                "seat": res_api.get("seat_id", "None"),
                "total_ms": res_api.get("total_ttf_ms", 9999.0),
                "react_ms": f"{res_api.get('network_rtt_ms', 0)} ms RTT"
            })
        else:
            runs.append({"name": "Protocol API Bot", "arch": "Raw JSON", "success": False, "seat": "None", "total_ms": 9999, "react_ms": "Error"})

        if isinstance(res_milli, dict):
            runs.append({
                "name": "Milli-Scrapes Reflex",
                "arch": "In-Loop CDP / Optical Centroid",
                "success": res_milli.get("success", False),
                "seat": "Auto-Acquired",
                "total_ms": res_milli.get("total_ttf_ms", 9999.0),
                "react_ms": f"{res_milli.get('snipe_reaction_ms', 0)} ms reflex"
            })
        else:
            runs.append({"name": "Milli-Scrapes Reflex", "arch": "CDP / Optical", "success": False, "seat": "None", "total_ms": 9999, "react_ms": "Error"})

        if isinstance(res_human, dict):
            runs.append({
                "name": "Human Consumer",
                "arch": "Full DOM / Cognitive Perception",
                "success": res_human.get("success", False),
                "seat": res_human.get("seat_id", "None"),
                "total_ms": res_human.get("total_ttf_ms", 9999.0),
                "react_ms": f"{res_human.get('human_reaction_ms', 0)} ms delay"
            })
        else:
            runs.append({"name": "Human Consumer", "arch": "Human Browser", "success": False, "seat": "None", "total_ms": 9999, "react_ms": "Error"})

        # Sort by total_ms
        runs.sort(key=lambda x: x["total_ms"])

        medals = ["🥇 1st", "🥈 2nd", "🥉 3rd", "4th"]
        for idx, r in enumerate(runs):
            status = "[bold green]BOOKED[/bold green]" if r["success"] else "[bold red]OUTPACED[/bold red]"
            table.add_row(
                medals[idx] if idx < len(medals) else f"{idx+1}th",
                r["name"],
                r["arch"],
                status,
                r["seat"],
                f"{r['total_ms']} ms",
                r["react_ms"]
            )

        console.print(table)

        # Speed differential analysis
        winner = runs[0]
        human_run = next(r for r in runs if r["name"] == "Human Consumer")
        if human_run["total_ms"] > 0 and winner["total_ms"] > 0:
            speedup = round(human_run["total_ms"] / winner["total_ms"], 1)
            console.print(f"\n[bold green]⚡ Analysis:[/bold green] [cyan]{winner['name']}[/cyan] beat the human consumer by [bold yellow]{speedup}×[/bold yellow] ({human_run['total_ms']} ms vs {winner['total_ms']} ms)!\n")

    finally:
        raw_bot.close()
        await api_bot.close()
        await milli_bot.close()


if __name__ == "__main__":
    asyncio.run(run_head_to_head_race())
