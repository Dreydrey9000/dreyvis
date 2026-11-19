// Dreyvis ears. Electron's built-in SpeechRecognition refuses to run, so this
// replaces it with one that records the mic, cuts it into phrases when you
// pause, and sends each phrase to Dreyvis's local Whisper (/api/transcribe).
// The page's voice code is unchanged: it sees the same events Chrome fires.
//
// The page restarts its recogniser every few seconds (Chrome needs that), so
// the mic and the phrase cutter live in ONE shared engine that stays open.
// A recogniser object only subscribes to it; stopping one never drops a phrase.
const { ipcRenderer } = require("electron");

const RATE = 16000;
const FRAME = 2048;                 // 128 ms per audio frame
const FRAME_MS = (FRAME / RATE) * 1000;
const END_SILENCE_MS = 800;         // a pause this long ends a phrase
const MAX_PHRASE_MS = 15000;
const PREROLL_FRAMES = 3;           // keep ~0.4 s before speech starts

const state = { muted: false, level: 0, noise: 0.01, phrasesSent: 0, lastText: "", lastError: "" };
const mutedListeners = new Set();
ipcRenderer.on("dreyvis:muted", (_e, value) => {
  state.muted = !!value;
  mutedListeners.forEach((fn) => fn(state.muted));
});

function fire(target, name, extra) {
  const ev = Object.assign(new Event(name), extra || {});
  const handler = target["on" + name];
  if (typeof handler === "function") handler.call(target, ev);
}

function rms(buf) {
  let s = 0;
  for (let i = 0; i < buf.length; i++) s += buf[i] * buf[i];
  return Math.sqrt(s / buf.length);
}

// ── The shared engine: one mic, one phrase cutter ──
const engine = {
  opening: null,
  subscriber: null,          // the recogniser currently running, if any
  frames: [],
  preroll: [],
  inSpeech: false,
  silentMs: 0,

  open() {
    if (!this.opening) {
      this.opening = navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      }).then((stream) => {
        const ctx = new AudioContext({ sampleRate: RATE });
        const src = ctx.createMediaStreamSource(stream);
        const node = ctx.createScriptProcessor(FRAME, 1, 1);
        node.onaudioprocess = (e) => this.onFrame(new Float32Array(e.inputBuffer.getChannelData(0)));
        src.connect(node);
        node.connect(ctx.destination);
        this.keep = { stream, ctx, src, node };   // held so nothing is garbage-collected
      }).catch((e) => { this.opening = null; throw e; });
    }
    return this.opening;
  },

  onFrame(frame) {
    const level = rms(frame);
    state.level = level;
    if (state.muted || !this.subscriber) {        // nobody listening: drop audio, forget any half phrase
      this.inSpeech = false;
      this.frames = [];
      this.preroll = [];
      return;
    }
    if (!this.inSpeech) state.noise = state.noise * 0.95 + level * 0.05;   // the room's background
    const loud = level > Math.max(0.015, state.noise * 3);
    if (!this.inSpeech) {
      this.preroll.push(frame);
      if (this.preroll.length > PREROLL_FRAMES) this.preroll.shift();
      if (loud) {
        this.inSpeech = true;
        this.silentMs = 0;
        this.frames = this.preroll.slice();
        this.preroll = [];
        fire(this.subscriber, "speechstart");
      }
      return;
    }
    this.frames.push(frame);
    this.silentMs = loud ? 0 : this.silentMs + FRAME_MS;
    if (this.silentMs >= END_SILENCE_MS || this.frames.length * FRAME_MS >= MAX_PHRASE_MS) {
      const phrase = this.frames;
      this.frames = [];
      this.inSpeech = false;
      this.send(phrase);
    }
  },

  async send(frames) {
    if (frames.length * FRAME < RATE * 0.4) return;   // under 0.4 s: a click, not speech
    const pcm = new Float32Array(frames.length * FRAME);
    frames.forEach((f, i) => pcm.set(f, i * FRAME));
    state.phrasesSent++;
    let text = "";
    try {
      const res = await fetch("/api/transcribe", {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: pcm.buffer,
      });
      if (!res.ok) throw new Error("transcribe " + res.status);
      text = ((await res.json()).text || "").trim();
    } catch (e) {
      state.lastError = String(e);
      return;
    }
    state.lastText = text;
    if (!text) return;
    // Deliver to whichever recogniser is running now (the page may have rotated while Whisper worked).
    let target = this.subscriber;
    for (let i = 0; !target && i < 20; i++) {
      await new Promise((r) => setTimeout(r, 100));
      target = this.subscriber;
    }
    if (target) target._deliver(text);
  },
};

