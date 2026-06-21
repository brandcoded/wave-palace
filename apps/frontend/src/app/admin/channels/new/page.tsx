"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { createChannel, getOptions } from "@/features/admin/lib/adminApi";
import type { SubmissionOptions } from "@/features/admin/types/admin";
import Link from "next/link";

function Field({
  label,
  name,
  form,
  setField,
  required,
}: {
  label: string;
  name: string;
  form: Record<string, unknown>;
  setField: (key: string, value: string | boolean | string[]) => void;
  required?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-white/50">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      <input
        type="text"
        value={(form[name] as string) ?? ""}
        onChange={(e) => setField(name, e.target.value)}
        required={required}
        className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-white/30"
      />
    </div>
  );
}

function MultiSelectChips({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string[];
  onChange: (values: string[]) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-white/50">{label}</label>
      <div className="flex flex-wrap gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-2 min-h-[40px]">
        {options.map((opt) => {
          const selected = value.includes(opt);
          return (
            <button
              key={opt}
              type="button"
              onClick={() =>
                onChange(selected ? value.filter((v) => v !== opt) : [...value, opt])
              }
              className={`rounded-full px-3 py-0.5 text-xs font-medium transition ${
                selected
                  ? "bg-cyan-500/30 text-cyan-200 border border-cyan-400/40"
                  : "bg-white/5 text-white/40 border border-white/10 hover:bg-white/10 hover:text-white/70"
              }`}
            >
              {opt}
            </button>
          );
        })}
        {options.length === 0 && (
          <span className="text-xs text-white/20">Loading options…</span>
        )}
      </div>
    </div>
  );
}

export default function NewChannelPage() {
  const router = useRouter();
  const [form, setForm] = useState<{
    title: string;
    description: string;
    genre: string[];
    mood: string[];
    energy: string[];
    theme: string[];
    hostName: string;
    coverImageUrl: string;
    audioUrl: string;
    isPublished: boolean;
  }>({
    title: "",
    description: "",
    genre: [],
    mood: [],
    energy: [],
    theme: [],
    hostName: "",
    coverImageUrl: "",
    audioUrl: "",
    isPublished: false,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [channelOptions, setChannelOptions] = useState<SubmissionOptions>({ genre: [], mood: [], energy: [], theme: [] });

  useEffect(() => {
    getOptions().then(setChannelOptions).catch(() => {});
  }, []);

  function setField(key: string, value: string | boolean | string[]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const ch = await createChannel(form as Parameters<typeof createChannel>[0]);
      router.push(`/admin/channels/${ch.slug}`);
    } catch (err) {
      setError(String(err));
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <Link href="/admin/channels" className="text-xs text-white/40 hover:text-white/70">
          ← Channels
        </Link>
        <h1 className="mt-1 text-xl font-semibold text-white">New Channel</h1>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Title" name="title" form={form} setField={setField} required />
          <Field label="Host name" name="hostName" form={form} setField={setField} />
          <Field label="Cover image URL" name="coverImageUrl" form={form} setField={setField} />
          <Field label="Audio URL" name="audioUrl" form={form} setField={setField} required />
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <MultiSelectChips
            label="Genre"
            options={channelOptions.genre}
            value={form.genre}
            onChange={(vals) => setField("genre", vals)}
          />
          <MultiSelectChips
            label="Mood"
            options={channelOptions.mood}
            value={form.mood}
            onChange={(vals) => setField("mood", vals)}
          />
          <MultiSelectChips
            label="Energy"
            options={channelOptions.energy}
            value={form.energy}
            onChange={(vals) => setField("energy", vals)}
          />
          <MultiSelectChips
            label="Theme"
            options={channelOptions.theme}
            value={form.theme}
            onChange={(vals) => setField("theme", vals)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-medium text-white/50">Description</label>
          <textarea
            value={form.description}
            onChange={(e) => setField("description", e.target.value)}
            rows={3}
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-white/30 resize-none"
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-white/60">
          <input
            type="checkbox"
            checked={form.isPublished}
            onChange={(e) => setField("isPublished", e.target.checked)}
            className="accent-cyan-400"
          />
          Publish immediately
        </label>
        {error && <p className="text-xs text-red-400">{error}</p>}
        <button
          type="submit"
          disabled={saving}
          className="w-fit rounded-lg bg-white/10 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-white/20 disabled:opacity-50"
        >
          {saving ? "Creating…" : "Create channel"}
        </button>
      </form>
    </div>
  );
}
