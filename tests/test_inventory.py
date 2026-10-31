"""
Unit tests for SeatInventory and QueueManager.
Verifies atomic reservation, race condition prevention, and queue token verification.
"""

import asyncio
import pytest
from server.inventory import SeatInventory
from server.queue_manager import QueueManager


@pytest.mark.asyncio
async def test_atomic_seat_reservation():
    inv = SeatInventory(total_seats=10, rows=2, cols=5)
    res = await inv.reserve_seat("A1", "client-1", "bot")
    assert res["success"] is True
    assert res["seat_id"] == "A1"
    assert res["booked_by"] == "client-1"

    # Second attempt on the same seat must fail
    res2 = await inv.reserve_seat("A1", "client-2", "bot")
    assert res2["success"] is False
    assert res2["status_code"] == 409


@pytest.mark.asyncio
async def test_concurrent_seat_race():
    """
    Simulates 50 concurrent bots attempting to claim the exact same seat simultaneously.
    Guarantees exactly ONE winner and 49 conflicts.
    """
    inv = SeatInventory(total_seats=10, rows=2, cols=5)

    async def _try_book(client_num):
        return await inv.reserve_seat("A1", f"bot-{client_num}", "bot")

    tasks = [_try_book(i) for i in range(50)]
    results = await asyncio.gather(*tasks)

    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    assert len(successes) == 1, f"Expected 1 winner, got {len(successes)}"
    assert len(failures) == 49
    assert all(f["status_code"] == 409 for f in failures)


@pytest.mark.asyncio
async def test_queue_tokens_and_admission():
    qm = QueueManager(admission_rate_per_sec=2)

    # Client 1 joins
    q1 = await qm.join_queue("client-1")
    assert q1["admitted"] is True
    assert q1["token"] is not None
    assert qm.verify_token(q1["token"]) is True

    # Tampered token must fail
    bad_token = q1["token"] + "tampered"
    assert qm.verify_token(bad_token) is False
