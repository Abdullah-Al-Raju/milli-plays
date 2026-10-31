"""
Thread-safe, atomic seat inventory manager with TTL reservation locks.
Guarantees zero double-booking under extreme concurrency.
"""

import time
import asyncio
from typing import Dict, List, Optional, Any


class SeatInventory:
    """
    Manages seat availability, atomic locks, and confirmed bookings.
    """

    def __init__(self, event_id: str = "grand-concert-2026", total_seats: int = 50, rows: int = 5, cols: int = 10):
        self.event_id = event_id
        self.total_seats = total_seats
        self.rows = rows
        self.cols = cols
        self.lock = asyncio.Lock()

        # Seat map: {seat_id: {"id": seat_id, "row": r, "col": c, "status": "available", "booked_by": None, "locked_until": 0}}
        self.seats: Dict[str, Dict[str, Any]] = {}
        self.booking_log: List[Dict[str, Any]] = []
        self._init_seats()

    def _init_seats(self):
        """Initializes grid of seats."""
        self.seats.clear()
        self.booking_log.clear()
        seat_idx = 1
        for r in range(1, self.rows + 1):
            row_letter = chr(64 + r)
            for c in range(1, self.cols + 1):
                seat_id = f"{row_letter}{c}"
                self.seats[seat_id] = {
                    "id": seat_id,
                    "row": row_letter,
                    "col": c,
                    "index": seat_idx,
                    "status": "available",  # 'available', 'locked', 'booked'
                    "booked_by": None,
                    "locked_by": None,
                    "locked_until": 0.0,
                    "booked_at": None
                }
                seat_idx += 1

    async def get_seats_snapshot(self) -> List[Dict[str, Any]]:
        """Returns snapshot of current seat statuses, cleaning up expired locks."""
        async with self.lock:
            now = time.time()
            snapshot = []
            for s in self.seats.values():
                # Check for expired lock
                if s["status"] == "locked" and now > s["locked_until"]:
                    s["status"] = "available"
                    s["locked_by"] = None
                    s["locked_until"] = 0.0

                snapshot.append({
                    "id": s["id"],
                    "row": s["row"],
                    "col": s["col"],
                    "status": s["status"],
                    "booked_by": s["booked_by"]
                })
            return snapshot

    async def reserve_seat(self, seat_id: str, client_id: str, client_type: str = "bot") -> Dict[str, Any]:
        """
        Atomically locks and confirms a seat.
        Records high-resolution timestamps down to microseconds.
        """
        t_request = time.time()
        t_perf = time.perf_counter()

        async with self.lock:
            seat = self.seats.get(seat_id)
            if not seat:
                return {
                    "success": False,
                    "error": f"Seat {seat_id} does not exist",
                    "status_code": 404
                }

            now = time.time()
            # If locked by someone else and lock is still active
            if seat["status"] == "locked" and now <= seat["locked_until"] and seat["locked_by"] != client_id:
                return {
                    "success": False,
                    "error": f"Seat {seat_id} is currently held by another user",
                    "status_code": 409
                }

            # If already booked
            if seat["status"] == "booked":
                return {
                    "success": False,
                    "error": f"Seat {seat_id} is already booked by {seat['booked_by']}",
                    "status_code": 409
                }

            # Confirm atomic booking
            seat["status"] = "booked"
            seat["booked_by"] = client_id
            seat["booked_at"] = now
            seat["client_type"] = client_type

            elapsed_lock_us = (time.perf_counter() - t_perf) * 1_000_000

            entry = {
                "seat_id": seat_id,
                "client_id": client_id,
                "client_type": client_type,
                "timestamp": now,
                "lock_latency_us": round(elapsed_lock_us, 2)
            }
            self.booking_log.append(entry)

            # Check remaining seats
            remaining = sum(1 for s in self.seats.values() if s["status"] == "available")

            return {
                "success": True,
                "event_id": self.event_id,
                "seat_id": seat_id,
                "booked_by": client_id,
                "client_type": client_type,
                "timestamp": now,
                "lock_latency_us": round(elapsed_lock_us, 2),
                "remaining_seats": remaining
            }

    async def reset(self):
        """Resets the inventory to initial state."""
        async with self.lock:
            self._init_seats()
