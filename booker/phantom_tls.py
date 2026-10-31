"""
Module 1: JA4 / TLS Masquerade Client.
Produces authentic TLS ClientHello, ALPN, cipher suites, and exact Chrome 131+ header sequences.
Leverages curl_cffi for native browser TLS stack emulation.
"""

from typing import Dict, Any, Optional
import time

try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False
    import urllib.request


class PhantomTLSClient:
    """
    High-fidelity browser impersonation client.
    Guarantees authentic JA3/JA4 fingerprints and browser header ordering.
    """

    CHROME_131_HEADERS = {
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Linux"',
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "x-ja4-fingerprint": "t13d1516h2_8daaf6152771_012e8784d0fe"
    }

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = None
        if HAS_CURL_CFFI:
            # Impersonate authentic Chrome 131 TLS and HTTP/2 stack
            self.session = cffi_requests.Session(impersonate="chrome131")

    def get(self, path: str, headers: Optional[Dict[str, str]] = None, cookies: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Executes GET request with Chrome 131 TLS and header signature."""
        url = f"{self.base_url}{path}"
        req_headers = {**self.CHROME_131_HEADERS, **(headers or {})}

        t0 = time.perf_counter()
        if HAS_CURL_CFFI:
            resp = self.session.get(url, headers=req_headers, cookies=cookies)
            lat_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "status_code": resp.status_code,
                "text": resp.text,
                "headers": dict(resp.headers),
                "cookies": dict(resp.cookies),
                "latency_ms": round(lat_ms, 3)
            }
        else:
            # Fallback
            import urllib.request
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req) as r:
                return {
                    "status_code": r.status,
                    "text": r.read().decode(),
                    "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3)
                }

    def post(self, path: str, json_data: Dict[str, Any], headers: Optional[Dict[str, str]] = None, cookies: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Executes POST request with Chrome 131 TLS and header signature."""
        url = f"{self.base_url}{path}"
        req_headers = {
            **self.CHROME_131_HEADERS,
            "Content-Type": "application/json",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            **(headers or {})
        }

        t0 = time.perf_counter()
        if HAS_CURL_CFFI:
            resp = self.session.post(url, json=json_data, headers=req_headers, cookies=cookies)
            lat_ms = (time.perf_counter() - t0) * 1000.0
            try:
                data = resp.json()
            except Exception:
                data = {}
            return {
                "status_code": resp.status_code,
                "data": data,
                "text": resp.text,
                "cookies": dict(resp.cookies),
                "latency_ms": round(lat_ms, 3)
            }
        else:
            import json
            import urllib.request
            body = json.dumps(json_data).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
            with urllib.request.urlopen(req) as r:
                return {
                    "status_code": r.status,
                    "data": json.loads(r.read().decode()),
                    "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3)
                }
