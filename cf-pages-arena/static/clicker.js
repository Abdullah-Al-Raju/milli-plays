/**
 * Ultra-Fast Response Clicker Engine - Turbo Refactored v2
 * Features:
 * 1. Zero Forced-Synchronous Reflow: Layout metrics cached on trial start / resize.
 * 2. Decoupled UI & Visual Rendering: HUD text updates and target transform updates are
 *    batched into requestAnimationFrame (60fps), completely freeing the V8 execution thread
 *    from layout & style invalidation thrash.
 * 3. Atomic Sequence Counter: Immune to browser timer coarsening / Spectre clamp.
 * 4. In-page Zero-Clamp MessageChannel Hyper-Burst Engine for maximum CPS.
 */

const CLICKER = {
  isPlaying: false,
  duration: 20.0,
  timeRemaining: 20.0,
  timerInterval: null,
  rafId: null,
  clicks: 0,
  spawnTime: 0,
  spawnSeq: 0,
  lastHandledSeq: -1,
  latencies: [],
  secondBuckets: [],
  currentBucketClicks: 0,
  lastBucketTime: 0,
  targetEl: null,
  arenaEl: null,

  // Position buffer for decoupled 60fps rendering
  lastRx: 100,
  lastRy: 100,

  // Cached layout metrics to completely eliminate layout recalculation during clicks
  arenaWidth: 880,
  arenaHeight: 420,
  maxX: 800,
  maxY: 340,
  targetSize: 58,
  padding: 20,

  // HUD elements & rolling stats
  hudClicksEl: null,
  hudTimerEl: null,
  hudCpsEl: null,
  hudAvgLatEl: null,
  hudBestLatEl: null,
  lastHudUpdate: 0,
  minLatency: 999999,
  maxLatency: 0,
  totalLatency: 0
};

function updateDimensions() {
  if (CLICKER.arenaEl) {
    CLICKER.arenaWidth = CLICKER.arenaEl.clientWidth || 880;
    CLICKER.arenaHeight = CLICKER.arenaEl.clientHeight || 420;
    CLICKER.maxX = Math.max(100, CLICKER.arenaWidth - CLICKER.targetSize - CLICKER.padding);
    CLICKER.maxY = Math.max(100, CLICKER.arenaHeight - CLICKER.targetSize - CLICKER.padding);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  CLICKER.targetEl = document.getElementById("ultra-target");
  CLICKER.arenaEl = document.getElementById("arena-box");

  CLICKER.hudClicksEl = document.getElementById("clicks-display");
  CLICKER.hudTimerEl = document.getElementById("timer-display");
  CLICKER.hudCpsEl = document.getElementById("cps-display");
  CLICKER.hudAvgLatEl = document.getElementById("avg-latency-display");
  CLICKER.hudBestLatEl = document.getElementById("best-latency-display");

  updateDimensions();
  window.addEventListener("resize", updateDimensions);

  document.getElementById("start-btn").addEventListener("click", () => startTrial(20.0));
  document.getElementById("reset-btn").addEventListener("click", resetTrial);

  const hyperBtn = document.getElementById("hyper-btn");
  if (hyperBtn) {
    hyperBtn.addEventListener("click", () => {
      if (window.__CLICKER__ && window.__CLICKER__.hyperBurst) {
        window.__CLICKER__.hyperBurst(20.0);
      }
    });
  }

  // Pointer event listeners for synthetic and physical interactions
  CLICKER.targetEl.addEventListener("pointerdown", handleTargetHit);
  CLICKER.targetEl.addEventListener("mousedown", handleTargetHit);
  CLICKER.targetEl.addEventListener("click", handleTargetHit);

  // Expose API for V8 Hyper-Reflex execution
  window.__CLICKER__ = {
    start: (dur = 20.0) => startTrial(dur),
    reset: () => resetTrial(),
    getTargetInfo: () => {
      if (!CLICKER.targetEl || CLICKER.targetEl.style.display === "none") return null;
      return {
        spawnTime: CLICKER.spawnTime,
        spawnSeq: CLICKER.spawnSeq,
        clicks: CLICKER.clicks,
        timeRemaining: CLICKER.timeRemaining
      };
    },
    strike: () => handleTargetHit({ clientX: 0, clientY: 0 }),
    hyperBurst: (durationSec = 20.0) => {
      return new Promise((resolve) => {
        startTrial(durationSec);
        logFeed("⚡ [V8 Turbo] Engaging Zero-Clamp MessageChannel Hyper-Burst Engine!", "system");
        const ch = new MessageChannel();
        ch.port1.onmessage = () => {
          if (CLICKER.isPlaying) {
            handleTargetHit();
            ch.port2.postMessage(0);
          } else {
            resolve(window.__CLICKER__.getStats());
          }
        };
        ch.port2.postMessage(0);
      });
    },
    getStats: () => {
      const lats = CLICKER.latencies;
      const count = CLICKER.clicks;
      const avg = count > 0 ? (CLICKER.totalLatency / count) : 0;
      const min = count > 0 && CLICKER.minLatency < 999999 ? CLICKER.minLatency : 0;
      const max = CLICKER.maxLatency;
      const elapsed = CLICKER.duration - CLICKER.timeRemaining;
      const cps = elapsed > 0 ? (CLICKER.clicks / elapsed) : 0;

      return {
        isPlaying: CLICKER.isPlaying,
        clicks: CLICKER.clicks,
        duration: CLICKER.duration,
        elapsedSec: parseFloat(elapsed.toFixed(3)),
        cps: parseFloat(cps.toFixed(2)),
        avgLatencyMs: parseFloat(avg.toFixed(4)),
        minLatencyMs: parseFloat(min.toFixed(4)),
        maxLatencyMs: parseFloat(max.toFixed(4)),
        secondBuckets: [...CLICKER.secondBuckets],
        totalSamples: lats.length
      };
    }
  };
});

