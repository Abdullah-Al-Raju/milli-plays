// Milli-Booker Interactive Front-End Controller
let selectedSeatId = null;
let currentEventId = "grand-concert-2026";
let queueToken = null;

document.addEventListener("DOMContentLoaded", () => {
  initUI();
  fetchSeats();
  startClock();
  startPolling();
});

function initUI() {
  // Cookie dismissal
  const cookieBanner = document.getElementById("cookie-consent-modal");
  const acceptBtn = document.getElementById("accept-cookies");
  if (acceptBtn) {
    acceptBtn.addEventListener("click", () => {
      cookieBanner.style.display = "none";
    });
  }

  // Booking buttons
  const confirmBtn = document.getElementById("confirm-booking");
  const bookNowBtn = document.getElementById("book-now-btn");
  if (confirmBtn) confirmBtn.addEventListener("click", handleBooking);
  if (bookNowBtn) bookNowBtn.addEventListener("click", handleBooking);

  // Reset button
  const resetBtn = document.getElementById("reset-btn");
  if (resetBtn) resetBtn.addEventListener("click", handleReset);
}

async function fetchSeats() {
  try {
    const res = await fetch(`/api/seats/${currentEventId}`);
    const data = await res.json();
    renderSeats(data.seats);
    updateStats(data);
  } catch (err) {
    console.error("Failed to fetch seats:", err);
  }
}

function renderSeats(seats) {
  const grid = document.getElementById("seat-grid");
  if (!grid) return;
  grid.innerHTML = "";

  seats.forEach(seat => {
    const div = document.createElement("div");
    div.id = `seat-${seat.id.toLowerCase()}`;
    div.className = `seat seat-${seat.status}`;
    div.innerText = seat.id;
    div.dataset.seatId = seat.id;

    if (seat.status === "available") {
      div.addEventListener("click", () => selectSeat(seat.id));
    }

    grid.appendChild(div);
  });
}

function selectSeat(seatId) {
  selectedSeatId = seatId;
  document.getElementById("selected-seat-label").innerText = seatId;

  // Highlight in DOM
  document.querySelectorAll(".seat").forEach(el => {
    if (el.dataset.seatId === seatId) {
      el.classList.add("seat-selected");
    } else {
      el.classList.remove("seat-selected");
    }
  });

  const confirmBtn = document.getElementById("confirm-booking");
  const bookNowBtn = document.getElementById("book-now-btn");
  if (confirmBtn) confirmBtn.disabled = false;
  if (bookNowBtn) bookNowBtn.disabled = false;
}

async function handleBooking() {
  if (!selectedSeatId) return;

  const t0 = performance.now();
  const clientId = "human-browser-" + Math.floor(Math.random() * 1000);

  try {
    // 1. Join queue if token not present
    if (!queueToken) {
      const qRes = await fetch("/api/queue/join", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: clientId })
      });
      const qData = await qRes.json();
      queueToken = qData.token;
    }

    // 2. Submit atomic booking
    const res = await fetch("/api/book", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_id: currentEventId,
        seat_id: selectedSeatId,
        client_id: clientId,
        client_type: "human_browser",
        queue_token: queueToken
      })
    });

    const elapsedMs = (performance.now() - t0).toFixed(2);
    const result = await res.json();

    if (result.success) {
      logEvent(`🏆 [SUCCESS] Booked Seat ${selectedSeatId} in ${elapsedMs} ms`, "book-success");
      document.getElementById("metric-latency").innerText = `${elapsedMs} ms`;
      document.getElementById("metric-winner").innerText = clientId;
      document.getElementById("metric-method").innerText = "Human DOM Click";
      selectedSeatId = null;
      document.getElementById("selected-seat-label").innerText = "None";
      document.getElementById("confirm-booking").disabled = true;
    } else {
      logEvent(`❌ [FAILED] Seat ${selectedSeatId}: ${result.error}`, "book-failed");
    }

    fetchSeats();
  } catch (err) {
    logEvent(`⚠️ Booking error: ${err.message}`, "book-failed");
  }
}

async function handleReset() {
  try {
    await fetch("/api/admin/reset", { method: "POST" });
    logEvent("↺ Arena and seat inventory reset by admin.", "system");
    queueToken = null;
    selectedSeatId = null;
    document.getElementById("selected-seat-label").innerText = "None";
    document.getElementById("confirm-booking").disabled = true;
    fetchSeats();
  } catch (err) {
    console.error("Reset failed:", err);
  }
}

function updateStats(data) {
  const availableCount = data.seats.filter(s => s.status === "available").length;
  const countEl = document.getElementById("seats-count");
  if (countEl) countEl.innerText = `${availableCount} / ${data.seats.length}`;

  const statusEl = document.getElementById("drop-status");
  if (statusEl) {
    if (availableCount === 0) {
      statusEl.innerText = "SOLD OUT";
      statusEl.className = "stat-value text-red";
    } else {
      statusEl.innerText = "LIVE";
      statusEl.className = "stat-value text-green";
    }
  }
}

function logEvent(message, type = "normal") {
  const logFeed = document.getElementById("telemetry-log");
  if (!logFeed) return;

  const item = document.createElement("div");
  const timeStr = new Date().toISOString().substring(11, 23);
  item.className = `log-item ${type}`;
  item.innerText = `[${timeStr}] ${message}`;

  logFeed.prepend(item);
}

function startClock() {
  const clockEl = document.getElementById("server-clock");
  setInterval(() => {
    if (clockEl) {
      const now = new Date();
      clockEl.innerText = now.toISOString().substring(11, 23);
    }
  }, 50);
}

function startPolling() {
  setInterval(fetchSeats, 1000);
}
