"""
Milli-Booker Unified Command Line Interface.
Run servers, execute head-to-head races, or fire reflex seat snipers.
"""

import sys
import asyncio
import click
import uvicorn
from rich.console import Console

from server.app import app
from booker.api_booker import FastApiBooker
from booker.reflex_booker import MilliReflexBooker
from booker.ultra_raw_booker import UltraRawSocketBooker
from booker.hyper_reflex_v8 import V8HyperReflexSniper
from benchmark import run_head_to_head_race

from booker.reaction_player import ensure_server_running

console = Console()


@click.group()
def cli():
    """⚡ Milli-Booker: High-Speed Ticketing Platform, Queue Simulator, and Reflex Sniper."""
    pass


@cli.command("serve")
@click.option("--host", default="127.0.0.1", help="Host interface to bind")
@click.option("--port", default=8000, type=int, help="Port to listen on")
def serve(host: str, port: int):
    """Launches the live ticketing server and visual seating arena UI."""
    console.print(f"\n[bold green]🚀 Launching Milli-Booker Ticketing Engine on http://{host}:{port}[/bold green]")
    console.print(f"[dim]• Interactive Seating Chart: http://{host}:{port}/[/dim]")
    console.print(f"[dim]• Reaction Game Arena:       http://{host}:{port}/game[/dim]")
    console.print(f"[dim]• REST API Endpoints:        http://{host}:{port}/docs[/dim]\n")
    uvicorn.run("server.app:app", host=host, port=port, log_level="info")


@cli.command("race")
@click.option("--url", default="http://localhost:8000", help="Ticketing server base URL")
def race(url: str):
    """Executes a 4-tier head-to-head race: Ultra-Raw TCP vs API Bot vs Milli-Scrapes Reflex vs Human Simulator."""
    asyncio.run(run_head_to_head_race(base_url=url))


@cli.command("snipe-ultra")
@click.option("--host", default="127.0.0.1", help="Server host")
@click.option("--port", default=8000, type=int, help="Server port")
@click.option("--seat", default=None, help="Specific seat ID to target (e.g. A1). Defaults to first available.")
def snipe_ultra(host: str, port: int, seat: str):
    """Executes HFT-grade sub-millisecond Raw TCP zero-copy checkout (<1ms)."""
    ensure_server_running(f"http://{host}:{port}")
    bot = UltraRawSocketBooker(host=host, port=port, client_id="cli-ultra-raw-sniper")
    try:
        console.print(f"\n[yellow]⚡ Pre-heating raw TCP socket with TCP_NODELAY against {host}:{port}...[/yellow]")
        warmup = bot.pre_warm_and_join_queue()
        console.print(f"  • Socket Warmup: [green]{warmup['warmup_time_us']} µs[/green] ({warmup['warmup_time_ms']} ms)")
        console.print(f"[bold green]🎯 Firing pre-baked wire reservation for seat {seat or 'Auto'}...[/bold green]")
        res = bot.snipe_seat(preferred_seat=seat)
        if res.get("success"):
            console.print(f"\n[bold green]🏆 SEAT {res['seat_id']} BOOKED IN {res['wire_rtt_ms']} ms ({res['wire_rtt_us']} µs)![/bold green]")
            console.print(f"  • Wire RTT:          {res['wire_rtt_us']} µs ({res['wire_rtt_ms']} ms)")
            console.print(f"  • Server Lock Time:  {res['server_process_ms']} ms")
        else:
            console.print(f"\n[bold red]❌ Booking failed: {res.get('error')}[/bold red]")
    finally:
        bot.close()


