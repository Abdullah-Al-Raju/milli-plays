/**
 * The 5-Minute Precision Gauntlet Engine
 * Manages Stage 1 (Vector Circuit Drawing), Stage 2 (Vector Signature Tracing), and Stage 3 (Crypto Speed Writing).
 */

const GAUNTLET_STATE = {
  active: false,
  stage: 1,
  startTime: 0,
  stage1Time: 0,
  stage2Time: 0,
  stage3Time: 0,
  totalTime: 0,
  stage1Completed: false,
  stage2Completed: false,
  stage3Completed: false,
  actionTimestamps: []
};

// Target Transcript for Stage 3
const CRYPTO_TRANSCRIPT = "AUTH-SIG#9821-V8-CRYPTO: I hereby authorize high-priority atomic allocation of VIP credentials with sub-millisecond precision execution verified. [NONCE: 0x7f4e91]";

// Circuit Pins Generation (60 precision pins in deterministic serpentine circuit layout)
const CIRCUIT_PINS = [];
const TOTAL_PINS = 60;

function generateCircuitPins() {
  CIRCUIT_PINS.length = 0;
  const cols = 12;
  const rows = 5;
  const startX = 60;
  const startY = 50;
  const spacingX = 68;
  const spacingY = 65;

  let pinId = 1;
  for (let r = 0; r < rows; r++) {
    const isEven = r % 2 === 0;
    for (let c = 0; c < cols; c++) {
      const colIdx = isEven ? c : (cols - 1 - c);
      // Add slight organic jitter to simulate real PCB schematic pads
      const jitterX = ((pinId * 17) % 19) - 9;
      const jitterY = ((pinId * 23) % 15) - 7;
      CIRCUIT_PINS.push({
        id: pinId,
        x: Math.round(startX + colIdx * spacingX + jitterX),
        y: Math.round(startY + r * spacingY + jitterY),
        connected: false
      });
      pinId++;
    }
  }
}

// Signature Path Waypoints Generation (Stage 2)
const SIGNATURE_POINTS = [];
function generateSignaturePath() {
  SIGNATURE_POINTS.length = 0;
  const steps = 60;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    // Lissajous / parametric spline representing a dense security seal signature
    const x = 120 + t * 640;
    const y = 190 + Math.sin(t * Math.PI * 5) * 80 + Math.cos(t * Math.PI * 3) * 35;
    SIGNATURE_POINTS.push({ x: Math.round(x), y: Math.round(y), hit: false });
  }
}

let circuitCanvas, circuitCtx;
let sigCanvas, sigCtx;
let timerInterval = null;
let currentConnectedPin = 0;
let isTracingSig = false;
let sigProgressIndex = 0;

document.addEventListener("DOMContentLoaded", () => {
  generateCircuitPins();
  generateSignaturePath();

  circuitCanvas = document.getElementById("circuit-canvas");
  circuitCtx = circuitCanvas.getContext("2d");

  sigCanvas = document.getElementById("signature-canvas");
  sigCtx = sigCanvas.getContext("2d");

  // DOM buttons
  document.getElementById("start-btn").addEventListener("click", startGauntlet);
  document.getElementById("reset-btn").addEventListener("click", resetGauntlet);
  document.getElementById("modal-restart-btn").addEventListener("click", () => {
    document.getElementById("gauntlet-modal").style.display = "none";
    startGauntlet();
  });
  document.getElementById("modal-close-btn").addEventListener("click", () => {
    document.getElementById("gauntlet-modal").style.display = "none";
  });

  // Setup inputs
  setupCircuitEvents();
  setupSignatureEvents();
  setupWritingEvents();

  // Draw initial idle canvas
  drawCircuit();
  drawSignature();

  // Expose global API for programmatic bot execution & latency benchmarking
  window.__GAUNTLET__ = {
    startGauntlet: startGauntlet,
    resetGauntlet: resetGauntlet,
    getPins: () => CIRCUIT_PINS.map(p => ({ id: p.id, x: p.x, y: p.y })),
    connectPin: (id) => handlePinConnect(id),
    getSignaturePoints: () => SIGNATURE_POINTS.map(p => ({ x: p.x, y: p.y })),
    traceSignaturePoint: (x, y) => handleSignatureMove(x, y),
    finishSignature: () => handleSignatureComplete(),
    getTargetTranscript: () => CRYPTO_TRANSCRIPT,
    writeTranscript: (text) => handleDirectWrite(text),
    getResults: () => ({ ...GAUNTLET_STATE })
  };
});

