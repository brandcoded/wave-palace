"use client";

import { useEffect, useRef } from "react";
import type { RefObject } from "react";

export type VisualizerStyle = "none" | "waveform" | "bars" | "circular" | "blob" | "terrain";
export type VisualizerTheme = "violet" | "teal" | "ember" | "rose" | "ice" | "frequency";

const THEME_HEX: Record<VisualizerTheme, string> = {
  violet:    "#a78bfa",
  teal:      "#2dd4bf",
  ember:     "#fb923c",
  rose:      "#fb7185",
  ice:       "#bae6fd",
  frequency: "#ffffff", // unused — per-bin gradient applied inline
};

function freqColor(i: number, total: number): string {
  const t = i / total;
  if (t < 0.5) {
    const tt = t * 2;
    return `rgb(${Math.round(239 * (1 - tt))},${Math.round(34 + 163 * tt)},${Math.round(68 * (1 - tt) + 68 * tt)})`;
  }
  const tt = (t - 0.5) * 2;
  return `rgb(${Math.round(34 * (1 - tt))},${Math.round(197 * (1 - tt))},${Math.round(68 + 182 * tt)})`;
}

function smoothFreq(raw: Uint8Array): Float32Array {
  const n = raw.length;
  const out = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const prev = i > 0 ? raw[i - 1] : raw[i];
    const next = i < n - 1 ? raw[i + 1] : raw[i];
    out[i] = prev * 0.2 + raw[i] * 0.6 + next * 0.2;
  }
  return out;
}

// Log-spaced x coordinate: compresses high-freq bins so bass is more visible.
function logX(i: number, n: number, W: number): number {
  return W * Math.log(1 + i) / Math.log(1 + n);
}

