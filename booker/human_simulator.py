"""
Simulated Human Booker.
Models realistic consumer browser behavior, cognitive perception latency, and DOM interaction delays.
"""

import time
import random
import asyncio
from typing import Dict, Any, Optional
import aiohttp


class HumanBrowserSimulator:
    """
    Simulates a human user opening a browser, loading full assets,
    visually scanning the seat chart, and clicking to book.
    """

    def __init__(self, base_url: str = "http://localhost:8000", client_id: str = "human-alex-2026"):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id

    async def simulate_human_checkout(
        self,
        event_id: str = "grand-concert-2026",
        perception_delay_ms: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes a simulated human booking flow with realistic delays:
        - Asset download and DOM parsing: 1,200 - 2,000 ms
        - Visual scanning & cognitive hesitation: 300 - 600 ms
        - Mouse movement & click: 150 - 350 ms
        - Form submit: Network RTT
        """
        t0 = time.perf_counter()

        # 1. Full page download + asset render latency (simulated)
        page_load_delay = random.uniform(1.2, 2.0)
        await asyncio.sleep(page_load_delay)

        async with aiohttp.ClientSession() as session:
            # 2. Join Queue
            queue_url = f"{self.base_url}/api/queue/join"
            async with session.post(queue_url, json={"client_id": self.client_id}) as resp:
                q_data = await resp.json()
                queue_token = q_data.get("token")

            # 3. Read seats
            seats_url = f"{self.base_url}/api/seats/{event_id}"
            async with session.get(seats_url) as resp:
                seats_data = await resp.json()
                available = [s["id"] for s in seats_data.get("seats", []) if s["status"] == "available"]

            if not available:
                return {
                    "success": False,
                    "error": "Sold out before human could click",
                    "client_id": self.client_id,
                    "client_type": "human_simulator",
                    "total_ttf_ms": round((time.perf_counter() - t0) * 1000.0, 2)
                }

            # 4. Human visual perception & hesitation delay
            human_reaction_delay = perception_delay_ms / 1000.0 if perception_delay_ms else random.uniform(0.35, 0.75)
            await asyncio.sleep(human_reaction_delay)

            # Pick a seat
            target_seat = random.choice(available)

            # 5. Form click & submit
            book_url = f"{self.base_url}/api/book"
            payload = {
                "event_id": event_id,
                "seat_id": target_seat,
                "client_id": self.client_id,
                "client_type": "human_simulator",
                "queue_token": queue_token
            }

            t_req = time.perf_counter()
            async with session.post(book_url, json=payload) as resp:
                result = await resp.json()
                net_rtt = (time.perf_counter() - t_req) * 1000.0

            total_ttf_ms = (time.perf_counter() - t0) * 1000.0

            return {
                "success": resp.status == 200 and result.get("success", False),
                "seat_id": target_seat,
                "client_id": self.client_id,
                "client_type": "human_simulator",
                "total_ttf_ms": round(total_ttf_ms, 2),
                "human_reaction_ms": round((page_load_delay + human_reaction_delay) * 1000.0, 2),
                "network_rtt_ms": round(net_rtt, 2),
                "error": result.get("detail") if resp.status != 200 else None
            }
