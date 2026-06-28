"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { followAsMe, submitFollow } from "@/features/follow/lib/followApi";
import { getMe } from "@/features/me/lib/meApi";

import type { CurrentUser } from "@/features/admin/types/admin";

interface Props {
  code: string;
  discordInitiateUrl: string;
}

type Method = "discord" | "email";

export function FollowForm({ code, discordInitiateUrl }: Props) {
  const [user, setUser] = useState<CurrentUser | null | "loading">("loading");
  const [method, setMethod] = useState<Method | null>(null);

  useEffect(() => {
    getMe().then((u) => setUser(u));
  }, []);
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "busy" | "done" | "already" | "error">("idle");
  const [message, setMessage] = useState("");

  async function handleFollowAsMe() {
    setStatus("busy");
    try {
      const result = await followAsMe(code);
      setStatus(result.already ? "already" : "done");
    } catch (err: unknown) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Something went wrong.");
    }
  }

  async function handleEmailSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setStatus("busy");
    try {
      await submitFollow(code, { channel: "email", email: email.trim() });
      setStatus("done");
      setMessage("Check your inbox to confirm your follow.");
    } catch (err: unknown) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Something went wrong.");
    }
  }

  const resolvedUser = user === "loading" ? null : user;

  // Success states
  if (status === "done") {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-center">
        <p className="mb-3 text-sm text-white/80">
          {resolvedUser ? "You're now following this channel!" : message}
        </p>
        {resolvedUser && (
          <Link
            href="/follows"
            className="text-xs text-wave-400 hover:underline"
          >
            Manage your follows →
          </Link>
        )}
      </div>
    );
  }

  if (status === "already") {
    return (
      <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-center">
        <p className="mb-3 text-sm text-white/60">You&apos;re already following this channel.</p>
        <Link href="/follows" className="text-xs text-wave-400 hover:underline">
          Manage your follows →
        </Link>
      </div>
    );
  }

  // Still checking session — show nothing to avoid flash of logged-out UI
  if (user === "loading") {
    return <div className="h-24" />;
  }

  // Logged-in: one-click path
  if (resolvedUser !== null) {
    return (
      <div className="flex flex-col gap-3">
        <button
          onClick={handleFollowAsMe}
          disabled={status === "busy"}
          className="rounded-2xl bg-wave-500 px-6 py-4 text-sm font-semibold text-white transition hover:bg-wave-400 disabled:opacity-50"
        >
          {status === "busy" ? "Following…" : `Follow as ${resolvedUser!.display_name}`}
        </button>
        {status === "error" && (
          <p className="text-xs text-red-400">{message}</p>
        )}
        <p className="text-xs text-white/30">
          Your follow will be confirmed instantly.
        </p>
      </div>
    );
  }

  // Logged-out: existing Discord/email form
  if (method === null) {
    return (
      <div className="flex flex-col gap-3">
        <a
          href={discordInitiateUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-3 rounded-2xl border border-[#5865F2]/40 bg-[#5865F2]/10 px-6 py-4 text-sm font-semibold text-white transition hover:bg-[#5865F2]/20"
        >
          <svg className="h-5 w-5" viewBox="0 0 71 55" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path
              d="M60.1 4.9A58.5 58.5 0 0 0 45.5.4a.22.22 0 0 0-.24.11 40.8 40.8 0 0 0-1.8 3.7 54 54 0 0 0-16.2 0 37.4 37.4 0 0 0-1.83-3.7.23.23 0 0 0-.24-.11A58.4 58.4 0 0 0 10.8 4.9a.2.2 0 0 0-.1.08C1.58 18.7-.96 32.2.3 45.5a.24.24 0 0 0 .09.17 58.8 58.8 0 0 0 17.7 8.95.23.23 0 0 0 .25-.08 42 42 0 0 0 3.62-5.9.22.22 0 0 0-.12-.31 38.7 38.7 0 0 1-5.53-2.64.23.23 0 0 1-.02-.38c.37-.28.74-.57 1.1-.86a.22.22 0 0 1 .23-.03c11.6 5.3 24.1 5.3 35.5 0a.22.22 0 0 1 .23.03c.36.3.74.58 1.1.86a.23.23 0 0 1-.02.38 36.3 36.3 0 0 1-5.53 2.63.23.23 0 0 0-.12.32 47.1 47.1 0 0 0 3.61 5.9.22.22 0 0 0 .25.07A58.6 58.6 0 0 0 70.5 45.7a.24.24 0 0 0 .1-.17c1.52-15.7-2.55-29.1-10.8-41.5a.2.2 0 0 0-.1-.08Z"
              fill="#5865F2"
            />
          </svg>
          Follow with Discord
        </a>
        <button
          onClick={() => setMethod("email")}
          className="rounded-2xl border border-white/10 bg-white/5 px-6 py-4 text-sm font-semibold text-white/70 transition hover:bg-white/10 hover:text-white"
        >
          Follow with Email
        </button>
        <p className="mt-2 text-xs text-white/30">
          No account required. Discord follows are confirmed instantly. A new tab
          will open for Discord — your music keeps playing here.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleEmailSubmit} className="flex flex-col gap-3">
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@example.com"
        required
        className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-white/30 outline-none focus:border-wave-400/60"
      />
      {status === "error" && (
        <p className="text-xs text-red-400">{message}</p>
      )}
      <button
        type="submit"
        disabled={status === "busy"}
        className="rounded-2xl bg-wave-500 px-6 py-3 text-sm font-semibold text-white transition hover:bg-wave-400 disabled:opacity-50"
      >
        {status === "busy" ? "Sending…" : "Send confirmation email"}
      </button>
      <button
        type="button"
        onClick={() => { setMethod(null); setStatus("idle"); setMessage(""); }}
        className="text-xs text-white/40 underline"
      >
        Back
      </button>
    </form>
  );
}
