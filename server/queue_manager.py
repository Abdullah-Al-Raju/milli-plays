"""
Virtual Waiting Room and Queue Token Manager.
Simulates enterprise waiting room mechanics (Queue-it / Ticketmaster Smart Queue).
"""

import time
import uuid
import hmac
import hashlib
import asyncio
from typing import Dict, Optional, Any, List


class QueueManager:
    """
    Manages client queue entry, position processing, and cryptographic pass tokens.
    """

    def __init__(self, secret_key: str = "ticket-booker-secret-key-2026", admission_rate_per_sec: int = 5):
        self.secret_key = secret_key.encode("utf-8")
        self.admission_rate = admission_rate_per_sec
        self.lock = asyncio.Lock()

        # Queue entries: {queue_id: {"queue_id": str, "client_id": str, "position": int, "admitted": bool, "token": str, "joined_at": float}}
        self.queue: Dict[str, Dict[str, Any]] = {}
        self.waiting_list: List[str] = []
        self.admitted_tokens: Dict[str, float] = {}  # {token: expiry_timestamp}
        self.is_queue_active = True

    def generate_token(self, queue_id: str, client_id: str, ttl_seconds: float = 300.0) -> str:
        """Generates HMAC-signed checkout pass token."""
        expiry = time.time() + ttl_seconds
        payload = f"{queue_id}:{client_id}:{expiry}"
        signature = hmac.new(self.secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        token = f"{payload}:{signature}"
        self.admitted_tokens[token] = expiry
        return token

    def verify_token(self, token: str) -> bool:
        """Verifies integrity and expiration of queue token."""
        if not self.is_queue_active:
            return True

        if not token:
            return False

        try:
            parts = token.split(":")
            if len(parts) != 4:
                return False

            queue_id, client_id, expiry_str, signature = parts
            expiry = float(expiry_str)

            if time.time() > expiry:
                return False

            payload = f"{queue_id}:{client_id}:{expiry_str}"
            expected_sig = hmac.new(self.secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
            return hmac.compare_digest(signature, expected_sig)
        except Exception:
            return False

    async def join_queue(self, client_id: str) -> Dict[str, Any]:
        """Adds client to the virtual waiting room."""
        async with self.lock:
            # Check if client already in queue
            for qid, q in self.queue.items():
                if q["client_id"] == client_id:
                    return {
                        "queue_id": qid,
                        "position": q["position"],
                        "admitted": q["admitted"],
                        "token": q.get("token")
                    }

            queue_id = str(uuid.uuid4())[:8]
            position = len(self.waiting_list) + 1
            now = time.time()

            entry = {
                "queue_id": queue_id,
                "client_id": client_id,
                "position": position,
                "admitted": False,
                "token": None,
                "joined_at": now
            }

            self.queue[queue_id] = entry
            self.waiting_list.append(queue_id)

            # Auto-admit immediately if queue is not active or position is 1
            if not self.is_queue_active or position <= 2:
                entry["admitted"] = True
                entry["position"] = 0
                entry["token"] = self.generate_token(queue_id, client_id)

            return {
                "queue_id": queue_id,
                "client_id": client_id,
                "position": entry["position"],
                "admitted": entry["admitted"],
                "token": entry["token"]
            }

    async def check_status(self, queue_id: str) -> Dict[str, Any]:
        """Checks position in queue; admits next batch if ready."""
        async with self.lock:
            entry = self.queue.get(queue_id)
            if not entry:
                return {"error": "Queue entry not found", "status_code": 404}

            if entry["admitted"]:
                return {
                    "queue_id": queue_id,
                    "position": 0,
                    "admitted": True,
                    "token": entry["token"]
                }

            # Update position
            try:
                current_idx = self.waiting_list.index(queue_id)
                entry["position"] = current_idx + 1

                # Admit if at the front
                if current_idx < self.admission_rate:
                    entry["admitted"] = True
                    entry["position"] = 0
                    entry["token"] = self.generate_token(queue_id, entry["client_id"])
                    self.waiting_list.remove(queue_id)
            except ValueError:
                pass

            return {
                "queue_id": queue_id,
                "position": entry["position"],
                "admitted": entry["admitted"],
                "token": entry.get("token")
            }

    async def reset(self):
        """Resets the queue."""
        async with self.lock:
            self.queue.clear()
            self.waiting_list.clear()
            self.admitted_tokens.clear()
