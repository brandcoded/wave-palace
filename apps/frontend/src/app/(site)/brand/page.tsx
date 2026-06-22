"use client";

import { useCallback } from "react";
import Link from "next/link";

export default function BrandPage() {
  const downloadPng = useCallback(async () => {
    const scale = 3;
    const W = 260;
    const H = 48;

    const canvas = document.createElement("canvas");
    canvas.width = W * scale;
    canvas.height = H * scale;
    const ctx = canvas.getContext("2d")!;
    ctx.scale(scale, scale);

    const fontSize = 20;
    ctx.font = `600 ${fontSize}px Inter, system-ui, -apple-system, sans-serif`;
    ctx.textBaseline = "middle";

    const centerY = H / 2;
    const iconCX = 12;
    const iconCY = centerY;

    // Disc3 icon — #a78bfa (wave-400)
    ctx.strokeStyle = "#a78bfa";
    ctx.lineWidth = 1.5;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    // Outer circle
    ctx.beginPath();
    ctx.arc(iconCX, iconCY, 10, 0, Math.PI * 2);
    ctx.stroke();

    // Arc: M6 12 c0,-1.7 0.7,-3.2 1.8,-4.2  (offset y by centerY-12)
    const dy = centerY - 12;
    ctx.beginPath();
    ctx.moveTo(6, iconCY);
    ctx.bezierCurveTo(6, iconCY - 1.7, 6.7, iconCY - 3.2, 7.8, iconCY - 4.2);
    ctx.stroke();

    // Inner circle r=2
    ctx.beginPath();
    ctx.arc(iconCX, iconCY, 2, 0, Math.PI * 2);
    ctx.stroke();

    // Arc: M18 12 c0,1.7 -0.7,3.2 -1.8,4.2
    ctx.beginPath();
    ctx.moveTo(18, iconCY);
    ctx.bezierCurveTo(18, iconCY + 1.7, 17.3, iconCY + 3.2, 16.2, iconCY + 4.2);
    ctx.stroke();

    // "Wave" — #ece9ff
    const textX = 34;
    ctx.fillStyle = "#ece9ff";
    ctx.fillText("Wave", textX, centerY);

    const waveW = ctx.measureText("Wave").width;

    // "Palace" — cyan→purple→magenta gradient
    const palaceX = textX + waveW;
    const palaceW = ctx.measureText("Palace").width;
    const grad = ctx.createLinearGradient(palaceX, 0, palaceX + palaceW, 0);
    grad.addColorStop(0, "#38e8ff");
    grad.addColorStop(0.45, "#a78bfa");
    grad.addColorStop(1, "#ff5cc8");
    ctx.fillStyle = grad;
    ctx.fillText("Palace", palaceX, centerY);

    canvas.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "wavepalace-logo.png";
      a.click();
      URL.revokeObjectURL(url);
    }, "image/png");
  }, []);

  return (
    <div className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">Brand Kit</h1>
      <p className="mb-12 text-sm text-white/50">
        Official WavePalace logo for press, partners, and community use.
      </p>

      {/* Logo preview on dark */}
      <div className="mb-4 flex items-center justify-center rounded-2xl border border-white/10 bg-black/40 px-12 py-14 backdrop-blur-sm">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/logo.svg" alt="WavePalace logo" className="h-12" />
      </div>
      <p className="mb-8 text-center text-xs text-white/30">
        SVG · transparent background · color
      </p>

      {/* Download actions */}
      <div className="flex flex-wrap justify-center gap-3">
        <button
          onClick={downloadPng}
          className="rounded-full bg-wave-500 px-6 py-2.5 text-sm font-medium text-white transition hover:bg-wave-400"
        >
          Download PNG
        </button>
        <a
          href="/logo.svg"
          download="wavepalace-logo.svg"
          className="rounded-full border border-white/10 bg-white/5 px-6 py-2.5 text-sm font-medium text-white/70 transition hover:bg-white/10 hover:text-white"
        >
          Download SVG
        </a>
      </div>

      <p className="mt-10 text-center text-xs text-white/30">
        Please do not alter the logo colors or proportions.{" "}
        <Link href="/submit" className="underline underline-offset-2 hover:text-white/60">
          Questions?
        </Link>
      </p>
    </div>
  );
}
