"use client";

import { useEffect, useState } from "react";
import { listSubmissions, reviewSubmission } from "@/features/admin/lib/adminApi";
import type { AdminSubmission } from "@/features/admin/types/admin";
import { X, CheckCircle, XCircle, ChevronRight } from "lucide-react";

const TABS = ["pending", "approved", "rejected"] as const;
type Tab = (typeof TABS)[number];

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "border-amber-400/30 bg-amber-400/10 text-amber-300",
    approved: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
    rejected: "border-red-400/30 bg-red-400/10 text-red-300",
  };
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${colors[status] ?? ""}`}>
      {status}
    </span>
  );
}

function Drawer({
  sub,
  onClose,
  onAction,
}: {
  sub: AdminSubmission;
  onClose: () => void;
  onAction: (id: string, status: "approved" | "rejected", notes?: string) => Promise<void>;
}) {
  const [notes, setNotes] = useState(sub.reviewer_notes ?? "");
  const [busy, setBusy] = useState(false);

  async function act(status: "approved" | "rejected") {
    setBusy(true);
    await onAction(sub.id, status, notes || undefined);
    setBusy(false);
    onClose();
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* backdrop */}
      <div className="flex-1 bg-black/60" onClick={onClose} />
      {/* panel */}
      <div className="w-full max-w-md overflow-y-auto border-l border-white/10 bg-black/90 p-8 backdrop-blur-xl">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">{sub.channel_title}</h2>
          <button onClick={onClose} className="text-white/40 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <dl className="flex flex-col gap-3 text-sm">
          <Row label="Submitted" value={formatDate(sub.submitted_at)} />
          <Row label="Submitter" value={sub.submitter_name} />
          <Row label="Email" value={sub.contact_email} />
          <Row label="Genre" value={sub.genre.join(", ")} />
          <Row label="Mood" value={sub.mood.join(", ")} />
          <Row label="Energy" value={sub.energy.join(", ")} />
          <Row label="Theme" value={sub.theme.join(", ")} />
          <Row label="Description" value={sub.description} />
          {sub.notes && <Row label="Notes" value={sub.notes} />}
          {sub.sample_links.length > 0 && (
            <div>
              <dt className="text-xs text-white/40">Sample links</dt>
              <dd className="mt-1 flex flex-col gap-1">
                {sub.sample_links.map((link) => (
                  <a
                    key={link}
                    href={link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="truncate text-xs text-cyan-400 hover:underline"
                  >
                    {link}
                  </a>
                ))}
              </dd>
            </div>
          )}
          {sub.profile_image_url && (
            <div>
              <dt className="mb-1 text-xs text-white/40">Profile image</dt>
              <img
                src={sub.profile_image_url}
                alt="Profile"
                className="h-16 w-16 rounded-full object-cover ring-2 ring-white/10"
              />
            </div>
          )}
        </dl>

        {sub.status === "pending" && (
          <div className="mt-6 flex flex-col gap-3">
            <label className="text-xs text-white/40">Reviewer notes (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white placeholder-white/30 outline-none focus:border-white/30 resize-none"
              placeholder="Internal notes…"
            />
            <div className="flex gap-3">
              <button
                onClick={() => act("approved")}
                disabled={busy}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-emerald-500/20 px-4 py-2.5 text-sm font-medium text-emerald-300 hover:bg-emerald-500/30 disabled:opacity-50 transition"
              >
                <CheckCircle className="h-4 w-4" /> Approve
              </button>
              <button
                onClick={() => act("rejected")}
                disabled={busy}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-red-500/20 px-4 py-2.5 text-sm font-medium text-red-300 hover:bg-red-500/30 disabled:opacity-50 transition"
              >
                <XCircle className="h-4 w-4" /> Reject
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-white/40">{label}</dt>
      <dd className="mt-0.5 text-white/90">{value}</dd>
    </div>
  );
}

export default function SubmissionsPage() {
  const [tab, setTab] = useState<Tab>("pending");
  const [subs, setSubs] = useState<AdminSubmission[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<AdminSubmission | null>(null);

  async function load(t: Tab) {
    setLoading(true);
    const data = await listSubmissions(t);
    setSubs(data);
    setLoading(false);
    if (t === "pending") setPendingCount(data.length);
  }

  useEffect(() => {
    load(tab);
    // also refresh pending count for badge
    if (tab !== "pending") listSubmissions("pending").then((d) => setPendingCount(d.length));
  }, [tab]);

  async function handleAction(id: string, status: "approved" | "rejected", notes?: string) {
    await reviewSubmission(id, status, notes);
    setSubs((prev) => prev.filter((s) => s.id !== id));
    if (status === "approved" || status === "rejected") {
      setPendingCount((c) => Math.max(0, c - 1));
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold text-white">Submissions</h1>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 border-b border-white/10">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition ${
              tab === t
                ? "border-b-2 border-white text-white"
                : "text-white/40 hover:text-white/70"
            }`}
          >
            {t}
            {t === "pending" && pendingCount > 0 && (
              <span className="ml-1.5 rounded-full bg-amber-400/20 px-1.5 py-0.5 text-xs text-amber-300">
                {pendingCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-white/40">Loading…</p>
      ) : subs.length === 0 ? (
        <p className="text-sm text-white/40">No {tab} submissions.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 text-left text-xs text-white/40">
              <th className="pb-2 pr-4">Date</th>
              <th className="pb-2 pr-4">Name</th>
              <th className="pb-2 pr-4">Channel</th>
              <th className="pb-2 pr-4">Genre</th>
              <th className="pb-2">Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {subs.map((s) => (
              <tr
                key={s.id}
                onClick={() => setSelected(s)}
                className="cursor-pointer border-b border-white/5 transition hover:bg-white/5"
              >
                <td className="py-3 pr-4 text-white/60">{formatDate(s.submitted_at)}</td>
                <td className="py-3 pr-4 text-white/90">{s.submitter_name}</td>
                <td className="py-3 pr-4 text-white/90">{s.channel_title}</td>
                <td className="py-3 pr-4 text-white/60">{s.genre.join(", ")}</td>
                <td className="py-3">
                  <StatusBadge status={s.status} />
                </td>
                <td className="py-3 pl-2">
                  <ChevronRight className="h-4 w-4 text-white/30" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selected && (
        <Drawer
          sub={selected}
          onClose={() => setSelected(null)}
          onAction={handleAction}
        />
      )}
    </div>
  );
}