function logEvent(msg, type = "normal") {
  const logFeed = document.getElementById("gauntlet-log");
  if (!logFeed) return;
  const timeStr = new Date().toISOString().substring(14, 23);
  const div = document.createElement("div");
  div.className = `log-line ${type}`;
  div.innerText = `[${timeStr}] ${msg}`;
  logFeed.prepend(div);
}

function startGauntlet() {
  resetGauntlet();
  GAUNTLET_STATE.active = true;
  GAUNTLET_STATE.startTime = performance.now();
  GAUNTLET_STATE.stage = 1;

  document.getElementById("circuit-overlay").style.display = "none";
  document.getElementById("stage-display").innerText = "STAGE 1: CIRCUIT (0/60)";

  logEvent("▶ The 5-Minute Precision Gauntlet initiated!", "stage");
  logEvent("Stage 1 Armed: Vector Circuit Drawing (Connect 60 pins sequentially)", "system");

  timerInterval = setInterval(() => {
    if (!GAUNTLET_STATE.active) return;
    const elapsedSec = (performance.now() - GAUNTLET_STATE.startTime) / 1000.0;
    document.getElementById("timer-display").innerText = `${elapsedSec.toFixed(3)}s`;
  }, 20);
}

function resetGauntlet() {
  GAUNTLET_STATE.active = false;
  GAUNTLET_STATE.stage = 1;
  GAUNTLET_STATE.stage1Completed = false;
  GAUNTLET_STATE.stage2Completed = false;
  GAUNTLET_STATE.stage3Completed = false;
  GAUNTLET_STATE.actionTimestamps = [];
  currentConnectedPin = 0;
  sigProgressIndex = 0;
  isTracingSig = false;

  clearInterval(timerInterval);
  timerInterval = null;

  document.getElementById("timer-display").innerText = "0.000s";
  document.getElementById("stage-display").innerText = "STAGE 1: CIRCUIT";
  document.getElementById("progress-display").innerText = "0%";
  document.getElementById("speed-display").innerText = "-- ms/action";

  document.getElementById("step-1").className = "step-item active";
  document.getElementById("step-2").className = "step-item";
  document.getElementById("step-3").className = "step-item";

  document.getElementById("stage-1-container").style.display = "flex";
  document.getElementById("stage-2-container").style.display = "none";
  document.getElementById("stage-3-container").style.display = "none";

  document.getElementById("circuit-overlay").style.display = "flex";
  document.getElementById("circuit-overlay").innerText = "Click 'Start Gauntlet' to Arm System";
  document.getElementById("gauntlet-modal").style.display = "none";

  const writingInput = document.getElementById("writing-input");
  writingInput.value = "";
  writingInput.disabled = true;
  document.getElementById("writing-status").innerText = "LOCKED";
  document.getElementById("writing-status").className = "text-amber";

  generateCircuitPins();
  generateSignaturePath();
  drawCircuit();
  drawSignature();
}

/* ---------------- STAGE 1: CIRCUIT DRAWING ---------------- */
function setupCircuitEvents() {
  circuitCanvas.addEventListener("pointerdown", (e) => {
    if (!GAUNTLET_STATE.active || GAUNTLET_STATE.stage !== 1) return;
    const rect = circuitCanvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    // Check hit against pins
    for (const pin of CIRCUIT_PINS) {
      const dist = Math.hypot(pin.x - clickX, pin.y - clickY);
      if (dist <= 16) {
        handlePinConnect(pin.id);
        break;
      }
    }
  });
}

function handlePinConnect(pinId) {
  if (!GAUNTLET_STATE.active || GAUNTLET_STATE.stage !== 1) return;
  const nextTarget = currentConnectedPin + 1;

  if (pinId === nextTarget) {
    const now = performance.now();
    currentConnectedPin = pinId;
    CIRCUIT_PINS[pinId - 1].connected = true;
    GAUNTLET_STATE.actionTimestamps.push(now);

    const progressPct = Math.round((currentConnectedPin / TOTAL_PINS) * 100);
    document.getElementById("progress-display").innerText = `${progressPct}%`;
    document.getElementById("stage-display").innerText = `STAGE 1: PIN ${currentConnectedPin}/${TOTAL_PINS}`;

    if (GAUNTLET_STATE.actionTimestamps.length > 1) {
      const lastActionDelta = now - GAUNTLET_STATE.actionTimestamps[GAUNTLET_STATE.actionTimestamps.length - 2];
      document.getElementById("speed-display").innerText = `${lastActionDelta.toFixed(2)} ms/pin`;
    }

    drawCircuit();

    if (currentConnectedPin === TOTAL_PINS) {
      // Stage 1 Complete!
      const stage1End = performance.now();
      GAUNTLET_STATE.stage1Time = (stage1End - GAUNTLET_STATE.startTime) / 1000.0;
      GAUNTLET_STATE.stage1Completed = true;
      logEvent(`✓ STAGE 1 COMPLETE! 60 Pins connected in ${GAUNTLET_STATE.stage1Time.toFixed(3)}s (Human baseline: 160s)`, "hit");

      advanceToStage2();
    }
  } else {
    logEvent(`Pin #${pinId} out of order! Expected Pin #${nextTarget}`, "error");
  }
}