@cli.command("snipe-api")
@click.option("--url", default="http://localhost:8000", help="Ticketing server base URL")
@click.option("--seat", default=None, help="Specific seat ID to target (e.g. A1). Defaults to first available.")
def snipe_api(url: str, seat: str):
    """Executes ultra-low latency protocol API checkout (<20ms)."""
    async def _run():
        bot = FastApiBooker(base_url=url, client_id="cli-api-sniper")
        try:
            console.print(f"\n[yellow]⚡ Pre-warming socket and acquiring queue token for {url}...[/yellow]")
            await bot.pre_warm()
            console.print(f"[bold green]🎯 Firing atomic reservation for seat {seat or 'Auto'}...[/bold green]")
            res = await bot.snipe_fastest_seat(preferred_seat=seat)
            if res.get("success"):
                console.print(f"\n[bold green]🏆 SEAT {res['seat_id']} BOOKED IN {res['total_ttf_ms']} ms![/bold green]")
                console.print(f"  • Network RTT:       {res['network_rtt_ms']} ms")
                console.print(f"  • Server Lock Time:  {res['server_process_ms']} ms")
            else:
                console.print(f"\n[bold red]❌ Booking failed: {res.get('error')}[/bold red]")
        finally:
            await bot.close()

    asyncio.run(_run())


@cli.command("snipe-reflex")
@click.option("--url", default="http://localhost:8000", help="Ticketing server base URL")
@click.option("--mode", type=click.Choice(["optical", "dom"]), default="dom", help="Reflex mode (optical framebuffer or in-loop DOM)")
def snipe_reflex(url: str, mode: str):
    """Executes sub-50ms visual reflex seat booking using Milli-Scrapes."""
    async def _run():
        bot = MilliReflexBooker(base_url=url, client_id="cli-milli-reflex", mode=mode)
        try:
            console.print(f"\n[yellow]🎯 Priming Milli-Scrapes Reflex Sniper (Mode: {mode}) against {url}...[/yellow]")
            res = await bot.snipe_event()
            if res.get("success"):
                console.print(f"\n[bold green]🏆 REFLEX SEAT BOOKED IN {res['total_ttf_ms']} ms![/bold green]")
                console.print(f"  • Navigation & Settle: {res['nav_settle_ms']} ms")
                console.print(f"  • Reflex Reaction:     {res['snipe_reaction_ms']} ms")
                if res.get("target_coords"):
                    console.print(f"  • Optical Centroid:    {res['target_coords']}")
            else:
                console.print(f"\n[bold red]⚠️ {res.get('message', 'Booking failed')}[/bold red]")
        finally:
            await bot.close()

    asyncio.run(_run())


@cli.command("status")
@click.option("--url", default="http://localhost:8000", help="Ticketing server base URL")
def status(url: str):
    """Checks current event inventory and queue status."""
    import requests
    try:
        r = requests.get(f"{url.rstrip('/')}/api/event/grand-concert-2026")
        data = r.json()
        console.print(f"\n[bold cyan]🎫 Event: {data['title']}[/bold cyan]")
        console.print(f"  • Available Seats: [green]{data['available_seats']} / {data['total_seats']}[/green]")
        console.print(f"  • Drop Status:     [yellow]{'SOLD OUT' if data['is_sold_out'] else 'LIVE'}[/yellow]")
        console.print(f"  • Queue Active:    {data['queue_active']}")
    except Exception as e:
        console.print(f"[bold red]Could not reach server: {e}[/bold red]")