export function useAudioVisualizer(
  audioRef: RefObject<HTMLAudioElement>,
  canvasRef: RefObject<HTMLCanvasElement>,
  style: VisualizerStyle,
  theme: VisualizerTheme,
  _playing: boolean,
) {
  const acRef  = useRef<AudioContext | null>(null);
  const anRef  = useRef<AnalyserNode | null>(null);
  const srcRef = useRef<MediaElementAudioSourceNode | null>(null);
  const rafRef = useRef<number>(0);
  const peakRef    = useRef<Float32Array | null>(null);
  const peakVelRef = useRef<Float32Array | null>(null);

  // Wire AudioContext on first play (user-gesture gated by browser).
  useEffect(() => {
    if (style === "none") return;
    const audio = audioRef.current;
    if (!audio) return;

    function setup() {
      if (acRef.current) {
        if (acRef.current.state === "suspended") acRef.current.resume().catch(() => {});
        return;
      }
      try {
        const ac = new AudioContext();
        const an = ac.createAnalyser();
        an.fftSize = 2048;
        an.smoothingTimeConstant = 0.88;
        const src = ac.createMediaElementSource(audio!);
        src.connect(an);
        an.connect(ac.destination);
        acRef.current  = ac;
        anRef.current  = an;
        srcRef.current = src;
      } catch {
        // Silently fail — never interrupt playback
      }
    }

    audio.addEventListener("play", setup);
    return () => audio.removeEventListener("play", setup);
  }, [audioRef, style]);

  // Animation loop — runs whenever style !== "none".
  useEffect(() => {
    cancelAnimationFrame(rafRef.current);

    const canvas = canvasRef.current;
    if (!canvas || style === "none") {
      if (canvas) {
        const c = canvas.getContext("2d");
        c?.clearRect(0, 0, canvas.width, canvas.height);
      }
      return;
    }

    function draw() {
      rafRef.current = requestAnimationFrame(draw);
      const canvas = canvasRef.current;
      if (!canvas) return;
      const c = canvas.getContext("2d");
      if (!c) return;

      // Sync logical canvas size to CSS pixel size for crisp rendering.
      const W = canvas.offsetWidth  || canvas.width;
      const H = canvas.offsetHeight || canvas.height;
      if (canvas.width !== W)  canvas.width  = W;
      if (canvas.height !== H) canvas.height = H;

      c.clearRect(0, 0, W, H);

      const an = anRef.current;
      const binCount = an ? an.frequencyBinCount : 1024;

      // Lazy-init peak arrays when bin count is known.
      if (!peakRef.current || peakRef.current.length !== binCount) {
        peakRef.current    = new Float32Array(binCount);
        peakVelRef.current = new Float32Array(binCount);
      }

      const fftRaw = new Uint8Array(binCount);
      const timRaw = new Uint8Array(an ? an.fftSize : 2048);
      if (an) {
        an.getByteFrequencyData(fftRaw);
        an.getByteTimeDomainData(timRaw);
      } else {
        timRaw.fill(128);
      }

      const freq   = smoothFreq(fftRaw);
      const color  = THEME_HEX[theme];

      if (style === "waveform") {
        c.beginPath();
        c.strokeStyle = color + "b0";
        c.lineWidth = 2;
        const step = W / timRaw.length;
        for (let i = 0; i < timRaw.length - 1; i++) {
          const x1 = i * step;
          const y1 = (timRaw[i] / 255) * H;
          const x2 = (i + 1) * step;
          const y2 = (timRaw[i + 1] / 255) * H;
          const mx = (x1 + x2) / 2;
          const my = (y1 + y2) / 2;
          if (i === 0) c.moveTo(x1, y1);
          else c.quadraticCurveTo(x1, y1, mx, my);
        }
        c.stroke();

      } else if (style === "bars") {
        const n = Math.min(freq.length, 128);
        const peak    = peakRef.current!;
        const peakVel = peakVelRef.current!;
        for (let i = 0; i < n; i++) {
          const x     = logX(i, n, W);
          const nextX = logX(i + 1, n, W);
          const barW  = Math.max(nextX - x - 1, 1);
          const val   = freq[i] / 255;
          const barH  = val * H;

          if (val > peak[i]) {
            peak[i]    = val;
            peakVel[i] = 0;
          } else {
            peakVel[i] = Math.min(peakVel[i] + 0.0008, 0.02);
            peak[i]    = Math.max(0, peak[i] - peakVel[i]);
          }

          const barColor = theme === "frequency" ? freqColor(i, n) : color;
          c.fillStyle = barColor + "99";
          c.fillRect(x, H - barH, barW, barH);
          if (peak[i] > 0.01) {
            c.fillStyle = barColor;
            c.fillRect(x, H - peak[i] * H - 2, barW, 2);
          }
        }

      } else if (style === "circular") {
        const n  = Math.min(freq.length, 128);
        const cx = W / 2;
        const cy = H / 2;
        const r0 = Math.min(W, H) * 0.28;
        for (let i = 0; i < n; i++) {
          const angle = (i / n) * Math.PI * 2 - Math.PI / 2;
          const r     = r0 + (freq[i] / 255) * r0 * 0.65;
          c.beginPath();
          c.moveTo(cx + Math.cos(angle) * r0, cy + Math.sin(angle) * r0);
          c.lineTo(cx + Math.cos(angle) * r,  cy + Math.sin(angle) * r);
          c.strokeStyle = (theme === "frequency" ? freqColor(i, n) : color) + "cc";
          c.lineWidth = 1.5;
          c.stroke();
        }
        c.beginPath();
        c.arc(cx, cy, r0, 0, Math.PI * 2);
        c.strokeStyle = color + "30";
        c.lineWidth = 1;
        c.stroke();

      } else if (style === "blob") {
        const n  = Math.min(freq.length, 64);
        const cx = W / 2;
        const cy = H / 2;
        const r0 = Math.min(W, H) * 0.26;
        c.beginPath();
        for (let i = 0; i <= n; i++) {
          const idx   = i % n;
          const angle = (idx / n) * Math.PI * 2 - Math.PI / 2;
          const r     = r0 + (freq[idx] / 255) * r0 * 0.65;
          const x     = cx + Math.cos(angle) * r;
          const y     = cy + Math.sin(angle) * r;
          const nIdx  = (idx + 1) % n;
          const nAng  = (nIdx / n) * Math.PI * 2 - Math.PI / 2;
          const nr    = r0 + (freq[nIdx] / 255) * r0 * 0.65;
          const nx    = cx + Math.cos(nAng) * nr;
          const ny    = cy + Math.sin(nAng) * nr;
          if (i === 0) c.moveTo((x + nx) / 2, (y + ny) / 2);
          else c.quadraticCurveTo(x, y, (x + nx) / 2, (y + ny) / 2);
        }
        c.closePath();
        c.fillStyle   = color + "18";
        c.fill();
        c.strokeStyle = color + "cc";
        c.lineWidth   = 2;
        c.stroke();

      } else if (style === "terrain") {
        const n = Math.min(freq.length, 128);
        c.beginPath();
        for (let i = 0; i <= n; i++) {
          const idx = i % n;
          const x   = logX(idx, n, W);
          const y   = H - (freq[idx] / 255) * H * 0.82 - H * 0.04;
          if (i === 0) {
            c.moveTo(x, y);
          } else {
            const pidx = (i - 1) % n;
            const px = logX(pidx, n, W);
            const py = H - (freq[pidx] / 255) * H * 0.82 - H * 0.04;
            c.quadraticCurveTo(px, py, (px + x) / 2, (py + y) / 2);
          }
        }
        c.lineTo(W, H);
        c.lineTo(0, H);
        c.closePath();
        c.fillStyle   = color + "22";
        c.fill();
        c.strokeStyle = color + "cc";
        c.lineWidth   = 2;
        c.stroke();
      }
    }

    draw();
    return () => cancelAnimationFrame(rafRef.current);
  }, [canvasRef, style, theme]);
}
