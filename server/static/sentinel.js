/**
 * Sentinel Fortress Client Telemetry Probe (Layers 2 & 3 Sensor)
 * Collects execution environment fingerprints, CDP automation artifacts,
 * prototype integrity checks, and high-frequency pointer kinematics.
 */

(() => {
  const SENTINEL = {
    trajectory: [],
    events: [],
    startTime: performance.now(),
    maxPoints: 150
  };

  // 1. Mouse Kinematics Recorder
  function recordPointer(e) {
    const t = performance.now();
    SENTINEL.trajectory.push({
      x: e.clientX,
      y: e.clientY,
      t: parseFloat(t.toFixed(2))
    });
    if (SENTINEL.trajectory.length > SENTINEL.maxPoints) {
      SENTINEL.trajectory.shift();
    }
  }

  function recordEvent(e) {
    SENTINEL.events.push({
      type: e.type,
      x: e.clientX,
      y: e.clientY,
      t: parseFloat(performance.now().toFixed(2))
    });
    if (SENTINEL.events.length > 25) {
      SENTINEL.events.shift();
    }
  }

  window.addEventListener("pointermove", recordPointer, { passive: true });
  window.addEventListener("mousemove", recordPointer, { passive: true });
  window.addEventListener("pointerdown", recordEvent, { passive: true });
  window.addEventListener("pointerup", recordEvent, { passive: true });
  window.addEventListener("click", recordEvent, { passive: true });

  // 2. Environment Fingerprinting
  function collectEnvironment() {
    const nav = navigator;

    // Check navigator.webdriver and descriptor
    let webdriverVal = nav.webdriver;
    let descriptorAnomaly = false;
    try {
      const desc = Object.getOwnPropertyDescriptor(Navigator.prototype, 'webdriver') ||
                   Object.getOwnPropertyDescriptor(nav, 'webdriver');
      if (desc && desc.get && !desc.get.toString().includes('[native code]')) {
        descriptorAnomaly = true;
      }
    } catch (e) {}

    // Check CDP automation hooks
    const cdpArtifacts = [];
    for (const key of Object.keys(window)) {
      if (key.includes('cdc_') || key.includes('__puppeteer') || key.includes('__playwright')) {
        cdpArtifacts.push(key);
      }
    }

    // Function.prototype.toString tampering check
    let toStringTampered = false;
    try {
      const evalStr = Function.prototype.toString.call(eval);
      if (!evalStr.includes('[native code]')) {
        toStringTampered = true;
      }
    } catch (e) {
      toStringTampered = true;
    }

    // WebGL Unmasked Vendor & Renderer
    let webglVendor = "";
    let webglRenderer = "";
    try {
      const canvas = document.createElement("canvas");
      const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
      if (gl) {
        const dbg = gl.getExtension("WEBGL_debug_renderer_info");
        if (dbg) {
          webglVendor = gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) || "";
          webglRenderer = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) || "";
        }
      }
    } catch (e) {}

    // Canvas 2D Hash
    let canvasHash = "";
    try {
      const c = document.createElement("canvas");
      c.width = 120;
      c.height = 30;
      const ctx = c.getContext("2d");
      if (ctx) {
        ctx.textBaseline = "top";
        ctx.font = "14px 'Arial'";
        ctx.fillStyle = "#f60";
        ctx.fillRect(10, 5, 60, 20);
        ctx.fillStyle = "#069";
        ctx.fillText("Sentinel🔒", 12, 8);
        const data = c.toDataURL();
        canvasHash = data.substring(data.length - 32);
      }
    } catch (e) {}

    return {
      webdriver: Boolean(webdriverVal),
      webdriver_descriptor_anomaly: descriptorAnomaly,
      cdp_artifacts_detected: cdpArtifacts,
      has_window_chrome: Boolean(window.chrome),
      hardware_concurrency: nav.hardwareConcurrency || 0,
      device_memory: nav.deviceMemory || 0,
      max_touch_points: nav.maxTouchPoints || 0,
      languages: nav.languages || [nav.language],
      screen_width: window.screen ? window.screen.width : 0,
      screen_height: window.screen ? window.screen.height : 0,
      toString_tampered: toStringTampered,
      webgl_vendor: webglVendor,
      webgl_renderer: webglRenderer,
      canvas_hash: canvasHash,
      user_agent: nav.userAgent
    };
  }

  // 3. PoW Miner in V8 (Sub-millisecond Web Worker / Loop)
  async function solvePoW(token, difficulty) {
    const target = "0".repeat(difficulty);
    const enc = new TextEncoder();
    let nonce = 0;

    while (nonce < 2000000) {
      const candidate = `${token}:${nonce}`;
      const buf = await crypto.subtle.digest("SHA-256", enc.encode(candidate));
      const hashArray = Array.from(new Uint8Array(buf));
      const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
      if (hashHex.startsWith(target)) {
        return { nonce, hash: hashHex };
      }
      nonce++;
    }
    return { nonce: -1, hash: null };
  }

  // Expose global API
  window.__SENTINEL__ = {
    getPayload: () => ({
      telemetry: collectEnvironment(),
      trajectory: [...SENTINEL.trajectory],
      events: [...SENTINEL.events]
    }),
    solvePoW,
    clearTelemetry: () => {
      SENTINEL.trajectory = [];
      SENTINEL.events = [];
    }
  };
})();
