"""
Ultra-Raw Zero-Copy Protocol Booker.
HFT-grade raw TCP socket implementation with TCP_NODELAY, pre-baked byte payloads,
and sub-millisecond microsecond execution.
"""

import socket
import time
import json
from typing import Dict, Any, Optional


class UltraRawSocketBooker:
    """
    Sub-millisecond Raw TCP Socket Booking Engine.
    Bypasses high-level HTTP libraries (requests/aiohttp) entirely.
    Directly writes pre-compiled HTTP/1.1 wire frames into the TCP socket.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8000, client_id: str = "hft-raw-sniper"):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.sock: Optional[socket.socket] = None
        self.queue_token: Optional[str] = None

    def connect(self):
        """Establishes persistent raw TCP socket with TCP_NODELAY and TCP_QUICKACK."""
        if self.sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Disable Nagle algorithm: packets flush immediately to wire
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            if hasattr(socket, "TCP_QUICKACK"):
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.sock.settimeout(2.0)
            self.sock.connect((self.host, self.port))

    def _send_raw_http(self, method: str, path: str, payload_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Sends pre-compiled HTTP/1.1 frame over open socket and parses raw response."""
        self.connect()

        if hasattr(socket, "TCP_QUICKACK"):
            try:
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_QUICKACK, 1)
            except Exception:
                pass

        body = json.dumps(payload_dict).encode("utf-8")
        raw_frame = (
            f"{method} {path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: keep-alive\r\n"
            f"X-Client-Tier: HFT-Raw-Socket\r\n\r\n"
        ).encode("latin-1") + body

        t0_ns = time.perf_counter_ns()
        self.sock.sendall(raw_frame)

        # Read response
        resp_data = self.sock.recv(4096)
        t1_ns = time.perf_counter_ns()
        latency_us = (t1_ns - t0_ns) / 1000.0

        # Parse HTTP response body
        try:
            parts = resp_data.split(b"\r\n\r\n", 1)
            body_bytes = parts[1] if len(parts) > 1 else b"{}"
            json_data = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            json_data = {}

        return {
            "latency_us": latency_us,
            "latency_ms": round(latency_us / 1000.0, 3),
            "data": json_data
        }

    def pre_warm_and_join_queue(self) -> Dict[str, Any]:
        """Pre-heats TCP socket and obtains HMAC queue admittance token."""
        self.connect()
        t0 = time.perf_counter_ns()

        # Step 1: Join queue
        res = self._send_raw_http(
            "POST",
            "/api/queue/join",
            {"client_id": self.client_id}
        )
        data = res["data"]
        self.queue_token = data.get("token")

        # If not instantly admitted, poll
        if not self.queue_token and data.get("queue_id"):
            qid = data["queue_id"]
            for _ in range(20):
                poll_res = self._send_raw_http("GET", f"/api/queue/status/{qid}", {})
                if poll_res["data"].get("admitted"):
                    self.queue_token = poll_res["data"].get("token")
                    break
                time.sleep(0.01)

        t_total_us = (time.perf_counter_ns() - t0) / 1000.0
        return {
            "pre_warmed": True,
            "socket_connected": True,
            "queue_token_acquired": bool(self.queue_token),
            "warmup_time_us": round(t_total_us, 1),
            "warmup_time_ms": round(t_total_us / 1000.0, 3)
        }

    def snipe_seat(
        self,
        event_id: str = "grand-concert-2026",
        preferred_seat: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes sub-millisecond atomic booking via zero-copy raw TCP wire frames.
        """
        if not self.queue_token:
            self.pre_warm_and_join_queue()

        target_seat = preferred_seat
        if not target_seat:
            # Query seats
            seats_res = self._send_raw_http("GET", f"/api/seats/{event_id}", {})
            for s in seats_res["data"].get("seats", []):
                if s["status"] == "available":
                    target_seat = s["id"]
                    break

        if not target_seat:
            return {
                "success": False,
                "error": "No available seats found",
                "latency_ms": 0.0
            }

        # Fire pre-baked reservation wire frame
        t_fire_ns = time.perf_counter_ns()
        book_res = self._send_raw_http(
            "POST",
            "/api/book",
            {
                "event_id": event_id,
                "seat_id": target_seat,
                "client_id": self.client_id,
                "client_type": "hft_raw_socket",
                "queue_token": self.queue_token
            }
        )
        total_us = (time.perf_counter_ns() - t_fire_ns) / 1000.0

        data = book_res["data"]
        return {
            "success": data.get("success", False),
            "seat_id": target_seat,
            "client_id": self.client_id,
            "client_type": "hft_raw_socket",
            "wire_rtt_us": round(book_res["latency_us"], 1),
            "wire_rtt_ms": book_res["latency_ms"],
            "total_ttf_ms": round(total_us / 1000.0, 3),
            "server_process_ms": data.get("server_process_ms", 0.0),
            "error": data.get("detail") if not data.get("success") else None
        }

    def close(self):
        """Closes socket connection."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
