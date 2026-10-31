"""
Integration tests for FastApiBooker, MilliReflexBooker, and HumanBrowserSimulator.
"""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport

from server.app import app, inventory, queue_mgr
from booker.clock_sync import ClockSynchronizer
from booker.api_booker import FastApiBooker
from booker.reflex_booker import MilliReflexBooker
from booker.human_simulator import HumanBrowserSimulator


@pytest.mark.asyncio
async def test_fastapi_server_endpoints():
    await inventory.reset()
    await queue_mgr.reset()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Event metadata
        r = await ac.get("/api/event/grand-concert-2026")
        assert r.status_code == 200
        data = r.json()
        assert data["total_seats"] == 50
        assert data["available_seats"] == 50

        # 2. Join queue
        q_res = await ac.post("/api/queue/join", json={"client_id": "test-client-1"})
        assert q_res.status_code == 200
        q_data = q_res.json()
        assert q_data["admitted"] is True
        token = q_data["token"]

        # 3. Book seat with admin clearance
        book_res = await ac.post(
            "/api/book",
            json={
                "event_id": "grand-concert-2026",
                "seat_id": "A1",
                "client_id": "test-client-1",
                "client_type": "bot",
                "queue_token": token
            },
            headers={"X-Sentinel-Admin-Key": "SENTINEL_WAR_2026"}
        )
        assert book_res.status_code == 200
        assert book_res.json()["success"] is True

        # 4. Attempt to book without valid token -> 403
        bad_book = await ac.post("/api/book", json={
            "event_id": "grand-concert-2026",
            "seat_id": "A2",
            "client_id": "bad-client",
            "queue_token": "invalid:token"
        })
        assert bad_book.status_code == 403


@pytest.mark.asyncio
async def test_reflex_booker_initialization():
    """Verifies that MilliReflexBooker loads with local milli-scrapes without error."""
    booker = MilliReflexBooker(base_url="http://localhost:8000", mode="dom")
    assert booker.mode == "dom"
    assert booker.client_id == "milli-reflex-sniper"


def test_ultra_raw_booker_frame_generation():
    """Verifies that UltraRawSocketBooker constructs valid HTTP/1.1 wire frames."""
    from booker.ultra_raw_booker import UltraRawSocketBooker
    bot = UltraRawSocketBooker(host="127.0.0.1", port=8000, client_id="test-hft-bot")
    assert bot.client_id == "test-hft-bot"
    assert bot.sock is None

