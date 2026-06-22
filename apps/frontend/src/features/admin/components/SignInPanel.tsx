"use client";

import { useState } from "react";
import { MessageSquare, Mail, KeyRound, CheckCircle } from "lucide-react";
import { login, requestEmailLink, discordLoginUrl } from "@/features/admin/lib/adminApi";

interface Props {
  onSuccess: () => void;
}

export function SignInPanel({ onSuccess }: Props) {
  const [tab, setTab] = useState<"discord" | "email" | "secret">("discord");
  const [email, setEmail] = useState("");
  const [secret, setSecret] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [emailSent, setEmailSent] = useState(false);

  async function handleEmailSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await requestEmailLink(email);
      setEmailSent(true);
    } catch {
      setError("Failed to send link. Try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSecretSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(secret);
      onSuccess();
    } catch {
      setError("Incorrect secret.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Tab bar */}
      <div className="flex rounded-xl border border-white/10 bg-white/5 p-1 gap-1">
        {(["discord", "email", "secret"] as const).map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); setError(""); setEmailSent(false); }}
            className={`flex-1 rounded-lg py-1.5 text-xs font-medium transition ${
              tab === t ? "bg-white/15 text-white" : "text-white/40 hover:text-white/70"
            }`}
          >
            {t === "discord" ? "Discord" : t === "email" ? "Email link" : "Secret"}
          </button>
        ))}
      </div>

      {/* Discord */}
      {tab === "discord" && (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-white/50">
            Sign in with your Discord account. You must have been granted access by an admin first.
          </p>
          <a
            href={discordLoginUrl()}
            className="flex items-center justify-center gap-2.5 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500"
          >
            <MessageSquare className="h-4 w-4" />
            Continue with Discord
          </a>
        </div>
      )}

      {/* Email magic link */}
      {tab === "email" && (
        emailSent ? (
          <div className="flex flex-col items-center gap-3 py-2 text-center">
            <CheckCircle className="h-8 w-8 text-emerald-400" />
            <p className="text-sm text-white/80">Check your inbox — a sign-in link is on its way.</p>
            <p className="text-xs text-white/40">The link expires in 15 minutes.</p>
          </div>
        ) : (
          <form onSubmit={handleEmailSubmit} className="flex flex-col gap-3">
            <p className="text-xs text-white/50">
              Enter your email address and we'll send a one-click sign-in link.
            </p>
            <div className="flex flex-col gap-1.5">
              <label htmlFor="email" className="text-xs font-medium text-white/60">Email address</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
                placeholder="you@example.com"
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/30 outline-none focus:border-white/30"
              />
            </div>
            {error && <p className="text-xs text-red-400">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="flex items-center justify-center gap-2 rounded-lg bg-white/10 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-white/20 disabled:opacity-50"
            >
              <Mail className="h-4 w-4" />
              {loading ? "Sending…" : "Send sign-in link"}
            </button>
          </form>
        )
      )}

      {/* Secret (break-glass) */}
      {tab === "secret" && (
        <form onSubmit={handleSecretSubmit} className="flex flex-col gap-3">
          <p className="text-xs text-white/50">Break-glass access via admin secret.</p>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="secret" className="text-xs font-medium text-white/60">Admin secret</label>
            <input
              id="secret"
              type="password"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              required
              autoFocus
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/30 outline-none focus:border-white/30"
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="flex items-center justify-center gap-2 rounded-lg bg-white/10 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-white/20 disabled:opacity-50"
          >
            <KeyRound className="h-4 w-4" />
            {loading ? "Checking…" : "Enter"}
          </button>
        </form>
      )}
    </div>
  );
}
