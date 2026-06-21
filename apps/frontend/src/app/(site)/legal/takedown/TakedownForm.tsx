"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

const ROLES = [
  { value: "artist", label: "Artist" },
  { value: "label", label: "Label / Publisher" },
  { value: "attorney", label: "Attorney" },
  { value: "other", label: "Other" },
] as const;

type Role = (typeof ROLES)[number]["value"];

export function TakedownForm() {
  const router = useRouter();

  const [fields, setFields] = useState({
    claimant_name: "",
    organization: "",
    email: "",
    role: "" as Role | "",
    infringing_url: "",
    description: "",
    proof: "",
    good_faith: false,
    accuracy: false,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set(key: keyof typeof fields, value: string | boolean) {
    setFields((prev) => ({ ...prev, [key]: value }));
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!fields.good_faith || !fields.accuracy) {
      setError("Both statements must be acknowledged before submitting.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/takedowns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...fields,
          organization: fields.organization || undefined,
          proof: fields.proof || undefined,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Submission failed. Please try again.");
      }
      router.push("/legal/takedown/submitted");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed.");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-6">
      {/* Claimant info */}
      <div className="glass rounded-2xl p-6 flex flex-col gap-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-white/50">
          Your Information
        </h2>

        <Field label="Full name *">
          <input
            required
            value={fields.claimant_name}
            onChange={(e) => set("claimant_name", e.target.value)}
            placeholder="Jane Doe"
            className={inputCls}
          />
        </Field>

        <Field label="Organization / Label" hint="Optional">
          <input
            value={fields.organization}
            onChange={(e) => set("organization", e.target.value)}
            placeholder="Doe Music Group"
            className={inputCls}
          />
        </Field>

        <Field label="Email address *">
          <input
            required
            type="email"
            value={fields.email}
            onChange={(e) => set("email", e.target.value)}
            placeholder="jane@example.com"
            className={inputCls}
          />
        </Field>

        <Field label="Your role *">
          <select
            required
            value={fields.role}
            onChange={(e) => set("role", e.target.value as Role)}
            className={inputCls}
          >
            <option value="">Select a role…</option>
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </Field>
      </div>

      {/* Claim details */}
      <div className="glass rounded-2xl p-6 flex flex-col gap-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-white/50">
          Claim Details
        </h2>

        <Field label="Infringing content URL *">
          <input
            required
            type="url"
            value={fields.infringing_url}
            onChange={(e) => set("infringing_url", e.target.value)}
            placeholder="https://wavepalace.live/channels/…"
            className={inputCls}
          />
        </Field>

        <Field label="Description of copyrighted work *">
          <textarea
            required
            rows={4}
            value={fields.description}
            onChange={(e) => set("description", e.target.value)}
            placeholder="I own the rights to [song] by [artist], released on [date]…"
            className={inputCls}
          />
        </Field>

        <Field label="Proof of ownership" hint="ISRC, registration number, release link, etc. — optional">
          <textarea
            rows={3}
            value={fields.proof}
            onChange={(e) => set("proof", e.target.value)}
            placeholder="ISRC: USRC17607839"
            className={inputCls}
          />
        </Field>
      </div>

      {/* Legal statements */}
      <div className="glass rounded-2xl p-6 flex flex-col gap-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-white/50">
          Statements
        </h2>

        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={fields.good_faith}
            onChange={(e) => set("good_faith", e.target.checked)}
            className="mt-0.5 h-4 w-4 shrink-0 accent-wave-400"
          />
          <span className="text-sm text-white/70">
            I have a good-faith belief that the use of the material in the manner
            complained of is not authorized by the copyright owner, its agent, or
            the law. *
          </span>
        </label>

        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={fields.accuracy}
            onChange={(e) => set("accuracy", e.target.checked)}
            className="mt-0.5 h-4 w-4 shrink-0 accent-wave-400"
          />
          <span className="text-sm text-white/70">
            The information in this notice is accurate, and under penalty of
            perjury, I am the copyright owner or am authorized to act on behalf
            of the owner of an exclusive right that is allegedly infringed. *
          </span>
        </label>
      </div>

      {error && (
        <p className="rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-300">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-2xl bg-white/10 py-3.5 text-sm font-semibold text-white transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? "Submitting…" : "Submit Takedown Request"}
      </button>
    </form>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline gap-2">
        <label className="text-xs font-semibold uppercase tracking-widest text-white/50">
          {label}
        </label>
        {hint && <span className="text-xs text-white/30">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

const inputCls =
  "w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder:text-white/25 outline-none transition focus:border-wave-400/50 focus:bg-white/8";
