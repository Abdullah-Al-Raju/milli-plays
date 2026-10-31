"""
Ultra-Low Latency Protocol API Booker.
Leverages persistent TCP connection pre-warming, socket reuse, and sub-20ms atomic checkout.
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
import aiohttp

from .clock_sync import ClockSynchronizer


class FastApiBooker:
    """
    Protocol-level high-speed booking client.
    Bypasses DOM rendering entirely to dispatch raw JSON payloads in milliseconds.
    """

    def __init__(self, base_url: str = "http://localhost:8000", client_id: str = "speed-bot-prime"):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.sync = ClockSynchronizer(base_url=self.base_url)
        self.session: Optional[aiohttp.ClientSession] = None
        self.queue_token: Optional[str] = None
        self.queue_id: Optional[str] = None

    async def init_session(self):
        """Initializes high-concurrency TCP session with keep-alive socket pooling."""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                keepalive_timeout=120.0,
                enable_cleanup_closed=True
            )
            self.session = aiohttp.ClientSession(
                connector=connector,
                headers={
                    "User-Agent": "MilliProtocolClient/1.0",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )

    async def pre_warm(self, event_id: str = "grand-concert-2026") -> Dict[str, Any]:
        """
        Pre-warms the TCP and TLS tunnel so socket is already open and authenticated.
        Pre-acquires queue token so it is cached in memory.
        """
        await self.init_session()
        t0 = time.perf_counter()

        # 1. Warm connection and calibrate clock
        calib = await self.sync.calibrate(session=self.session, event_id=event_id, samples=3)

        # 2. Pre-join queue to harvest pass token
        queue_res = await self.join_and_wait_queue(max_wait_sec=5.0)

        warmup_time_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "pre_warmed": True,
            "warmup_time_ms": round(warmup_time_ms, 2),
            "rtt_ms": calib.get("rtt_ms"),
            "token_acquired": bool(self.queue_token)
        }

    async def join_and_wait_queue(self, max_wait_sec: float = 5.0) -> Optional[str]:
        """Enters virtual queue and polls until admitted."""
        await self.init_session()

        # Join queue
        url = f"{self.base_url}/api/queue/join"
        async with self.session.post(url, json={"client_id": self.client_id}) as resp:
            data = await resp.json()
            self.queue_id = data.get("queue_id")
            if data.get("admitted") and data.get("token"):
                self.queue_token = data["token"]
                return self.queue_token

        # Poll if in queue
        t_start = time.time()
        while (time.time() - t_start) < max_wait_sec:
            poll_url = f"{self.base_url}/api/queue/status/{self.queue_id}"
            async with self.session.get(poll_url) as resp:
                data = await resp.json()
                if data.get("admitted") and data.get("token"):
                    self.queue_token = data["token"]
                    return self.queue_token
            await asyncio.sleep(0.05)

        return self.queue_token

    async def snipe_fastest_seat(
        self,
        event_id: str = "grand-concert-2026",
        preferred_seat: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Finds best available seat and executes atomic reservation in under 20 ms.
        """
        await self.init_session()
        t0 = time.perf_counter()

        # 1. Ensure queue token
        if not self.queue_token:
            await self.join_and_wait_queue(max_wait_sec=2.0)

        # 2. If no preferred seat, quickly grab first available
        target_seat = preferred_seat
        if not target_seat:
            seats_url = f"{self.base_url}/api/seats/{event_id}"
            async with self.session.get(seats_url) as resp:
                seats_data = await resp.json()
                for s in seats_data.get("seats", []):
                    if s["status"] == "available":
                        target_seat = s["id"]
                        break

        if not target_seat:
            return {
                "success": False,
                "error": "No available seats found",
                "time_to_acquire_ms": round((time.perf_counter() - t0) * 1000.0, 2)
            }

        # 3. Fire high-priority atomic reservation
        book_url = f"{self.base_url}/api/book"
        payload = {
            "event_id": event_id,
            "seat_id": target_seat,
            "client_id": self.client_id,
            "client_type": "api_speed_bot",
            "queue_token": self.queue_token
        }

        t_request0 = time.perf_counter()
        async with self.session.post(book_url, json=payload) as resp:
            data = await resp.json()
            rtt_ms = (time.perf_counter() - t_request0) * 1000.0

        total_ttf_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "success": resp.status == 200 and data.get("success", False),
            "seat_id": target_seat,
            "client_id": self.client_id,
            "client_type": "api_speed_bot",
            "total_ttf_ms": round(total_ttf_ms, 2),
            "network_rtt_ms": round(rtt_ms, 2),
            "server_process_ms": data.get("server_process_ms", 0.0),
            "error": data.get("detail") if resp.status != 200 else None
        }

    async def close(self):
        """Closes session."""
        if self.session and not self.session.closed:
            await self.session.close()
