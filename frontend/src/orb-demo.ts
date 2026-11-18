// Standalone orb demo: no server, no mic. A stand-in "analyser" gives the
// speaking state a speech-shaped pulse so the orb can be seen as it is in the app.
import { createOrb, type OrbState } from "./orb";

const canvas = document.getElementById("orb") as HTMLCanvasElement;
const orb = createOrb(canvas);

const BINS = 128;
const fakeAnalyser = {
  frequencyBinCount: BINS,
  getByteFrequencyData(out: Uint8Array) {
    const t = performance.now() / 1000;
    // Phrases of about 1.6 s with short pauses, each with a syllable flutter.
    const phrase = Math.max(0, Math.sin((t % 2.2) / 1.6 * Math.PI));
    const syll = 0.6 + 0.4 * Math.abs(Math.sin(t * 9.0));
    const level = (t % 2.2) < 1.6 ? phrase * syll : 0;
    for (let i = 0; i < out.length; i++) out[i] = Math.round(255 * level * Math.exp(-i / 40));
  },
} as unknown as AnalyserNode;

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function setState(s: OrbState) {
  orb.setState(s);
  orb.setAnalyser(s === "speaking" && !reduceMotion ? fakeAnalyser : null);
  document.querySelectorAll<HTMLButtonElement>("button[data-state]").forEach((b) =>
    b.setAttribute("aria-pressed", String(b.dataset.state === s)));
}

document.querySelectorAll<HTMLButtonElement>("button[data-state]").forEach((b) =>
  b.addEventListener("click", () => setState(b.dataset.state as OrbState)));
setState(reduceMotion ? "idle" : "speaking");
