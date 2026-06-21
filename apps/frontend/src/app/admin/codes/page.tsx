"use client";

import { useEffect, useState } from "react";
import { createCode, deactivateCode, listCodes, type AdminCode } from "@/features/admin/lib/adminApi";

const FRONTEND_BASE =
  typeof window !== "undefined" ? window.location.origin : "https://wavepalace.live";

export default function AdminCodesPage() {
  const [codes, setCodes] = useState<AdminCode[]>([]);
  const [loading, setLoading] = useState(true);
  const [slug, setSlug] = useState("");
  const [entityId, setEntityId] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    listCodes()
      .then(setCodes)
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!slug.trim()) return;
    setBusy(true);
    try {
      const code = await createCode(slug.trim(), entityId.trim() || slug.trim());
      setCodes((prev) => [code, ...prev]);
      setSlug("");
      setEntityId("");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeactivate(code: string) {
    await deactivateCode(code);
    setCodes((prev) => prev.map((c) => (c.code === code ? { ...c, active: false } : c)));
  }

  function copyLink(code: string) {
    navigator.clipboard.writeText(`${FRONTEND_BASE}/follow/${code}`);
    setCopied(code);
    setTimeout(() => setCopied(null), 2000);
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8 px-6 py-12">
      <h1 className="text-2xl font-bold text-white">Follow Codes</h1>

      <form onSubmit={handleCreate} className="glass rounded-2xl p-6 space-y-4">
        <h2 className="text-sm font-semibold text-white/60 uppercase tracking-wider">
          Generate New Code
        </h2>
        <div className="flex gap-3">
          <input
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            placeholder="Channel slug (e.g. late-night-house)"
            className="flex-1 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-white placeholder:text-white/30 outline-none focus:border-wave-400/60"
          />
          <button
            type="submit"
            disabled={busy || !slug.trim()}
            className="rounded-xl bg-wave-500 px-4 py-2 text-sm font-semibold text-white hover:bg-wave-400 disabled:opacity-40"
          >
            Generate
          </button>
        </div>
      </form>

      <div className="glass rounded-2xl p-6">
        <h2 className="mb-4 text-sm font-semibold text-white/60 uppercase tracking-wider">
          Active Codes
        </h2>
        {loading ? (
          <p className="text-white/40 text-sm">Loading…</p>
        ) : codes.filter((c) => c.active).length === 0 ? (
          <p className="text-white/40 text-sm">No active codes yet.</p>
        ) : (
          <ul className="space-y-3">
            {codes
              .filter((c) => c.active)
              .map((c) => (
                <li key={c.code} className="flex items-center justify-between gap-4">
                  <div>
                    <span className="font-mono font-bold tracking-widest text-wave-400">
                      {c.code}
                    </span>
                    <span className="ml-3 text-xs text-white/40">{c.channel_slug}</span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => copyLink(c.code)}
                      className="text-xs text-white/50 hover:text-white"
                    >
                      {copied === c.code ? "Copied!" : "Copy link"}
                    </button>
                    <button
                      onClick={() => handleDeactivate(c.code)}
                      className="text-xs text-red-400/60 hover:text-red-400"
                    >
                      Deactivate
                    </button>
                  </div>
                </li>
              ))}
          </ul>
        )}
      </div>
    </div>
  );
}

