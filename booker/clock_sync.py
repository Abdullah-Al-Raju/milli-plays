"""
Precision Clock Drift Synchronizer.
Calculates client-server latency offset down to milliseconds using Cristian's Algorithm.
"""

import time
import asyncio
from typing import Dict, Any, Optional
import aiohttp


class ClockSynchronizer:
    """
    Measures network RTT and server clock drift for microsecond-accurate drop synchronization.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.clock_drift_ms: float = 0.0
        self.rtt_ms: float = 0.0
        self.calibrated = False

    async def calibrate(self, session: Optional[aiohttp.ClientSession] = None, event_id: str = "grand-concert-2026", samples: int = 5) -> Dict[str, Any]:
        """
        Samples server timestamp across multiple requests to calculate smoothed RTT and clock drift.
        """
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        drifts = []
        rtts = []

        try:
            url = f"{self.base_url}/api/event/{event_id}"
            for _ in range(samples):
                t_send = time.time() * 1000.0
                async with session.get(url) as resp:
                    data = await resp.json()
                    t_recv = time.time() * 1000.0

                server_time_ms = data.get("server_time_ms", data.get("server_time", 0) * 1000.0)
                rtt = t_recv - t_send
                # Cristian's algorithm: drift = server_time - (t_send + rtt / 2)
                estimated_server_current = server_time_ms + (rtt / 2.0)
                drift = estimated_server_current - t_recv

                rtts.append(rtt)
                drifts.append(drift)
                await asyncio.sleep(0.01)

            # Average metrics
            self.rtt_ms = sum(rtts) / len(rtts)
            self.clock_drift_ms = sum(drifts) / len(drifts)
            self.calibrated = True

            return {
                "calibrated": True,
                "rtt_ms": round(self.rtt_ms, 2),
                "clock_drift_ms": round(self.clock_drift_ms, 2)
            }
        finally:
            if close_session:
                await session.close()

    def get_estimated_server_time_ms(self) -> float:
        """Returns current local time adjusted for server clock drift."""
        return (time.time() * 1000.0) + self.clock_drift_ms

    async def wait_until_target(self, target_server_time_ms: float):
        """
        Sleeps until target server timestamp arrives with sub-millisecond precision.
        """
        while True:
            current = self.get_estimated_server_time_ms()
            diff = target_server_time_ms - current
            if diff <= 0.5:
                break
            elif diff > 50:
                await asyncio.sleep((diff - 20) / 1000.0)
            else:
                await asyncio.sleep(0.001)
