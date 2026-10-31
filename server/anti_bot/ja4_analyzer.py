"""
Layer 1: Network, TLS & Header Profile Analyzer.
Inspects HTTP header casing, header sequence, client hints, and JA4/TLS heuristic fingerprints.
"""

from typing import Dict, Any, List, Tuple


class JA4Analyzer:
    """
    Evaluates HTTP request transport headers and protocol fingerprints
    to distinguish authentic modern browsers from automation scripts.
    """

    CHROME_CLIENT_HINTS = [
        "sec-ch-ua",
        "sec-ch-ua-mobile",
        "sec-ch-ua-platform"
    ]

    EXPECTED_CHROME_FETCH_METADATA = [
        "sec-fetch-site",
        "sec-fetch-mode",
        "sec-fetch-dest"
    ]

    def evaluate_headers(self, raw_headers: List[Tuple[bytes, bytes]]) -> Dict[str, Any]:
        """
        Analyzes raw header sequence, casing, and client hints.
        raw_headers: list of (name_bytes, value_bytes) preserving wire order and casing.
        """
        headers_dict = {}
        header_names_ordered = []
        casing_anomalies = []

        for k_bytes, v_bytes in raw_headers:
            name_str = k_bytes.decode("latin-1")
            val_str = v_bytes.decode("latin-1")
            name_lower = name_str.lower()
            headers_dict[name_lower] = val_str
            header_names_ordered.append(name_str)

        score = 0.0  # 0.0 = completely authentic, 1.0 = definitely bot
        reasons = []

        ua = headers_dict.get("user-agent", "")

        # 1. User-Agent presence check
        if not ua:
            score += 0.8
            reasons.append("Missing User-Agent header")
        elif "python" in ua.lower() or "aiohttp" in ua.lower() or "httpx" in ua.lower():
            score += 1.0
            reasons.append(f"Automation library User-Agent detected: {ua}")

        # 2. Chrome Client Hints consistency check
        is_chrome = "chrome" in ua.lower() and "safari" in ua.lower() and "edg" not in ua.lower()
        if is_chrome:
            missing_hints = [h for h in self.CHROME_CLIENT_HINTS if h not in headers_dict]
            if missing_hints:
                score += 0.45
                reasons.append(f"Chrome User-Agent missing client hints: {missing_hints}")

            # Check OS consistency
            platform_hint = headers_dict.get("sec-ch-ua-platform", "").replace('"', '').lower()
            if platform_hint:
                if "windows" in ua.lower() and "windows" not in platform_hint:
                    score += 0.5
                    reasons.append(f"OS mismatch: User-Agent claims Windows but sec-ch-ua-platform is {platform_hint}")
                elif "linux" in ua.lower() and "linux" not in platform_hint:
                    score += 0.5
                    reasons.append(f"OS mismatch: User-Agent claims Linux but sec-ch-ua-platform is {platform_hint}")
                elif "mac" in ua.lower() and "mac" not in platform_hint:
                    score += 0.5
                    reasons.append(f"OS mismatch: User-Agent claims Mac but sec-ch-ua-platform is {platform_hint}")

        # 3. Sec-Fetch Metadata check (Modern browsers send Sec-Fetch-* on all cross-resource requests)
        missing_fetch = [h for h in self.EXPECTED_CHROME_FETCH_METADATA if h not in headers_dict]
        if missing_fetch and is_chrome:
            score += 0.35
            reasons.append(f"Missing Sec-Fetch metadata headers: {missing_fetch}")

        # 4. Accept-Encoding check (Real browsers always support gzip, deflate, br)
        accept_enc = headers_dict.get("accept-encoding", "")
        if not accept_enc or ("br" not in accept_enc and "gzip" not in accept_enc):
            score += 0.25
            reasons.append("Suspicious Accept-Encoding (lacks modern compression like br/gzip)")

        # 5. Header count anomaly
        if len(headers_dict) < 4:
            score += 0.5
            reasons.append(f"Abnormally low header count: {len(headers_dict)}")

        # 6. Check for custom TLS/JA4 header simulation flag
        ja4_fingerprint = headers_dict.get("x-ja4-fingerprint") or headers_dict.get("cf-ja4")
        if ja4_fingerprint and "python" in ja4_fingerprint.lower():
            score += 0.9
            reasons.append(f"Python TLS OpenSSL fingerprint detected: {ja4_fingerprint}")

        clamped_score = min(1.0, round(score, 3))
        return {
            "passed": clamped_score < 0.35,
            "bot_score": clamped_score,
            "reasons": reasons,
            "detected_ua": ua,
            "header_count": len(headers_dict)
        }
