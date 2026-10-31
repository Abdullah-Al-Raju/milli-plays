// 30-Second Visual Reaction Game Engine
let isPlaying = false;
let gameDuration = 30.0;
let timeRemaining = 30.0;
let timerInterval = null;
let score = 0;
let ballSpawnTime = 0;
let reactionTimes = [];
let targetBall = null;
let playArea = null;

document.addEventListener("DOMContentLoaded", () => {
  targetBall = document.getElementById("target-ball");
  playArea = document.getElementById("play-area");

  document.getElementById("start-btn").addEventListener("click", startGame);
  document.getElementById("reset-btn").addEventListener("click", resetGame);
  document.getElementById("modal-restart-btn").addEventListener("click", () => {
    document.getElementById("scorecard-modal").style.display = "none";
    startGame();
  });

  // Target ball click handler (supports native click, mousedown, pointerdown, and direct CDP dispatch)
  targetBall.addEventListener("pointerdown", handleBallHit);
  targetBall.addEventListener("mousedown", handleBallHit);
  targetBall.addEventListener("click", handleBallHit);

  // Expose programmatic hooks on window for automation
  window.__START_GAME__ = startGame;
  window.__RESET_GAME__ = resetGame;
  window.__HIT_TARGET__ = () => handleBallHit({ clientX: 0, clientY: 0 });
});

function startGame() {
  if (isPlaying) resetGame();

  isPlaying = true;
  score = 0;
  timeRemaining = gameDuration;
  reactionTimes = [];

  document.getElementById("score-display").innerText = "0";
  document.getElementById("last-latency-display").innerText = "-- ms";
  document.getElementById("avg-latency-display").innerText = "-- ms";
  document.getElementById("overlay-msg").style.display = "none";
  document.getElementById("scorecard-modal").style.display = "none";

  logGameEvent("▶ Round started! Target ball active for 30.0 seconds.", "system");

  // Notify backend API
  fetch("/api/game/start", { method: "POST" }).catch(() => {});

  // Spawn first ball
  spawnBall();

  // Start countdown timer
  const startTime = performance.now();
  timerInterval = setInterval(() => {
    const elapsed = (performance.now() - startTime) / 1000.0;
    timeRemaining = Math.max(0.0, gameDuration - elapsed);

    document.getElementById("timer-display").innerText = timeRemaining.toFixed(1) + "s";

    if (timeRemaining <= 0.0) {
      endGame();
    }
  }, 50);
}

function spawnBall() {
  if (!isPlaying) return;

  const areaWidth = playArea.clientWidth;
  const areaHeight = playArea.clientHeight;
  const ballSize = 54;
  const padding = 20;

  // Compute random coordinate strictly inside play bounds
  const maxX = areaWidth - ballSize - padding;
  const maxY = areaHeight - ballSize - padding;

  const randX = Math.floor(Math.random() * (maxX - padding)) + padding;
  const randY = Math.floor(Math.random() * (maxY - padding)) + padding;

  targetBall.style.left = `${randX}px`;
  targetBall.style.top = `${randY}px`;
  targetBall.style.display = "flex";

  ballSpawnTime = performance.now();

  // Expose global state for optical/CDP bot tracking
  const rect = targetBall.getBoundingClientRect();
  window.__TARGET_INFO__ = {
    x: Math.round(rect.left + rect.width / 2),
    y: Math.round(rect.top + rect.height / 2),
    local_x: randX + ballSize / 2,
    local_y: randY + ballSize / 2,
    spawn_time: ballSpawnTime,
    hit_count: score
  };
}

let lastHitSpawnTime = -1;

function handleBallHit(e) {
  if (!isPlaying) return;
  if (ballSpawnTime === lastHitSpawnTime) return; // Prevent double trigger on same spawn
  lastHitSpawnTime = ballSpawnTime;

  if (e && e.preventDefault) e.preventDefault();
  if (e && e.stopPropagation) e.stopPropagation();

  const now = performance.now();
  const latencyMs = (now - ballSpawnTime).toFixed(1);
  reactionTimes.push(parseFloat(latencyMs));
  score++;

  // Update HUD
  document.getElementById("score-display").innerText = score;
  document.getElementById("last-latency-display").innerText = `${latencyMs} ms`;

  const avgLatency = (reactionTimes.reduce((a, b) => a + b, 0) / reactionTimes.length).toFixed(1);
  document.getElementById("avg-latency-display").innerText = `${avgLatency} ms`;

  logGameEvent(`🎯 Hit #${score}: Reaction time ${latencyMs} ms at (${Math.round(e.clientX || 0)}, ${Math.round(e.clientY || 0)})`, "hit");

  // Immediate respawn in new random spot
  spawnBall();
}

function endGame() {
  isPlaying = false;
  clearInterval(timerInterval);
  targetBall.style.display = "none";
  document.getElementById("timer-display").innerText = "0.0s";

  const totalHits = score;
  const hps = (totalHits / gameDuration).toFixed(2);
  const avgMs = reactionTimes.length > 0
    ? (reactionTimes.reduce((a, b) => a + b, 0) / reactionTimes.length).toFixed(1)
    : "0.0";
  const bestMs = reactionTimes.length > 0 ? Math.min(...reactionTimes).toFixed(1) : "0.0";

  logGameEvent(`🏁 Round Over! Final Score: ${totalHits} Hits (${hps} HPS), Avg Latency: ${avgMs} ms`, "system");

  // Show Scorecard Modal
  document.getElementById("final-hits").innerText = totalHits;
  document.getElementById("final-hps").innerText = hps;
  document.getElementById("final-avg-ms").innerText = `${avgMs} ms`;
  document.getElementById("final-best-ms").innerText = `${bestMs} ms`;
  document.getElementById("scorecard-modal").style.display = "flex";

  // Post summary to server
  fetch("/api/game/end", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      total_hits: totalHits,
      hps: parseFloat(hps),
      avg_latency_ms: parseFloat(avgMs),
      best_latency_ms: parseFloat(bestMs),
      duration_sec: gameDuration
    })
  }).catch(() => {});
}

function resetGame() {
  isPlaying = false;
  clearInterval(timerInterval);
  score = 0;
  timeRemaining = gameDuration;
  reactionTimes = [];

  document.getElementById("timer-display").innerText = "30.0s";
  document.getElementById("score-display").innerText = "0";
  document.getElementById("last-latency-display").innerText = "-- ms";
  document.getElementById("avg-latency-display").innerText = "-- ms";
  document.getElementById("overlay-msg").style.display = "block";
  document.getElementById("scorecard-modal").style.display = "none";
  targetBall.style.display = "none";

  logGameEvent("↺ Arena reset.", "system");
}

function logGameEvent(text, type = "normal") {
  const logFeed = document.getElementById("game-log");
  if (!logFeed) return;

  const timeStr = new Date().toISOString().substring(14, 23);
  const div = document.createElement("div");
  div.className = `log-line ${type}`;
  div.innerText = `[${timeStr}] ${text}`;

  logFeed.prepend(div);
}
