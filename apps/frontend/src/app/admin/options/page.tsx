"use client";

import { useEffect, useState } from "react";
import { getOptions, updateOptions } from "@/features/admin/lib/adminApi";
import type { SubmissionOptions } from "@/features/admin/types/admin";
import { X, Plus } from "lucide-react";

const FIELDS = ["genre", "mood", "energy", "theme"] as const;
type Field = (typeof FIELDS)[number];

function OptionList({
  field,
  options: initial,
}: {
  field: Field;
  options: string[];
}) {
  const [options, setOptions] = useState(initial);
  const [input, setInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  function add() {
    const v = input.trim();
    if (!v || options.includes(v)) return;
    setOptions((prev) => [...prev, v]);
    setInput("");
  }

  function remove(opt: string) {
    setOptions((prev) => prev.filter((o) => o !== opt));
  }

  async function save() {
    setSaving(true);
    await updateOptions(field, options);
    setSaved(true);
    setSaving(false);
    setTimeout(() => setSaved(false), 2000);
  }

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-white/10 bg-white/5 p-5">
      <h2 className="text-sm font-semibold capitalize text-white">{field}</h2>
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => (
          <span
            key={opt}
            className="flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/80"
          >
            {opt}
            <button onClick={() => remove(opt)} className="text-white/30 hover:text-red-400 transition">
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), add())}
          placeholder={`Add ${field}…`}
          className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white placeholder-white/30 outline-none focus:border-white/30"
        />
        <button
          onClick={add}
          className="flex items-center gap-1 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-white/70 hover:bg-white/10 transition"
        >
          <Plus className="h-4 w-4" /> Add
        </button>
      </div>
      <button
        onClick={save}
        disabled={saving}
        className="w-fit rounded-lg bg-white/10 px-4 py-1.5 text-sm font-medium text-white transition hover:bg-white/20 disabled:opacity-50"
      >
        {saving ? "Saving…" : saved ? "Saved ✓" : "Save"}
      </button>
    </div>
  );
}

export default function OptionsPage() {
  const [opts, setOpts] = useState<SubmissionOptions | null>(null);

  useEffect(() => {
    getOptions().then(setOpts);
  }, []);

  if (!opts) return <p className="text-sm text-white/40">Loading…</p>;

  return (
    <div>
      <h1 className="mb-6 text-xl font-semibold text-white">Submission Options</h1>
      <div className="grid gap-5 sm:grid-cols-2">
        {FIELDS.map((f) => (
          <OptionList key={f} field={f} options={opts[f]} />
        ))}
      </div>
    </div>
  );
}
