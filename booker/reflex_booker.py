"""
Milli-Scrapes Reflex Booker Adapter.
Leverages MilliScrapeBrowser, ReflexSeatSniper, ConsentSniper, and TurnstileSniper.
Executes sub-50ms optical or DOM reflex booking against visual seat maps.
"""

import time
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

# Add local milli-scrapes to sys.path
milli_scrapes_dir = Path(__file__).resolve().parent.parent / "milli-scrapes"
if str(milli_scrapes_dir) not in sys.path:
    sys.path.insert(0, str(milli_scrapes_dir))

from milli_scrapes.browser.engine import MilliScrapeBrowser
from milli_scrapes.sniper.seat_sniper import ReflexSeatSniper
from milli_scrapes.sniper.consent_sniper import ConsentSniper
from milli_scrapes.sniper.turnstile_sniper import TurnstileSniper


class MilliReflexBooker:
    """
    Automated browser booking agent using Milli-Scrapes CDP engine.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        client_id: str = "milli-reflex-sniper",
        mode: str = "optical",  # 'optical' or 'dom'
        headless: bool = True
    ):
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.mode = mode
        self.headless = headless
        self.browser: Optional[MilliScrapeBrowser] = None
        self.sniper: Optional[ReflexSeatSniper] = None

    async def init(self):
        """Initializes CDP browser connection and primes snipers."""
        if self.browser is None:
            self.browser = MilliScrapeBrowser(headless=self.headless)
            await self.browser.start()
            self.sniper = ReflexSeatSniper(browser=self.browser)

    async def snipe_event(
        self,
        event_id: str = "grand-concert-2026",
        confirm_selector: str = "#confirm-booking",
        seat_selector: str = ".seat-available",
        auto_consent: bool = True,
        auto_turnstile: bool = True
    ) -> Dict[str, Any]:
        """
        Navigates to live seating chart, dismisses cookie consent, solves gates,
        and fires sub-50ms reflex seat booking.
        """
        await self.init()
        t0 = time.perf_counter()

        url = f"{self.base_url}/"
        # 1. Navigate and settle reactively without arbitrary sleeps
        t_nav0 = time.perf_counter()
        nav_res = await self.browser.navigate_and_settle(url)
        nav_ms = (time.perf_counter() - t_nav0) * 1000.0

        # 2. Auto-dismiss cookie banner if present
        if auto_consent:
            consent_sniper = ConsentSniper(self.browser)
            await consent_sniper.auto_dismiss_consent()

        # 3. Solve Turnstile challenge if present
        if auto_turnstile:
            turnstile_sniper = TurnstileSniper(self.browser)
            await turnstile_sniper.detect_and_solve()

        # 4. Fire Reflex Sniper
        t_snipe0 = time.perf_counter()
        if self.mode == "optical":
            # Scans RAM framebuffer for green available seat centroids (RGB: 46, 204, 113)
            res = await self.sniper.snipe_optical_seat(
                confirm_selector=confirm_selector,
                max_scan_seconds=5.0
            )
        else:
            # In-loop DOM event dispatch
            res = await self.sniper.snipe_dom_seat(
                seat_selector=seat_selector,
                confirm_selector=confirm_selector
            )
        snipe_reaction_ms = (time.perf_counter() - t_snipe0) * 1000.0

        total_ttf_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "success": res.get("status") == "booked",
            "client_id": self.client_id,
            "client_type": f"milli_reflex_{self.mode}",
            "mode": res.get("mode"),
            "total_ttf_ms": round(total_ttf_ms, 2),
            "nav_settle_ms": round(nav_ms, 2),
            "snipe_reaction_ms": round(snipe_reaction_ms, 2),
            "target_coords": res.get("target_coords"),
            "message": res.get("message")
        }

    async def close(self):
        """Closes browser session."""
        if self.browser:
            await self.browser.aclose()
            self.browser = None
            self.sniper = None