function drawCircuit() {
  if (!circuitCtx) return;
  circuitCtx.clearRect(0, 0, circuitCanvas.width, circuitCanvas.height);

  // Background grid
  circuitCtx.strokeStyle = "#162238";
  circuitCtx.lineWidth = 1;
  for (let x = 0; x < circuitCanvas.width; x += 30) {
    circuitCtx.beginPath();
    circuitCtx.moveTo(x, 0);
    circuitCtx.lineTo(x, circuitCanvas.height);
    circuitCtx.stroke();
  }
  for (let y = 0; y < circuitCanvas.height; y += 30) {
    circuitCtx.beginPath();
    circuitCtx.moveTo(0, y);
    circuitCtx.lineTo(circuitCanvas.width, y);
    circuitCtx.stroke();
  }

  // Draw connected traces (glowing cyan lines)
  if (currentConnectedPin > 1) {
    circuitCtx.strokeStyle = "#00f0ff";
    circuitCtx.lineWidth = 3;
    circuitCtx.shadowColor = "#00f0ff";
    circuitCtx.shadowBlur = 10;
    circuitCtx.beginPath();
    circuitCtx.moveTo(CIRCUIT_PINS[0].x, CIRCUIT_PINS[0].y);
    for (let i = 1; i < currentConnectedPin; i++) {
      circuitCtx.lineTo(CIRCUIT_PINS[i].x, CIRCUIT_PINS[i].y);
    }
    circuitCtx.stroke();
    circuitCtx.shadowBlur = 0;
  }

  // Draw pins
  for (const pin of CIRCUIT_PINS) {
    circuitCtx.beginPath();
    circuitCtx.arc(pin.x, pin.y, 10, 0, Math.PI * 2);

    if (pin.connected) {
      circuitCtx.fillStyle = "#00ff88";
      circuitCtx.fill();
    } else if (pin.id === currentConnectedPin + 1) {
      circuitCtx.fillStyle = "#ffb800";
      circuitCtx.fill();
      circuitCtx.lineWidth = 2;
      circuitCtx.strokeStyle = "#fff";
      circuitCtx.stroke();
    } else {
      circuitCtx.fillStyle = "#2a3a5e";
      circuitCtx.fill();
      circuitCtx.lineWidth = 1;
      circuitCtx.strokeStyle = "#475569";
      circuitCtx.stroke();
    }

    // Pin number label
    circuitCtx.fillStyle = pin.connected ? "#000" : "#fff";
    circuitCtx.font = "9px JetBrains Mono, monospace";
    circuitCtx.textAlign = "center";
    circuitCtx.textBaseline = "middle";
    circuitCtx.fillText(pin.id, pin.x, pin.y);
  }
}

/* ---------------- STAGE 2: CONTINUOUS VECTOR SIGNATURE ---------------- */
function advanceToStage2() {
  GAUNTLET_STATE.stage = 2;
  document.getElementById("step-1").className = "step-item completed";
  document.getElementById("step-2").className = "step-item active";

  document.getElementById("stage-1-container").style.display = "none";
  document.getElementById("stage-2-container").style.display = "flex";
  document.getElementById("stage-display").innerText = "STAGE 2: SIGNATURE TRACE";
  document.getElementById("progress-display").innerText = "0%";

  logEvent("Stage 2 Armed: Continuous Vector Waveform / Signature Tracing", "stage");
  drawSignature();
}