class DreyvisSpeechRecognition {
  constructor() {
    this.continuous = false;
    this.interimResults = false;
    this.lang = "en-US";
    this.maxAlternatives = 1;
    this._running = false;
  }

  async start() {
    if (this._running) throw new DOMException("already started", "InvalidStateError");
    this._running = true;
    try {
      await engine.open();
    } catch (e) {
      this._running = false;
      state.lastError = String(e);
      fire(this, "error", { error: "not-allowed", message: String(e) });
      fire(this, "end");
      return;
    }
    if (!this._running) return;                  // stopped while the mic was opening
    engine.subscriber = this;
    fire(this, "start");
    fire(this, "audiostart");
  }

  _deliver(text) {
    if (!this._running) return;
    const alt = { transcript: text, confidence: 0.9 };
    const result = Object.assign([alt], { isFinal: true, item: (i) => [alt][i] });
    const results = Object.assign([result], { item: (i) => [result][i] });
    fire(this, "result", { resultIndex: 0, results });
    if (!this.continuous) this.stop();
  }

  _detach() {
    this._running = false;
    if (engine.subscriber === this) engine.subscriber = null;
  }

  stop() {
    if (!this._running) return;
    this._detach();
    fire(this, "audioend");
    fire(this, "end");
  }

  abort() {
    if (!this._running) return;
    this._detach();
    fire(this, "error", { error: "aborted" });
    fire(this, "end");
  }
}

// A button to switch between the orb and Ethan's dashboard (runs, sessions, memory,
// specs, projects, usage), placed clear of the window's traffic-light buttons.
window.addEventListener("DOMContentLoaded", () => {
  const onDashboard = location.pathname.startsWith("/dashboard");
  const onOrb = location.pathname === "/";
  // The orb gets Dashboard + Connectors; every other page gets a way back to the orb.
  const links = onOrb
    ? [["Dashboard", "dashboard", "Open the dashboard (Cmd+2)"], ["Connectors", "connectors", "Connect apps (Cmd+3)"]]
    : [["Orb", "", "Back to the orb (Cmd+1)"]];
  const bar = document.createElement("div");
  Object.assign(bar.style, {
    position: "fixed", zIndex: "2147483647", display: "flex", gap: "8px",
    ...(onDashboard ? { right: "16px", bottom: "16px" } : { left: "88px", top: "16px" }),
  });
  for (const [label, page, title] of links) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.title = title;
    b.setAttribute("aria-label", title);
    // Aurora Glass pills, matching the Connectors page (THEME-DECISION.md).
    Object.assign(b.style, {
      font: "600 14px Sora, -apple-system, BlinkMacSystemFont, sans-serif",
      color: "#e8eefc", background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.22)",
      borderRadius: "999px", padding: "0 16px", height: "36px", cursor: "pointer",
      backdropFilter: "blur(20px) saturate(140%)", webkitBackdropFilter: "blur(20px) saturate(140%)",
      boxShadow: "0 8px 24px rgba(0,0,0,0.25)", transition: "background .2s, border-color .2s",
    });
    b.addEventListener("mouseenter", () => { b.style.background = "rgba(255,255,255,0.16)"; b.style.borderColor = "rgba(90,160,255,0.7)"; });
    b.addEventListener("mouseleave", () => { b.style.background = "rgba(255,255,255,0.08)"; b.style.borderColor = "rgba(255,255,255,0.22)"; });
    b.addEventListener("focus", () => { b.style.outline = "2px solid #5aa0ff"; b.style.outlineOffset = "2px"; });
    b.addEventListener("blur", () => { b.style.outline = "none"; });
    b.addEventListener("click", () => ipcRenderer.send("dreyvis:show", page));
    bar.appendChild(b);
  }
  document.body.appendChild(bar);
});

// Load Whisper now with a quiet half second, so the first real phrase isn't a 30 second wait.
window.addEventListener("load", () => {
  fetch("/api/transcribe", { method: "POST", headers: { "Content-Type": "application/octet-stream" },
    body: new Float32Array(RATE / 2).buffer }).catch(() => {});
});

window.SpeechRecognition = DreyvisSpeechRecognition;
window.webkitSpeechRecognition = DreyvisSpeechRecognition;
window.dreyvis = { onMuted: (fn) => mutedListeners.add(fn), isMuted: () => state.muted, debug: () => ({ ...state }),
  // Test hook: hand the phrase cutter a recorded clip (float32 16 kHz) as if it came from the mic.
  testPhrase: (pcm) => {
    const frames = [];
    for (let i = 0; i < pcm.length; i += FRAME) { const f = new Float32Array(FRAME); f.set(pcm.subarray(i, i + FRAME)); frames.push(f); }
    return engine.send(frames);
  } };
