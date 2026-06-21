"use client";

import { useEffect, useState } from "react";
import { X, ExternalLink } from "lucide-react";
import { listTakedowns, updateTakedownStatus } from "@/features/admin/lib/adminApi";
import type { AdminTakedown } from "@/features/admin/types/admin";

const STATUS_FLOW = ["pending", "reviewed", "actioned", "dismissed"] as const;

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function StatusBadge({ status }: { status: AdminTakedown["status"] }) {
  const colors: Record<AdminTakedown["status"], string> = {
    pending: "border-amber-400/30 bg-amber-400/10 text-amber-300",
    reviewed: "border-blue-400/30 bg-blue-400/10 text-blue-300",
    actioned: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
    dismissed: "border-white/10 bg-white/5 text-white/40",
  };
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${colors[status]}`}>
      {status}
    </span>
  );
}

function TakedownDrawer({
  item,
  onClose,
  onUpdate,
}: {
  item: AdminTakedown;
  onClose: () => void;
  onUpdate: (updated: AdminTakedown) => void;
}) {
  const [status, setStatus] = useState<AdminTakedown["status"]>(item.status);
  const [notes, setNotes] = useState(item.notes ?? "");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  async function save() {
    setBusy(true);
    try {
      const updated = await updateTakedownStatus(item.id, status, notes || undefined);
      onUpdate(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="flex-1 bg-black/60" onClick={onClose} />
      <div className="w-full sm:max-w-lg overflow-y-auto border-l border-white/10 bg-black/90 p-6 sm:p-8 backdrop-blur-xl">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">
            Takedown — {item.claimant_name}
          </h2>
          <button
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-white/40 hover:text-white transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <dl className="flex flex-col gap-3 text-sm mb-6">
          <Row label="Submitted" value={formatDate(item.submitted_at)} />
          <Row label="Claimant" value={item.claimant_name} />
          {item.organization && <Row label="Organization" value={item.organization} />}
          <Row label="Email" value={item.email} />
          <Row label="Role" value={item.role} />
          <div>
            <dt className="text-xs text-white/40 mb-1">Infringing URL</dt>
            <dd>
              <a
                href={item.infringing_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-wave-400 hover:text-wave-300 break-all"
              >
                {item.infringing_url}
                <ExternalLink className="h-3 w-3 shrink-0" />
              </a>
            </dd>
          </div>
          <Row label="Description" value={item.description} />
          {item.proof && <Row label="Proof of ownership" value={item.proof} />}
          <Row label="Good-faith statement" value={item.good_faith ? "Yes" : "No"} />
          <Row label="Accuracy statement" value={item.accuracy ? "Yes" : "No"} />
        </dl>

        <div className="flex flex-col gap-4 border-t border-white/10 pt-6">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold uppercase tracking-widest text-white/40">
              Status
            </label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as AdminTakedown["status"])}
              className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white outline-none focus:border-wave-400/50"
            >
              {STATUS_FLOW.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold uppercase tracking-widest text-white/40">
              Internal notes
            </label>
            <textarea
              rows={4}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Add review notes…"
              className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-sm text-white placeholder:text-white/25 outline-none focus:border-wave-400/50"
            />
          </div>

          <button
            onClick={save}
            disabled={busy}
            className="w-full rounded-xl bg-white/10 py-2.5 text-sm font-semibold text-white transition hover:bg-white/20 disabled:opacity-50"
          >
            {saved ? "Saved" : busy ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-white/40">{label}</dt>
      <dd className="mt-0.5 text-white/85 whitespace-pre-wrap">{value}</dd>
    </div>
  );
}

export default function AdminTakedownsPage() {
  const [items, setItems] = useState<AdminTakedown[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<AdminTakedown | null>(null);

  useEffect(() => {
    listTakedowns()
      .then(setItems)
      .finally(() => setLoading(false));
  }, []);

  function handleUpdate(updated: AdminTakedown) {
    setItems((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    setSelected(updated);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Takedown Requests</h1>

      {loading ? (
        <p className="text-white/40 text-sm">Loading…</p>
      ) : items.length === 0 ? (
        <div className="glass rounded-2xl p-8 text-center">
          <p className="text-white/50 text-sm">No takedown requests yet.</p>
        </div>
      ) : (
        <div className="glass rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10">
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest text-white/40">
                  Date
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest text-white/40">
                  Claimant
                </th>
                <th className="hidden md:table-cell px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest text-white/40">
                  Infringing URL
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest text-white/40">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  onClick={() => setSelected(item)}
                  className="border-b border-white/5 cursor-pointer transition hover:bg-white/5 last:border-0"
                >
                  <td className="px-4 py-3 text-white/60 whitespace-nowrap">
                    {formatDate(item.submitted_at)}
                  </td>
                  <td className="px-4 py-3 text-white font-medium">
                    {item.claimant_name}
                    {item.organization && (
                      <span className="ml-1 text-white/40 font-normal">
                        ({item.organization})
                      </span>
                    )}
                  </td>
                  <td className="hidden md:table-cell px-4 py-3 text-white/50 max-w-xs truncate">
                    {item.infringing_url}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={item.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <TakedownDrawer
          item={selected}
          onClose={() => setSelected(null)}
          onUpdate={handleUpdate}
        />
      )}
    </div>
  );
}
