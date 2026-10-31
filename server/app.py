"""
FastAPI Ticketing Platform and High-Concurrency Queue Server.
Provides REST APIs for event discovery, virtual waiting room, and sub-millisecond atomic booking.
"""

import time
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .inventory import SeatInventory
from .queue_manager import QueueManager
from .anti_bot import fortress_instance

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Milli-Booker Ticketing Engine",
    description="High-Throughput Seat Reservation Platform & Anti-Bot Defense Simulator",
    version="1.0.0"
)

# Static & Templates setup
static_dir = BASE_DIR / "static"
templates_dir = BASE_DIR / "templates"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

inventory = SeatInventory(event_id="grand-concert-2026", total_seats=50, rows=5, cols=10)
queue_mgr = QueueManager(admission_rate_per_sec=10)


class QueueJoinRequest(BaseModel):
    client_id: str


class BookingRequest(BaseModel):
    event_id: str = "grand-concert-2026"
    seat_id: str
    client_id: str
    client_type: str = "bot"
    queue_token: Optional[str] = None


game_leaderboard = []


class GameResultRequest(BaseModel):
    total_hits: int
    hps: float
    avg_latency_ms: float
    best_latency_ms: float
    duration_sec: float = 30.0
    player_type: str = "player"


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the interactive visual seating chart & arena page."""
    html_path = templates_dir / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/game", response_class=HTMLResponse)
async def serve_game():
    """Serves the 30-second visual reaction arena game."""
    game_path = templates_dir / "game.html"
    return HTMLResponse(content=game_path.read_text(encoding="utf-8"))


@app.get("/gauntlet", response_class=HTMLResponse)
async def serve_gauntlet():
    """Serves the 5-minute precision human gauntlet (vector circuit drawing, waveform signature, speed writing)."""
    gauntlet_path = templates_dir / "gauntlet.html"
    return HTMLResponse(content=gauntlet_path.read_text(encoding="utf-8"))


@app.get("/clicker", response_class=HTMLResponse)
async def serve_clicker():
    """Serves the 20-second ultra-fast response endurance clicker arena."""
    clicker_path = templates_dir / "clicker.html"
    return HTMLResponse(content=clicker_path.read_text(encoding="utf-8"))


@app.get("/challenge", response_class=HTMLResponse)
async def serve_challenge():
    """Serves the Cloudflare Turnstile & Sentinel Challenge Interstitial."""
    challenge_path = templates_dir / "challenge.html"
    return HTMLResponse(content=challenge_path.read_text(encoding="utf-8"))


@app.get("/sentinel", response_class=HTMLResponse)
async def serve_sentinel():
    """Serves the Sentinel Fortress live visual threat radar dashboard."""
    sentinel_path = templates_dir / "sentinel.html"
    return HTMLResponse(content=sentinel_path.read_text(encoding="utf-8"))


class ChallengeVerifyRequest(BaseModel):
    pow_token: str
    pow_nonce: int
    telemetry: Optional[Dict[str, Any]] = None
    trajectory: Optional[List[Dict[str, Any]]] = None
    events: Optional[List[Dict[str, Any]]] = None



@app.post("/api/game/start")
async def start_game():
    """Signals start of a 30-second reaction test session."""
    return {"status": "started", "timestamp": time.time(), "duration_sec": 30.0}


@app.post("/api/game/end")
async def end_game(result: GameResultRequest):
    """Records final scorecard metrics for reaction round."""
    entry = {
        "timestamp": time.time(),
        "total_hits": result.total_hits,
        "hps": result.hps,
        "avg_latency_ms": result.avg_latency_ms,
        "best_latency_ms": result.best_latency_ms,
        "duration_sec": result.duration_sec,
        "player_type": result.player_type
    }
    game_leaderboard.append(entry)
    return {"success": True, "entry": entry, "rank": len(game_leaderboard)}


@app.get("/api/game/leaderboard")
async def get_game_leaderboard():
    """Returns top scores recorded during this server session."""
    sorted_scores = sorted(game_leaderboard, key=lambda x: x["total_hits"], reverse=True)
    return {"total_games": len(game_leaderboard), "leaderboard": sorted_scores[:10]}


@app.get("/api/event/{event_id}")
async def get_event_details(event_id: str):
    """
    Returns event metadata with precise server timestamp for clock drift calculation.
    """
    now = time.time()
    seats = await inventory.get_seats_snapshot()
    available = sum(1 for s in seats if s["status"] == "available")

    return {
        "event_id": event_id,
        "title": "Grand Arena World Tour 2026",
        "server_time": now,
        "server_time_ms": int(now * 1000),
        "total_seats": len(seats),
        "available_seats": available,
        "is_sold_out": available == 0,
        "queue_active": queue_mgr.is_queue_active
    }


@app.get("/api/seats/{event_id}")
async def get_seats(event_id: str):
    """Returns real-time seat inventory array."""
    seats = await inventory.get_seats_snapshot()
    return {
        "event_id": event_id,
        "timestamp": time.time(),
        "total": len(seats),
        "seats": seats
    }


@app.post("/api/queue/join")
async def join_queue(req: QueueJoinRequest):
    """Joins the virtual waiting room."""
    res = await queue_mgr.join_queue(req.client_id)
    return res


@app.get("/api/queue/status/{queue_id}")
async def check_queue_status(queue_id: str):
    """Polls queue position and retrieves checkout pass token."""
    res = await queue_mgr.check_status(queue_id)
    if "error" in res:
        raise HTTPException(status_code=res.get("status_code", 404), detail=res["error"])
    return res


@app.get("/api/challenge/issue")
async def issue_challenge():
    """Issues dynamic Proof-of-Work puzzle token."""
    return fortress_instance.pow.generate_challenge("cf-client", difficulty=4)


@app.post("/api/challenge/verify")
async def verify_challenge(req: ChallengeVerifyRequest, request: Request):
    """Evaluates multi-layer bot classification and issues signed clearance cookie."""
    raw_headers = request.scope.get("headers", [])
    auth_key = request.headers.get("X-Sentinel-Admin-Key") or request.cookies.get("sentinel_admin_key")
    res = fortress_instance.evaluate_request(
        raw_headers=raw_headers,
        telemetry=req.telemetry,
        trajectory=req.trajectory,
        pow_token=req.pow_token,
        pow_nonce=req.pow_nonce,
        auth_key=auth_key
    )
    return {
        "success": res["decision"] == "ALLOW",
        "decision": res["decision"],
        "bot_probability": res["bot_probability"],
        "clearance_token": res["clearance_token"],
        "unconditional_access": res.get("unconditional_access", False),
        "anomalies": res["details"].get("anomalies", []),
        "latency_us": res["details"].get("latency_us", 0)
    }


@app.get("/api/sentinel/telemetry")
async def get_sentinel_telemetry():
    """Returns live Sentinel WAF audit log stream."""
    return {
        "enabled": fortress_instance.enabled,
        "logs": fortress_instance.audit_log[-50:]
    }


@app.post("/api/admin/sentinel/toggle")
async def toggle_sentinel():
    """Toggles Sentinel WAF enforcement on/off."""
    fortress_instance.enabled = not fortress_instance.enabled
    return {"sentinel_enabled": fortress_instance.enabled}


@app.post("/api/book")
async def book_seat(req: BookingRequest, request: Request):
    """
    Executes atomic seat reservation.
    Enforces Sentinel Fortress WAF clearance and queue token verification.
    """
    t_start = time.perf_counter()

    # 1. Sentinel Fortress WAF Enforcement
    if fortress_instance.enabled:
        auth_key = request.headers.get("X-Sentinel-Admin-Key") or request.cookies.get("sentinel_admin_key")
        clearance_token = request.headers.get("X-Sentinel-Clearance") or request.cookies.get("sentinel_clearance")
        is_admin = fortress_instance.check_unconditional_admin(auth_key, auth_key)
        if not is_admin:
            if not clearance_token or not fortress_instance.verify_clearance_token(clearance_token):
                l1_check = fortress_instance.ja4.evaluate_headers(request.scope.get("headers", []))
                fortress_instance._record_audit({
                    "timestamp": time.time(),
                    "action": "BLOCK",
                    "bot_score": 1.0,
                    "latency_us": round((time.perf_counter() - t_start) * 1000000.0, 1),
                    "anomalies": ["Missing/invalid sentinel_clearance token. Complete the challenge at /challenge."] + l1_check.get("reasons", [])
                })
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sentinel Fortress WAF Block: Missing or invalid sentinel_clearance token. Complete the challenge at /challenge."
                )

    # 2. Enforce Queue Token verification
    if queue_mgr.is_queue_active:
        if not req.queue_token or not queue_mgr.verify_token(req.queue_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or expired queue token. You must wait in the virtual queue."
            )

    # 3. Atomic reservation
    res = await inventory.reserve_seat(
        seat_id=req.seat_id,
        client_id=req.client_id,
        client_type=req.client_type
    )

    t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
    res["server_process_ms"] = round(t_elapsed_ms, 3)

    if not res.get("success"):
        raise HTTPException(
            status_code=res.get("status_code", 409),
            detail=res.get("error", "Failed to reserve seat")
        )

    return res


@app.get("/api/telemetry")
async def get_telemetry():
    """Returns telemetry data and leaderboards for latency benchmarking."""
    seats = await inventory.get_seats_snapshot()
    booked = [s for s in seats if s["status"] == "booked"]

    return {
        "total_seats": len(seats),
        "booked_count": len(booked),
        "remaining_count": len(seats) - len(booked),
        "logs": inventory.booking_log,
        "recent_bookings": inventory.booking_log[-20:]
    }


@app.post("/api/admin/reset")
async def reset_arena():
    """Resets all seats and waiting queues."""
    await inventory.reset()
    await queue_mgr.reset()
    return {"success": True, "message": "Arena and queue successfully reset"}


@app.post("/api/admin/queue/toggle")
async def toggle_queue():
    """Toggles queue enforcement on/off."""
    queue_mgr.is_queue_active = not queue_mgr.is_queue_active
    return {"queue_active": queue_mgr.is_queue_active}
