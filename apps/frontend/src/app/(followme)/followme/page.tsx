"use client";

import { Suspense, useRef, useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Disc3 } from "lucide-react";
import { resolveCode } from "@/features/follow/lib/followApi";

function FollowMeInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const inputRefs = useRef<Array<HTMLInputElement | null>>([]);
  const [cells, setCells] = useState<string[]>(Array(6).fill(""));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const errorTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const busyRef = useRef(false);

  busyRef.current = busy;

  const clearError = () => {
    if (errorTimer.current) clearTimeout(errorTimer.current);
    setError(null);
  };

  const showError = (msg: string) => {
    clearError();
    setError(msg);
    errorTimer.current = setTimeout(() => setError(null), 3000);
  };

  const submit = useCallback(
    async (code: string) => {
      if (code.length !== 6 || busyRef.current) return;
      setBusy(true);
      clearError();
      try {
        const info = await resolveCode(code);
        if (!info) {
          setCells(Array(6).fill(""));
          setTimeout(() => inputRefs.current[0]?.focus(), 0);
          showError("That code isn't valid or has expired.");
        } else {
          router.push(`/follow/${code}`);
        }
      } catch {
        showError("Something went wrong. Try again.");
      } finally {
        setBusy(false);
      }
    },
    [router]
  );

  // Pre-fill + auto-submit from ?c= query param
  useEffect(() => {
    const c = searchParams.get("c");
    if (!c) return;
    const chars = c.replace(/[^A-Za-z0-9]/g, "").toUpperCase().slice(0, 6);
    if (chars.length !== 6) return;
    setCells(chars.split(""));
    submit(chars);
  }, []);   // mount-only — submit is stable

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, idx: number) => {
    if (e.key === "Backspace" && cells[idx] === "" && idx > 0) {
      inputRefs.current[idx - 1]?.focus();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>, idx: number) => {
    clearError();
    const raw = e.target.value.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
    const char = raw ? raw[raw.length - 1] : "";
    const next = [...cells];
    next[idx] = char;
    setCells(next);
    if (char && idx < 5) {
      inputRefs.current[idx + 1]?.focus();
    } else if (char && idx === 5) {
      const code = next.join("");
      if (code.length === 6) submit(code);
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text");
    const chars = pasted.replace(/[^A-Za-z0-9]/g, "").toUpperCase().slice(0, 6);
    if (!chars) return;
    const next = Array(6).fill("") as string[];
    chars.split("").forEach((c, i) => { next[i] = c; });
    setCells(next);
    const focusIdx = Math.min(chars.length, 5);
    inputRefs.current[focusIdx]?.focus();
    if (chars.length === 6) submit(chars);
  };

  const filled = cells.filter(Boolean).length;

  const cellStyle = (idx: number): React.CSSProperties => ({
    background: "rgba(255,255,255,0.07)",
    border: `1px solid ${cells[idx] ? "rgba(127,119,221,0.8)" : "rgba(255,255,255,0.15)"}`,
    caretColor: "transparent",
  });

  return (
    <div
      className="relative flex min-h-screen flex-col"
      style={{ backgroundColor: "#0d0d14" }}
    >
      {/* Radial glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 60% 50% at 50% 50%, rgba(83,74,183,0.18) 0%, transparent 70%)",
        }}
      />

      {/* Wordmark */}
      <div className="relative z-10 px-6 pt-6">
        <a href="/" className="group inline-flex items-center gap-1.5" aria-label="WavePalace home">
          <Disc3 className="h-4 w-4 text-wave-400 opacity-60 transition-transform group-hover:rotate-90" />
          <span
            className="text-xs font-semibold uppercase tracking-widest"
            style={{ color: "rgba(255,255,255,0.35)" }}
          >
            WavePalace
          </span>
        </a>
      </div>

      {/* Main */}
      <div className="relative z-10 flex flex-1 flex-col items-center justify-center px-6 pb-20">
        <h1 className="mb-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
          Follow me
        </h1>
        <p className="mb-10 text-sm" style={{ color: "rgba(255,255,255,0.5)" }}>
          Enter the code from your DJ, artist, or host.
        </p>

        {/* Glass card */}
        <div
          className="w-full max-w-sm rounded-3xl p-8"
          style={{
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.10)",
            backdropFilter: "blur(20px)",
          }}
        >
          {/* Six-cell input: ◻ ◻ ◻ · ◻ ◻ ◻ */}
          <div
            className="flex items-center justify-center gap-2"
            role="group"
            aria-label="Enter 6-character code"
          >
            {[0, 1, 2].map((i) => (
              <input
                key={i}
                ref={(el) => { inputRefs.current[i] = el; }}
                type="text"
                inputMode="text"
                maxLength={1}
                value={cells[i]}
                disabled={busy}
                onChange={(e) => handleChange(e, i)}
                onKeyDown={(e) => handleKeyDown(e, i)}
                onPaste={handlePaste}
                onFocus={(e) => e.target.select()}
                className="h-14 w-12 rounded-lg text-center font-mono text-2xl font-semibold text-white outline-none transition-all disabled:opacity-40"
                style={cellStyle(i)}
                aria-label={`Code character ${i + 1}`}
              />
            ))}

            <span className="select-none text-lg" style={{ color: "rgba(255,255,255,0.25)" }}>
              ·
            </span>

            {[3, 4, 5].map((i) => (
              <input
                key={i}
                ref={(el) => { inputRefs.current[i] = el; }}
                type="text"
                inputMode="text"
                maxLength={1}
                value={cells[i]}
                disabled={busy}
                onChange={(e) => handleChange(e, i)}
                onKeyDown={(e) => handleKeyDown(e, i)}
                onPaste={handlePaste}
                onFocus={(e) => e.target.select()}
                className="h-14 w-12 rounded-lg text-center font-mono text-2xl font-semibold text-white outline-none transition-all disabled:opacity-40"
                style={cellStyle(i)}
                aria-label={`Code character ${i + 1}`}
              />
            ))}
          </div>

          {/* Error */}
          {error && (
            <p
              className="mt-4 text-center text-xs"
              style={{ color: "rgba(226,75,74,0.9)" }}
              role="alert"
            >
              {error}
            </p>
          )}

          {/* Button */}
          <button
            type="button"
            disabled={busy || filled < 6}
            onClick={() => submit(cells.join(""))}
            className="mt-6 w-full rounded-xl py-3 text-sm font-semibold text-white/90 transition-colors disabled:cursor-not-allowed disabled:opacity-40"
            style={{
              background: "rgba(127,119,221,0.15)",
              border: "1px solid rgba(127,119,221,0.4)",
            }}
            onMouseEnter={(e) => {
              if (!busy && filled === 6)
                (e.currentTarget as HTMLButtonElement).style.background =
                  "rgba(127,119,221,0.28)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background =
                "rgba(127,119,221,0.15)";
            }}
          >
            {busy ? "Finding them…" : "Follow them"}
          </button>
        </div>

        {/* Footer */}
        <p className="mt-8 text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>
          Just browsing?{" "}
          <a
            href="/"
            style={{ color: "rgba(127,119,221,0.7)" }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.color = "rgba(167,139,250,1)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.color = "rgba(127,119,221,0.7)";
            }}
          >
            Explore channels →
          </a>
        </p>
      </div>
    </div>
  );
}

export default function FollowMePage() {
  return (
    <Suspense fallback={null}>
      <FollowMeInner />
    </Suspense>
  );
}
