// ── State ─────────────────────────────────────────────────────────────
let lastSign        = "";
let lastSentence    = "";
let holdProgress    = 0;
let sameSignFrames  = 0;

// ── DOM refs ──────────────────────────────────────────────────────────
const statusChip   = document.getElementById("statusChip");
const statusDot    = document.getElementById("statusDot");
const statusTxt    = document.getElementById("statusTxt");
const signWord     = document.getElementById("signWord");
const signCard     = document.getElementById("signCard");
const confPct      = document.getElementById("confPct");
const confCircle   = document.getElementById("confCircle");
const outputText   = document.getElementById("outputText");
const outputTags   = document.getElementById("outputTags");
const wordCount    = document.getElementById("wordCount");
const noHand       = document.getElementById("noHand");
const holdRing     = document.getElementById("holdRing");
const ringCircle   = document.getElementById("ringCircle");
const fpsVal       = document.getElementById("fpsVal");
const totalVal     = document.getElementById("totalVal");

// Confidence ring circumference = 2π × 32 ≈ 201
const CONF_CIRC = 201;
// Hold ring circumference = 2π × 24 ≈ 150.8
const HOLD_CIRC = 150.8;
// Frames to auto-add = 25 (set in app.py), track on frontend for progress bar
const HOLD_FRAMES = 25;

// ── Poll backend every 150ms ──────────────────────────────────────────
async function pollState() {
  try {
    const res  = await fetch("/get_state");
    const data = await res.json();

    updateStatus(data);
    updateSign(data);
    updateConfidence(data);
    updateSentence(data);
    updateStats(data);

  } catch (err) {
    console.error("Poll error:", err);
  }
}

// ── Status pill ───────────────────────────────────────────────────────
function updateStatus(data) {
  if (!data.model_loaded) {
    statusTxt.textContent = "No Model";
    statusChip.classList.remove("active");
    return;
  }
  if (data.hand_detected) {
    statusChip.classList.add("active");
    statusTxt.textContent = "Hand Detected";
    noHand.classList.add("hidden");
    holdRing.classList.add("visible");
  } else {
    statusChip.classList.remove("active");
    statusTxt.textContent = "No Hand";
    noHand.classList.remove("hidden");
    holdRing.classList.remove("visible");
    // reset hold ring
    ringCircle.style.strokeDashoffset = HOLD_CIRC;
    sameSignFrames = 0;
  }
}

// ── Detected sign + hold ring ─────────────────────────────────────────
function updateSign(data) {
  const sign = data.current_sign || "";

  if (sign !== lastSign) {
    // New sign — animate pop
    signWord.classList.remove("pop");
    void signWord.offsetWidth; // reflow
    signWord.classList.add("pop");
    setTimeout(() => signWord.classList.remove("pop"), 200);

    // Highlight gesture chip
    if (lastSign) {
      const oldChip = document.getElementById("chip-" + lastSign.replace(/ /g, "_"));
      if (oldChip) oldChip.classList.remove("active");
    }
    if (sign) {
      const newChip = document.getElementById("chip-" + sign.replace(/ /g, "_"));
      if (newChip) newChip.classList.add("active");
    }

    lastSign       = sign;
    sameSignFrames = 0;
  } else if (sign) {
    sameSignFrames++;
  }

  signWord.textContent = sign || "—";
  signCard.classList.toggle("active", !!sign);

  // Hold ring progress (25 frames = full)
  if (sign && data.hand_detected) {
    const progress = Math.min(sameSignFrames / HOLD_FRAMES, 1);
    const offset   = HOLD_CIRC * (1 - progress);
    ringCircle.style.strokeDashoffset = offset;
  }
}

// ── Confidence ring ───────────────────────────────────────────────────
function updateConfidence(data) {
  const conf   = data.confidence || 0;
  const offset = CONF_CIRC * (1 - conf / 100);
  confCircle.style.strokeDashoffset = offset;
  confCircle.style.transition = "stroke-dashoffset 0.4s ease";
  confPct.textContent = conf + "%";
}

// ── Sentence + word tags ──────────────────────────────────────────────
function updateSentence(data) {
  const sentence  = data.sentence || "";
  const wordList  = data.word_list || [];

  if (sentence === lastSentence) return;
  lastSentence = sentence;

  // Main text display
  if (sentence.trim()) {
    outputText.innerHTML = `<span>${sentence}</span><span class="cursor-blink">|</span>`;
  } else {
    outputText.innerHTML = `<span class="placeholder">Your sentence will appear here as you sign...</span>`;
  }

  // Word tag chips
  outputTags.innerHTML = "";
  wordList.forEach(w => {
    const tag = document.createElement("div");
    if (w === "|space|") {
      tag.className    = "word-tag space-tag";
      tag.textContent  = "[ space ]";
    } else {
      tag.className   = "word-tag";
      tag.textContent = w;
    }
    outputTags.appendChild(tag);
  });

  // Word count
  const realWords = wordList.filter(w => w !== "|space|");
  wordCount.textContent = realWords.length;
}

// ── Stats ─────────────────────────────────────────────────────────────
function updateStats(data) {
  fpsVal.textContent   = data.fps   || 0;
  totalVal.textContent = data.total_detected || 0;
}

// ── Control buttons ───────────────────────────────────────────────────
async function clearSentence() {
  await fetch("/clear_sentence", { method: "POST" });
  sameSignFrames = 0;
  lastSentence   = "__force_refresh__";
}

async function addSpace() {
  await fetch("/add_space", { method: "POST" });
  lastSentence = "__force_refresh__";
}

async function deleteLast() {
  await fetch("/delete_last", { method: "POST" });
  lastSentence = "__force_refresh__";
}

async function copyText() {
  const text = document.querySelector("#outputText span")?.textContent || "";
  if (!text || text === "Your sentence will appear here as you sign...") return;

  try {
    await navigator.clipboard.writeText(text);
    const btn = document.querySelector(".copy-btn");
    const orig = btn.innerHTML;
    btn.textContent = "✓ COPIED";
    btn.style.color = "var(--accent)";
    btn.style.borderColor = "rgba(0,229,160,0.5)";
    setTimeout(() => {
      btn.innerHTML = orig;
      btn.style.color = "";
      btn.style.borderColor = "";
    }, 1500);
  } catch (e) {
    console.error("Copy failed:", e);
  }
}

// ── Cursor blink style ────────────────────────────────────────────────
const style = document.createElement("style");
style.textContent = `
  .cursor-blink {
    display: inline-block;
    color: var(--accent);
    animation: cur-blink 1s step-end infinite;
    margin-left: 1px;
    font-weight: 300;
  }
  @keyframes cur-blink {
    0%,100% { opacity: 1; }
    50%      { opacity: 0; }
  }
`;
document.head.appendChild(style);

// ── Start polling ─────────────────────────────────────────────────────
setInterval(pollState, 150);
pollState();