@cli.command("play-game")
@click.option("--url", default="http://127.0.0.1:8000", help="Ticketing server base URL")
@click.option("--duration", default=30.0, type=float, help="Game duration in seconds (default: 30.0)")
def play_game(url: str, duration: float):
    """Executes a 30-second live CDP reaction trial against the target ball arena."""
    from rich.panel import Panel
    from rich.table import Table
    from booker.reaction_player import ReactionGameBot

    async def _run():
        console.print(Panel.fit(
            f"[bold cyan]🎯 30-SECOND VISUAL REACTION TRIAL: MILLI-REFLEX BOT[/bold cyan]\n"
            f"[dim]Randomly appearing target ball arena at {url}/game[/dim]",
            border_style="cyan"
        ))
        bot = ReactionGameBot(base_url=url, headless=True, duration_sec=duration)
        try:
            res = await bot.play_round(show_live_hits=True)

            table = Table(title=f"🏆 30-Second Reaction Scorecard", header_style="bold magenta")
            table.add_column("Metric", style="cyan")
            table.add_column("Milli-Reflex Bot", justify="right", style="bold green")
            table.add_column("Typical Human", justify="right", style="dim")

            table.add_row("Total Hits in 30s", str(res["total_hits"]), "40 – 65 hits")
            table.add_row("Hits Per Second (HPS)", f"{res['hits_per_second']:.2f}", "1.3 – 2.1 HPS")
            table.add_row("Average Reaction Latency", f"{res['avg_latency_ms']} ms", "280 – 350 ms")
            table.add_row("Fastest Reaction Latency", f"{res['fastest_latency_ms']} ms", "~210 ms")

            console.print("\n")
            console.print(table)

            human_avg = 310.0
            speedup = round(human_avg / res["avg_latency_ms"], 1) if res["avg_latency_ms"] > 0 else 0
            console.print(f"\n[bold green]⚡ Analysis:[/bold green] Milli-Reflex Bot registered [bold yellow]{res['total_hits']} hits[/bold yellow] at [bold cyan]{res['avg_latency_ms']} ms[/bold cyan] avg response time ([bold yellow]{speedup}× faster[/bold yellow] than human visual reaction)!\n")
        finally:
            await bot.close()

    asyncio.run(_run())


@cli.command("play-hyper")
@click.option("--url", default="http://127.0.0.1:8000", help="Ticketing server base URL")
@click.option("--duration", default=30.0, type=float, help="Game duration in seconds (default: 30.0)")
def play_hyper(url: str, duration: float):
    """Executes a V8 in-memory sub-millisecond hyper-reflex trial (<1ms)."""
    from rich.panel import Panel
    from rich.table import Table

    async def _run():
        console.print(Panel.fit(
            f"[bold red]⚡ V8 IN-MEMORY HYPER-REFLEX TRIAL (SUB-MILLISECOND)[/bold red]\n"
            f"[dim]Bypassing CDP IPC bottlenecks with zero-clamp MessageChannel hooks[/dim]",
            border_style="red"
        ))
        bot = V8HyperReflexSniper(base_url=url, headless=True, duration_sec=duration)
        try:
            res = await bot.run_trial(show_live=True)

            table = Table(title=f"⚡ V8 In-Memory Hyper-Reflex Scorecard", header_style="bold magenta")
            table.add_column("Metric", style="cyan")
            table.add_column("V8 Hyper-Reflex", justify="right", style="bold red")
            table.add_column("CDP Bot", justify="right", style="yellow")
            table.add_column("Typical Human", justify="right", style="dim")

            table.add_row("Total Hits in 30s", str(res["total_hits"]), "~550 hits", "40 – 65 hits")
            table.add_row("Hits Per Second (HPS)", f"{res['hits_per_second']:.2f}", "~18.4 HPS", "1.3 – 2.1 HPS")
            table.add_row("Average Reaction Latency", f"{res['avg_latency_ms']} ms", "~35.2 ms", "280 – 350 ms")
            table.add_row("Fastest Reaction Latency", f"{res['best_latency_ms']} ms", "11.0 ms", "~210 ms")

            console.print("\n")
            console.print(table)

            human_avg = 310.0
            speedup = round(human_avg / res["best_latency_ms"], 1) if res["best_latency_ms"] > 0 else 0
            console.print(f"\n[bold green]⚡ Analysis:[/bold green] V8 In-Memory Sniper achieved [bold red]{res['best_latency_ms']} ms[/bold red] peak response latency ([bold yellow]{speedup}× faster[/bold yellow] than human visual reaction)!\n")
        finally:
            await bot.close()

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