function logFeed(msg, type = "normal") {
  const feed = document.getElementById("clicker-log");
  if (!feed) return;
  const timeStr = new Date().toISOString().substring(14, 23);
  const div = document.createElement("div");
  div.className = `log-line ${type}`;
  div.innerText = `[${timeStr}] ${msg}`;
  feed.prepend(div);
  if (feed.children.length > 25) {
    feed.removeChild(feed.lastChild);
  }
}

function renderHUD() {
  if (!CLICKER.isPlaying) return;
  const now = performance.now();

  // Decoupled visual target positioning: update target position smoothly on animation frames
  CLICKER.targetEl.style.transform = `translate3d(${CLICKER.lastRx}px, ${CLICKER.lastRy}px, 0)`;

  if (now - CLICKER.lastHudUpdate >= 25) { // Smooth ~40fps HUD updates decoupled from click micro-ticks
    CLICKER.lastHudUpdate = now;
    if (CLICKER.hudClicksEl) CLICKER.hudClicksEl.innerText = CLICKER.clicks.toLocaleString();
    const elapsed = CLICKER.duration - CLICKER.timeRemaining;
    const cps = elapsed > 0 ? (CLICKER.clicks / elapsed).toFixed(1) : "0.0";
    if (CLICKER.hudTimerEl) CLICKER.hudTimerEl.innerText = `${CLICKER.timeRemaining.toFixed(1)}s`;
    if (CLICKER.hudCpsEl) CLICKER.hudCpsEl.innerText = `${parseFloat(cps).toLocaleString()} CPS`;
    if (CLICKER.clicks > 0) {
      const avg = (CLICKER.totalLatency / CLICKER.clicks).toFixed(3);
      if (CLICKER.hudAvgLatEl) CLICKER.hudAvgLatEl.innerText = `${avg} ms`;
      if (CLICKER.hudBestLatEl) CLICKER.hudBestLatEl.innerText = `${CLICKER.minLatency.toFixed(3)} ms`;
    }
  }
  CLICKER.rafId = requestAnimationFrame(renderHUD);
}

function startTrial(durationSec = 20.0) {
  resetTrial();
  updateDimensions();

  CLICKER.isPlaying = true;
  CLICKER.duration = durationSec;
  CLICKER.timeRemaining = durationSec;
  CLICKER.clicks = 0;
  CLICKER.latencies = [];
  CLICKER.secondBuckets = [];
  CLICKER.currentBucketClicks = 0;
  CLICKER.minLatency = 999999;
  CLICKER.maxLatency = 0;
  CLICKER.totalLatency = 0;
  CLICKER.spawnSeq = 0;
  CLICKER.lastHandledSeq = -1;

  document.getElementById("arena-overlay").style.display = "none";
  CLICKER.targetEl.style.display = "flex";

  if (CLICKER.hudClicksEl) CLICKER.hudClicksEl.innerText = "0";
  if (CLICKER.hudCpsEl) CLICKER.hudCpsEl.innerText = "0.0 CPS";
  if (CLICKER.hudAvgLatEl) CLICKER.hudAvgLatEl.innerText = "-- ms";
  if (CLICKER.hudBestLatEl) CLICKER.hudBestLatEl.innerText = "-- ms";

  logFeed(`▶ Initiating ${durationSec.toFixed(1)}-second ultra-response endurance trial!`, "stage");

  spawnTarget();

  const startTime = performance.now();
  CLICKER.lastBucketTime = startTime;

  // Background timer loop (tick every 50ms)
  CLICKER.timerInterval = setInterval(() => {
    const now = performance.now();
    const elapsed = (now - startTime) / 1000.0;
    CLICKER.timeRemaining = Math.max(0.0, CLICKER.duration - elapsed);

    // Track 1-second endurance buckets
    if (now - CLICKER.lastBucketTime >= 1000.0) {
      CLICKER.secondBuckets.push(CLICKER.currentBucketClicks);
      logFeed(`⏱ Second ${CLICKER.secondBuckets.length}s Pace: ${CLICKER.currentBucketClicks.toLocaleString()} clicks/sec`, "system");
      CLICKER.currentBucketClicks = 0;
      CLICKER.lastBucketTime = now;
    }

    if (CLICKER.timeRemaining <= 0.0) {
      endTrial();
    }
  }, 50);

  // Start decoupled requestAnimationFrame HUD loop
  CLICKER.rafId = requestAnimationFrame(renderHUD);
}

