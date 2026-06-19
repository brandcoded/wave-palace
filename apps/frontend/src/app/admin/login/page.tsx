"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/features/admin/lib/adminApi";
import { GlassPanel } from "@/presentation/components/GlassPanel";

export default function AdminLoginPage() {
  const [secret, setSecret] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(secret);
      router.replace("/admin/submissions");
    } catch {
      setError("Incorrect secret.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <GlassPanel className="w-full max-w-sm p-8">
        <h1 className="mb-6 text-lg font-semibold text-white">Admin</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="secret" className="text-xs font-medium text-white/60">
              Admin secret
            </label>
            <input
              id="secret"
              type="password"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              required
              autoFocus
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/30 outline-none focus:border-white/30 focus:ring-0"
            />
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="rounded-lg bg-white/10 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-white/20 disabled:opacity-50"
          >
            {loading ? "Checking…" : "Enter"}
          </button>
        </form>
      </GlassPanel>
    </div>
  );
}
