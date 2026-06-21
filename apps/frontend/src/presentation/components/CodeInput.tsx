"use client";

import { useRouter } from "next/navigation";
import { useState, useRef } from "react";

export function CodeInput() {
  const [value, setValue] = useState("");
  const [error, setError] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const code = value.trim().toUpperCase();
    if (code.length === 0) return;
    if (!/^[A-Z0-9]{4,8}$/.test(code)) {
      setError(true);
      return;
    }
    router.push(`/follow/${code}`);
    setValue("");
    setError(false);
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => {
          setValue(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 8));
          setError(false);
        }}
        maxLength={8}
        placeholder="ENTER CODE"
        aria-label="Enter channel code"
        className={[
          "w-28 rounded-full border bg-white/5 px-3 py-1.5 text-center text-xs font-mono font-semibold tracking-widest text-white/80 outline-none transition placeholder:text-white/30",
          error
            ? "border-red-500/60 focus:border-red-400"
            : "border-white/10 focus:border-wave-400/60",
        ].join(" ")}
      />
      <button
        type="submit"
        className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-medium text-white/70 transition hover:bg-white/10 hover:text-white"
      >
        Go
      </button>
    </form>
  );
}
