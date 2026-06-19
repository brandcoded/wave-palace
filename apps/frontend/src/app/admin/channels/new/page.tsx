"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createChannel } from "@/features/admin/lib/adminApi";
import Link from "next/link";

export default function NewChannelPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    title: "",
    description: "",
    genre: "",
    mood: "",
    energy: "",
    theme: "",
    hostName: "",
    coverImageUrl: "",
    audioUrl: "",
    isPublished: false,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function setField(key: string, value: string | boolean) {
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

  const Field = ({
    label,
    name,
    required,
  }: {
    label: string;
    name: string;
    required?: boolean;
  }) => (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-white/50">
        {label} {required && <span className="text-red-400">*</span>}
      </label>
      <input
        type="text"
        value={(form as Record<string, unknown>)[name] as string ?? ""}
        onChange={(e) => setField(name, e.target.value)}
        required={required}
        className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-white/30"
      />
    </div>
  );

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <Link href="/admin/channels" className="text-xs text-white/40 hover:text-white/70">
          ← Channels
        </Link>
        <h1 className="mt-1 text-xl font-semibold text-white">New Channel</h1>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Title" name="title" required />
          <Field label="Host name" name="hostName" />
          <Field label="Genre" name="genre" />
          <Field label="Mood" name="mood" />
          <Field label="Energy" name="energy" />
          <Field label="Theme" name="theme" />
          <Field label="Cover image URL" name="coverImageUrl" />
          <Field label="Audio URL" name="audioUrl" required />
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
