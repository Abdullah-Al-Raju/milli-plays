/**
 * Cloudflare Pages Advanced Mode: _worker.js
 * Runs directly on Cloudflare Edge global network for milli-plays.pages.dev.
 * Handles:
 * 1. Microsecond Edge Routing & Aliases
 * 2. Official Cloudflare Turnstile Siteverify (via env.TURNSTILE_SECRET)
 * 3. Seat Booking & Microsecond Edge Ping API
 * 4. Static Asset Passthrough via env.ASSETS
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const turnstileSecret = env.TURNSTILE_SECRET || "";
    const masterKey = env.MASTER_KEY || "";

    // ---------------------------------------------------------
    // Route 1: /api/verify - Official Turnstile Server Siteverify
    // ---------------------------------------------------------
    if (url.pathname === "/api/verify" && request.method === "POST") {
      let body = {};
      try {
        body = await request.json();
      } catch (e) {
        return Response.json({ success: false, error: "Invalid JSON body" }, { status: 400 });
      }

      const adminKey = request.headers.get("X-Sentinel-Admin-Key") || body.admin_key;
      if (masterKey && adminKey === masterKey) {
        return Response.json({
          success: true,
          unconditional_access: true,
          auth_method: "MASTER_KEY_AUTHORIZED",
          hostname: url.hostname
        });
      }

      const token = body.token;
      if (!token && turnstileSecret) {
        return Response.json({ success: false, error: "Missing Turnstile response token" }, { status: 400 });
      }

      if (!turnstileSecret) {
        return Response.json({
          success: true,
          challenge_ts: new Date().toISOString(),
          hostname: url.hostname,
          action: "public_access",
          edge_colo: request.cf?.colo || "EDGE"
        });
      }

      const formData = new FormData();
      formData.append("secret", turnstileSecret);
      formData.append("response", token || "");
      const remoteIp = request.headers.get("CF-Connecting-IP") || "";
      if (remoteIp) formData.append("remoteip", remoteIp);

      try {
        const cfResp = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
          method: "POST",
          body: formData
        });
        const cfData = await cfResp.json();
        return Response.json({
          success: cfData.success,
          challenge_ts: cfData.challenge_ts,
          hostname: cfData.hostname,
          error_codes: cfData["error-codes"] || [],
          action: cfData.action,
          cdata: cfData.cdata,
          edge_colo: request.cf?.colo || "EDGE"
        });
      } catch (err) {
        return Response.json({ success: false, error: "Cloudflare upstream siteverify error: " + err.message }, { status: 502 });
      }
    }

    // ---------------------------------------------------------
    // Route 2: /api/book - Protected Seat Booking
    // ---------------------------------------------------------
    if (url.pathname === "/api/book" && request.method === "POST") {
      let body = {};
      try {
        body = await request.json();
      } catch (e) {
        return Response.json({ success: false, error: "Invalid JSON body" }, { status: 400 });
      }

      const adminKey = request.headers.get("X-Sentinel-Admin-Key") || body.admin_key;
      const isMaster = Boolean(masterKey && adminKey === masterKey);

      if (!isMaster && turnstileSecret) {
        const token = body.turnstile_token || request.headers.get("CF-Turnstile-Token");
        if (!token) {
          return Response.json({
            success: false,
            error: "BLOCKED: Cloudflare Turnstile token or Master Password required.",
            waf_status: "CHALLENGE_REQUIRED"
          }, { status: 403 });
        }

        // Verify with Cloudflare siteverify
        const formData = new FormData();
        formData.append("secret", turnstileSecret);
        formData.append("response", token);
        const remoteIp = request.headers.get("CF-Connecting-IP") || "";
        if (remoteIp) formData.append("remoteip", remoteIp);

        const cfResp = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
          method: "POST",
          body: formData
        });
        const cfData = await cfResp.json();

        if (!cfData.success) {
          return Response.json({
            success: false,
            error: "BLOCKED: Cloudflare Turnstile verification failed.",
            details: cfData["error-codes"] || []
          }, { status: 403 });
        }
      }

      const seatId = body.seat_id || "A1";
      const clientId = body.client_id || "unknown";

      return Response.json({
        success: true,
        seat_id: seatId,
        client_id: clientId,
        booked_at: new Date().toISOString(),
        edge_colo: request.cf?.colo || "EDGE",
        auth_method: isMaster ? "MASTER_KEY_AUTHORIZED" : (turnstileSecret ? "CLOUDFLARE_TURNSTILE_VERIFIED" : "PUBLIC_EDGE_ACCESS"),
        message: `Seat ${seatId} successfully booked on Cloudflare Edge!`
      });
    }

    // ---------------------------------------------------------
    // Route 3: /api/seats - Real-time seat inventory
    // ---------------------------------------------------------
    if (url.pathname === "/api/seats") {
      const seats = [];
      const rows = ["A", "B", "C", "D", "E"];
      let idx = 1;
      for (const r of rows) {
        for (let c = 1; c <= 10; c++) {
          seats.push({
            id: `${r}${c}`,
            row: r,
            col: c,
            index: idx++,
            status: "available",
            price: r === "A" ? 250 : (r === "B" ? 180 : 95)
          });
        }
      }
      return Response.json({
        event_id: "grand-concert-2026",
        title: "Grand Arena World Tour 2026",
        venue: "Cloudflare Edge Global Network",
        total_seats: seats.length,
        seats: seats
      });
    }

    // ---------------------------------------------------------
    // Route 4: /api/ping - Microsecond Edge RTT Latency Diagnostic
    // ---------------------------------------------------------
    if (url.pathname === "/api/ping") {
      return Response.json({
        success: true,
        edge_colo: request.cf?.colo || "EDGE",
        timestamp_utc: new Date().toISOString(),
        timestamp_ms: Date.now(),
        http_protocol: request.cf?.httpProtocol || "HTTP/2",
        asn: request.cf?.asn,
        client_country: request.cf?.country || "US"
      }, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Cache-Control": "no-store, max-age=0"
        }
      });
    }

    // Clean Short-form Aliases -> Extensionless Clean URLs
    const shortAliases = {
      "/drive": "/milli-drive",
      "/scalper-royale": "/milli-scalper-royale",
      "/matrix": "/milli-matrix",
      "/maze": "/milli-maze",
      "/rhythm": "/milli-rhythm",
      "/orbit": "/milli-orbit",
      "/snake": "/milli-snake",
      "/swarm": "/milli-swarm",
      "/danmaku": "/milli-danmaku",
      "/pong": "/milli-pong",
      "/trader": "/milli-trader",
      "/stealth": "/milli-stealth",
      "/sweeper": "/milli-sweeper",
      "/defense": "/milli-defense",
      "/portal": "/milli-portal",
      "/circuit": "/milli-circuit"
    };

    const trimmedPath = url.pathname.endsWith("/") && url.pathname.length > 1 ? url.pathname.slice(0, -1) : url.pathname;
    if (shortAliases[trimmedPath]) {
      return Response.redirect(new URL(shortAliases[trimmedPath], request.url).toString(), 308);
    }

    // Static asset fallback (Cloudflare Pages env.ASSETS natively serves clean URLs)
    return env.ASSETS.fetch(request);
  }
};