function spawnTarget() {
  if (!CLICKER.isPlaying) return;

  // Compute purely with cached bounds (ZERO layout reflow!)
  CLICKER.lastRx = Math.floor(Math.random() * (CLICKER.maxX - CLICKER.padding)) + CLICKER.padding;
  CLICKER.lastRy = Math.floor(Math.random() * (CLICKER.maxY - CLICKER.padding)) + CLICKER.padding;

  CLICKER.spawnSeq++;
  CLICKER.spawnTime = performance.now();
}

function handleTargetHit(e) {
  if (!CLICKER.isPlaying) return;
  // Sequence counter check (immune to timer coarsening)
  if (CLICKER.spawnSeq === CLICKER.lastHandledSeq) return;
  CLICKER.lastHandledSeq = CLICKER.spawnSeq;

  if (e && e.preventDefault) e.preventDefault();
  if (e && e.stopPropagation) e.stopPropagation();

  const now = performance.now();
  const latency = Math.max(0.0001, now - CLICKER.spawnTime);

  CLICKER.clicks++;
  CLICKER.currentBucketClicks++;
  CLICKER.totalLatency += latency;
  if (latency < CLICKER.minLatency) CLICKER.minLatency = latency;
  if (latency > CLICKER.maxLatency) CLICKER.maxLatency = latency;

  // Sample latencies for telemetry
  if (CLICKER.clicks <= 5000 || CLICKER.clicks % 20 === 0) {
    CLICKER.latencies.push(latency);
  }

  // Immediate zero-reflow respawn
  spawnTarget();
}

function endTrial() {
  CLICKER.isPlaying = false;
  clearInterval(CLICKER.timerInterval);
  if (CLICKER.rafId) cancelAnimationFrame(CLICKER.rafId);

  CLICKER.targetEl.style.display = "none";
  if (CLICKER.hudTimerEl) CLICKER.hudTimerEl.innerText = "0.0s";

  if (CLICKER.currentBucketClicks > 0) {
    CLICKER.secondBuckets.push(CLICKER.currentBucketClicks);
  }

  const total = CLICKER.clicks;
  const avg = total > 0 ? (CLICKER.totalLatency / total).toFixed(3) : "0.000";
  const min = total > 0 && CLICKER.minLatency < 999999 ? CLICKER.minLatency.toFixed(3) : "0.000";
  const cps = (total / CLICKER.duration).toFixed(1);

  if (CLICKER.hudClicksEl) CLICKER.hudClicksEl.innerText = total.toLocaleString();
  if (CLICKER.hudCpsEl) CLICKER.hudCpsEl.innerText = `${parseFloat(cps).toLocaleString()} CPS`;
  if (CLICKER.hudAvgLatEl) CLICKER.hudAvgLatEl.innerText = `${avg} ms`;
  if (CLICKER.hudBestLatEl) CLICKER.hudBestLatEl.innerText = `${min} ms`;

  logFeed(`🏁 20s Trial Completed! Total Clicks: ${total.toLocaleString()} (${parseFloat(cps).toLocaleString()} CPS) | Avg Latency: ${avg} ms | Peak: ${min} ms`, "stage");
  document.getElementById("arena-overlay").style.display = "flex";
  document.getElementById("arena-overlay").innerHTML = `<b>TRIAL FINISHED!</b><br>Total Clicks: ${total.toLocaleString()} (${parseFloat(cps).toLocaleString()} CPS)<br>Avg: ${avg} ms | Best: ${min} ms`;
}

function resetTrial() {
  CLICKER.isPlaying = false;
  clearInterval(CLICKER.timerInterval);
  if (CLICKER.rafId) cancelAnimationFrame(CLICKER.rafId);

  CLICKER.timeRemaining = CLICKER.duration;
  CLICKER.clicks = 0;
  CLICKER.latencies = [];
  CLICKER.secondBuckets = [];
  CLICKER.currentBucketClicks = 0;
  CLICKER.minLatency = 999999;
  CLICKER.maxLatency = 0;
  CLICKER.totalLatency = 0;
  CLICKER.spawnSeq = 0;
  CLICKER.lastHandledSeq = -1;

  if (CLICKER.hudTimerEl) CLICKER.hudTimerEl.innerText = `${CLICKER.duration.toFixed(1)}s`;
  if (CLICKER.hudClicksEl) CLICKER.hudClicksEl.innerText = "0";
  if (CLICKER.hudCpsEl) CLICKER.hudCpsEl.innerText = "0.0 CPS";
  if (CLICKER.hudAvgLatEl) CLICKER.hudAvgLatEl.innerText = "-- ms";
  if (CLICKER.hudBestLatEl) CLICKER.hudBestLatEl.innerText = "-- ms";
  document.getElementById("arena-overlay").style.display = "flex";
  document.getElementById("arena-overlay").innerText = "Click 'Start 20s Trial' or 'V8 Hyper-Burst' to initiate";
  CLICKER.targetEl.style.display = "none";
}