function setupSignatureEvents() {
  sigCanvas.addEventListener("pointerdown", (e) => {
    if (!GAUNTLET_STATE.active || GAUNTLET_STATE.stage !== 2) return;
    const rect = sigCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Must start near point 0
    const startPt = SIGNATURE_POINTS[0];
    if (Math.hypot(startPt.x - x, startPt.y - y) <= 25) {
      isTracingSig = true;
      sigProgressIndex = 0;
      handleSignatureMove(x, y);
    }
  });

  sigCanvas.addEventListener("pointermove", (e) => {
    if (!isTracingSig) return;
    const rect = sigCanvas.getBoundingClientRect();
    handleSignatureMove(e.clientX - rect.left, e.clientY - rect.top);
  });

  sigCanvas.addEventListener("pointerup", () => {
    if (isTracingSig) {
      isTracingSig = false;
      if (sigProgressIndex < SIGNATURE_POINTS.length - 1) {
        logEvent("Pointer lifted before curve completion! Re-trace from start.", "error");
        sigProgressIndex = 0;
        drawSignature();
      }
    }
  });
}

function handleSignatureMove(x, y) {
  if (!GAUNTLET_STATE.active || GAUNTLET_STATE.stage !== 2) return;

  // Advance through points
  while (sigProgressIndex < SIGNATURE_POINTS.length) {
    const pt = SIGNATURE_POINTS[sigProgressIndex];
    const dist = Math.hypot(pt.x - x, pt.y - y);
    if (dist <= 30) {
      pt.hit = true;
      sigProgressIndex++;
    } else {
      break;
    }
  }

  const progressPct = Math.round((sigProgressIndex / SIGNATURE_POINTS.length) * 100);
  document.getElementById("progress-display").innerText = `${progressPct}%`;
  drawSignature();

  if (sigProgressIndex >= SIGNATURE_POINTS.length) {
    handleSignatureComplete();
  }
}

function handleSignatureComplete() {
  if (GAUNTLET_STATE.stage !== 2) return;
  const now = performance.now();
  GAUNTLET_STATE.stage2Time = (now - GAUNTLET_STATE.startTime) / 1000.0 - GAUNTLET_STATE.stage1Time;
  GAUNTLET_STATE.stage2Completed = true;
  logEvent(`✓ STAGE 2 COMPLETE! Vector signature verified in ${GAUNTLET_STATE.stage2Time.toFixed(3)}s (Human baseline: 50s)`, "hit");

  advanceToStage3();
}

function drawSignature() {
  if (!sigCtx) return;
  sigCtx.clearRect(0, 0, sigCanvas.width, sigCanvas.height);

  // Guide spline (dim purple)
  sigCtx.strokeStyle = "#432b68";
  sigCtx.lineWidth = 8;
  sigCtx.lineCap = "round";
  sigCtx.lineJoin = "round";
  sigCtx.beginPath();
  sigCtx.moveTo(SIGNATURE_POINTS[0].x, SIGNATURE_POINTS[0].y);
  for (let i = 1; i < SIGNATURE_POINTS.length; i++) {
    sigCtx.lineTo(SIGNATURE_POINTS[i].x, SIGNATURE_POINTS[i].y);
  }
  sigCtx.stroke();

  // Completed traced spline (bright glowing purple/cyan)
  if (sigProgressIndex > 0) {
    sigCtx.strokeStyle = "#9d4edd";
    sigCtx.lineWidth = 4;
    sigCtx.shadowColor = "#c77dff";
    sigCtx.shadowBlur = 12;
    sigCtx.beginPath();
    sigCtx.moveTo(SIGNATURE_POINTS[0].x, SIGNATURE_POINTS[0].y);
    for (let i = 1; i < sigProgressIndex; i++) {
      sigCtx.lineTo(SIGNATURE_POINTS[i].x, SIGNATURE_POINTS[i].y);
    }
    sigCtx.stroke();
    sigCtx.shadowBlur = 0;
  }

  // Draw Start & Finish Markers
  const startPt = SIGNATURE_POINTS[0];
  const endPt = SIGNATURE_POINTS[SIGNATURE_POINTS.length - 1];

  sigCtx.fillStyle = "#00ff88";
  sigCtx.beginPath();
  sigCtx.arc(startPt.x, startPt.y, 8, 0, Math.PI * 2);
  sigCtx.fill();

  sigCtx.fillStyle = "#ff3366";
  sigCtx.beginPath();
  sigCtx.arc(endPt.x, endPt.y, 8, 0, Math.PI * 2);
  sigCtx.fill();

  sigCtx.fillStyle = "#fff";
  sigCtx.font = "11px JetBrains Mono, monospace";
  sigCtx.fillText("START", startPt.x, startPt.y - 14);
  sigCtx.fillText("FINISH", endPt.x, endPt.y - 14);
}

/* ---------------- STAGE 3: CRYPTOGRAPHIC WRITING ---------------- */
function advanceToStage3() {
  GAUNTLET_STATE.stage = 3;
  document.getElementById("step-2").className = "step-item completed";
  document.getElementById("step-3").className = "step-item active";

  document.getElementById("stage-2-container").style.display = "none";
  document.getElementById("stage-3-container").style.display = "flex";
  document.getElementById("stage-display").innerText = "STAGE 3: CRYPTO SPEED WRITING";
  document.getElementById("progress-display").innerText = "0%";

  const transcriptBox = document.getElementById("target-transcript");
  transcriptBox.innerText = CRYPTO_TRANSCRIPT;

  const writingInput = document.getElementById("writing-input");
  writingInput.disabled = false;
  writingInput.placeholder = "Type or inject exact cryptographic clause here...";
  writingInput.focus();

  document.getElementById("writing-chars").innerText = `0 / ${CRYPTO_TRANSCRIPT.length}`;
  document.getElementById("writing-status").innerText = "ACTIVE";
  document.getElementById("writing-status").className = "text-cyan";

  logEvent("Stage 3 Armed: Cryptographic Legal Transcript Verification (Exact match required)", "stage");
}

function setupWritingEvents() {
  const writingInput = document.getElementById("writing-input");
  writingInput.addEventListener("input", () => {
    handleDirectWrite(writingInput.value);
  });
}

function handleDirectWrite(typedText) {
  if (!GAUNTLET_STATE.active || GAUNTLET_STATE.stage !== 3) return;
  const writingInput = document.getElementById("writing-input");
  if (writingInput.value !== typedText) {
    writingInput.value = typedText;
  }

  const target = CRYPTO_TRANSCRIPT;
  let matches = 0;
  for (let i = 0; i < typedText.length && i < target.length; i++) {
    if (typedText[i] === target[i]) matches++;
  }

  const accuracy = typedText.length > 0 ? Math.round((matches / typedText.length) * 100) : 0;
  const progress = Math.min(100, Math.round((matches / target.length) * 100));

  document.getElementById("writing-accuracy").innerText = `${accuracy}%`;
  document.getElementById("writing-chars").innerText = `${matches} / ${target.length}`;
  document.getElementById("progress-display").innerText = `${progress}%`;

  if (typedText === target) {
    // Stage 3 Complete!
    const finishTime = performance.now();
    GAUNTLET_STATE.stage3Time = (finishTime - GAUNTLET_STATE.startTime) / 1000.0 - GAUNTLET_STATE.stage1Time - GAUNTLET_STATE.stage2Time;
    GAUNTLET_STATE.totalTime = (finishTime - GAUNTLET_STATE.startTime) / 1000.0;
    GAUNTLET_STATE.stage3Completed = true;
    GAUNTLET_STATE.active = false;
    clearInterval(timerInterval);

    document.getElementById("step-3").className = "step-item completed";
    document.getElementById("writing-status").innerText = "VERIFIED";
    document.getElementById("writing-status").className = "text-green";
    document.getElementById("progress-display").innerText = "100%";
    writingInput.disabled = true;

    logEvent(`✓ STAGE 3 COMPLETE! Cryptographic writing verified in ${GAUNTLET_STATE.stage3Time.toFixed(3)}s (Human baseline: 90s)`, "hit");
    logEvent(`🏁 GAUNTLET COMPLETE! Total Time: ${GAUNTLET_STATE.totalTime.toFixed(3)}s`, "system");

    showFinalScorecard();
  }
}

function showFinalScorecard() {
  const humanEquivalentSec = 300.0; // 5.0 minutes
  const speedup = (humanEquivalentSec / GAUNTLET_STATE.totalTime).toFixed(1);

  document.getElementById("final-total-time").innerText = `${GAUNTLET_STATE.totalTime.toFixed(3)}s`;
  document.getElementById("final-stage1-time").innerText = `${GAUNTLET_STATE.stage1Time.toFixed(3)}s`;
  document.getElementById("final-stage2-time").innerText = `${GAUNTLET_STATE.stage2Time.toFixed(3)}s`;
  document.getElementById("final-stage3-time").innerText = `${GAUNTLET_STATE.stage3Time.toFixed(3)}s`;
  document.getElementById("final-speedup").innerText = `${speedup}× FASTER`;

  document.getElementById("gauntlet-modal").style.display = "flex";
}
