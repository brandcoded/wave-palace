"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  updateChannel,
  deleteChannel,
  uploadImage,
  uploadVideo,
  uploadAudio,
  muxChannel,
} from "@/features/admin/lib/adminApi";
import type { AdminChannel } from "@/features/admin/types/admin";
import type { TrackItem } from "@/features/channels/types/channel";
import { GripVertical, Trash2, Plus, Loader2 } from "lucide-react";
import Link from "next/link";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function fetchChannel(slug: string): Promise<AdminChannel> {
  const res = await fetch(`${API_BASE}/api/admin/channels`, { credentials: "include" });
  const all: AdminChannel[] = await res.json();
  const ch = all.find((c) => c.slug === slug);
  if (!ch) throw new Error("Channel not found");
  return ch;
}

type TrackRow = TrackItem & { _id: string };

function SortableTrack({
  track,
  onChange,
  onDelete,
}: {
  track: TrackRow;
  onChange: (id: string, field: keyof TrackItem, value: string) => void;
  onDelete: (id: string) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: track._id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2"
    >
      <button
        {...attributes}
        {...listeners}
        className="cursor-grab text-white/30 hover:text-white/60 active:cursor-grabbing"
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <input
        value={track.title}
        onChange={(e) => onChange(track._id, "title", e.target.value)}
        placeholder="Track title"
        className="flex-1 bg-transparent text-sm text-white outline-none placeholder-white/30"
      />
      <input
        value={track.artist}
        onChange={(e) => onChange(track._id, "artist", e.target.value)}
        placeholder="Artist"
        className="w-36 bg-transparent text-sm text-white/70 outline-none placeholder-white/30"
      />
      <button
        onClick={() => onDelete(track._id)}
        className="text-white/30 hover:text-red-400 transition"
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
  );
}

function UploadButton({
  label,
  accept,
  onUpload,
}: {
  label: string;
  accept: string;
  onUpload: (file: File) => Promise<string>;
}) {
  const [uploading, setUploading] = useState(false);
  const [done, setDone] = useState(false);

  async function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await onUpload(file);
      setDone(true);
      setTimeout(() => setDone(false), 3000);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/70 transition hover:bg-white/10">
      {uploading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : done ? (
        <span className="text-emerald-400">✓</span>
      ) : (
        <Plus className="h-4 w-4" />
      )}
      {label}
      <input type="file" accept={accept} onChange={handleChange} className="sr-only" />
    </label>
  );
}

function Field({
  label,
  name,
  form,
  setField,
  type = "text",
  rows,
}: {
  label: string;
  name: keyof AdminChannel;
  form: Partial<AdminChannel>;
  setField: <K extends keyof AdminChannel>(key: K, value: AdminChannel[K]) => void;
  type?: string;
  rows?: number;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-white/50">{label}</label>
      {rows ? (
        <textarea
          value={(form[name] as string) ?? ""}
          onChange={(e) => setField(name, e.target.value as AdminChannel[typeof name])}
          rows={rows}
          className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-white/30 resize-none"
        />
      ) : (
        <input
          type={type}
          value={(form[name] as string) ?? ""}
          onChange={(e) => setField(name, e.target.value as AdminChannel[typeof name])}
          className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-white/30"
        />
      )}
    </div>
  );
}

export default function ChannelEditPage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const [channel, setChannel] = useState<AdminChannel | null>(null);
  const [form, setForm] = useState<Partial<AdminChannel>>({});
  const [tracks, setTracks] = useState<TrackRow[]>([]);
  const [saving, setSaving] = useState(false);
  const [muxing, setMuxing] = useState(false);
  const [muxStatus, setMuxStatus] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  useEffect(() => {
    fetchChannel(slug).then((ch) => {
      setChannel(ch);
      setForm(ch);
      setTracks(
        (ch.playlist ?? []).map((t, i) => ({ ...t, _id: `track-${i}-${Date.now()}` }))
      );
    });
  }, [slug]);

  function setField<K extends keyof AdminChannel>(key: K, value: AdminChannel[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleDragEnd(e: DragEndEvent) {
    const { active, over } = e;
    if (over && active.id !== over.id) {
      setTracks((items) => {
        const from = items.findIndex((t) => t._id === active.id);
        const to = items.findIndex((t) => t._id === over.id);
        return arrayMove(items, from, to);
      });
    }
  }

  function updateTrack(id: string, field: keyof TrackItem, value: string) {
    setTracks((prev) => prev.map((t) => (t._id === id ? { ...t, [field]: value } : t)));
  }

  function deleteTrack(id: string) {
    setTracks((prev) => prev.filter((t) => t._id !== id));
  }

  async function addTrack(file: File): Promise<string> {
    const { url } = await uploadAudio(file);
    const newTrack: TrackRow = {
      _id: `track-new-${Date.now()}`,
      url,
      title: file.name.replace(/\.mp3$/i, "").replace(/-/g, " "),
      artist: "",
    };
    setTracks((prev) => [...prev, newTrack]);
    return url;
  }

  async function handleSave() {
    setSaving(true);
    const playlist = tracks.map(({ _id: _ignore, ...t }) => t);
    await updateChannel(slug, { ...form, playlist });
    setSaving(false);
    router.push("/admin/channels");
  }

  async function handleMux() {
    setMuxing(true);
    setMuxStatus("Muxing…");
    try {
      await muxChannel(slug);
      setMuxStatus("Done ✓");
    } catch {
      setMuxStatus("Mux failed.");
    } finally {
      setMuxing(false);
    }
  }

  async function handleDelete() {
    await deleteChannel(slug);
    router.push("/admin/channels");
  }

  if (!channel) return <p className="text-sm text-white/40">Loading…</p>;

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link href="/admin/channels" className="text-xs text-white/40 hover:text-white/70">
            ← Channels
          </Link>
          <h1 className="mt-1 text-xl font-semibold text-white">{channel.title}</h1>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-white/60">
            <input
              type="checkbox"
              checked={form.isPublished ?? false}
              onChange={(e) => setField("isPublished", e.target.checked)}
              className="accent-cyan-400"
            />
            Published
          </label>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 sm:flex-none rounded-lg bg-white/10 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/20 disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>

      <div className="flex flex-col gap-8">
        {/* Channel info */}
        <section className="flex flex-col gap-4">
          <h2 className="text-xs font-bold uppercase tracking-widest text-white/30">Channel info</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Title" name="title" form={form} setField={setField} />
            <Field label="Host name" name="hostName" form={form} setField={setField} />
            <Field label="Genre" name="genre" form={form} setField={setField} />
            <Field label="Mood" name="mood" form={form} setField={setField} />
            <Field label="Energy" name="energy" form={form} setField={setField} />
            <Field label="Theme" name="theme" form={form} setField={setField} />
          </div>
          <Field label="Description" name="description" rows={3} form={form} setField={setField} />
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-white/50">Rights status</label>
            <select
              value={(form.rightsStatus as string) ?? "owned_or_cleared"}
              onChange={(e) => setField("rightsStatus", e.target.value)}
              className="rounded-lg border border-white/10 bg-black/60 px-3 py-2 text-sm text-white outline-none focus:border-white/30"
            >
              <option value="owned_or_cleared">Owned or cleared</option>
              <option value="licensed">Licensed</option>
              <option value="cleared_sample">Cleared sample</option>
            </select>
          </div>
        </section>

        {/* Cover image */}
        <section className="flex flex-col gap-3">
          <h2 className="text-xs font-bold uppercase tracking-widest text-white/30">Cover image</h2>
          {form.coverImageUrl && (
            <img
              src={form.coverImageUrl as string}
              alt="Cover"
              className="h-24 w-40 rounded-lg object-cover ring-1 ring-white/10"
            />
          )}
          <Field label="Cover image URL" name="coverImageUrl" form={form} setField={setField} />
          <UploadButton
            label="Upload image"
            accept="image/jpeg,image/png,image/webp"
            onUpload={async (file) => {
              const { url } = await uploadImage(file);
              setField("coverImageUrl", url);
              return url;
            }}
          />
        </section>

        {/* Visual loop */}
        <section className="flex flex-col gap-3">
          <h2 className="text-xs font-bold uppercase tracking-widest text-white/30">Visual loop</h2>
          <Field label="Visual loop URL (MP4)" name="visualLoopUrl" />
          <UploadButton
            label="Upload video loop"
            accept="video/mp4"
            onUpload={async (file) => {
              const { url } = await uploadVideo(file);
              setField("visualLoopUrl", url);
              return url;
            }}
          />
        </section>

        {/* Tracks */}
        <section className="flex flex-col gap-3">
          <h2 className="text-xs font-bold uppercase tracking-widest text-white/30">Tracks</h2>
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={tracks.map((t) => t._id)}
              strategy={verticalListSortingStrategy}
            >
              <div className="flex flex-col gap-2">
                {tracks.map((t) => (
                  <SortableTrack
                    key={t._id}
                    track={t}
                    onChange={updateTrack}
                    onDelete={deleteTrack}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
          <UploadButton
            label="Add track (MP3)"
            accept="audio/mpeg"
            onUpload={addTrack}
          />
        </section>

        {/* VRChat mux */}
        <section className="flex flex-col gap-3">
          <h2 className="text-xs font-bold uppercase tracking-widest text-white/30">VRChat mux</h2>
          <p className="text-xs text-white/40">Re-mux after changing tracks, cover image, or visual loop.</p>
          <div className="flex items-center gap-3">
            <button
              onClick={handleMux}
              disabled={muxing}
              className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/70 transition hover:bg-white/10 disabled:opacity-50"
            >
              {muxing && <Loader2 className="h-4 w-4 animate-spin" />}
              Re-mux for VRChat
            </button>
            {muxStatus && <span className="text-xs text-white/50">{muxStatus}</span>}
          </div>
          {form.vrchatPlaybackUrl && (
            <p className="truncate text-xs text-white/30">{form.vrchatPlaybackUrl as string}</p>
          )}
        </section>

        {/* Danger zone */}
        <section className="flex flex-col gap-3 border-t border-white/10 pt-6">
          <h2 className="text-xs font-bold uppercase tracking-widest text-red-400/60">Danger zone</h2>
          {confirmDelete ? (
            <div className="flex items-center gap-3">
              <span className="text-sm text-white/60">Delete this channel?</span>
              <button
                onClick={handleDelete}
                className="rounded-lg bg-red-500/20 px-3 py-1.5 text-sm text-red-300 hover:bg-red-500/30"
              >
                Confirm delete
              </button>
              <button
                onClick={() => setConfirmDelete(false)}
                className="text-sm text-white/40 hover:text-white/60"
              >
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmDelete(true)}
              className="w-fit rounded-lg border border-red-400/20 px-3 py-1.5 text-sm text-red-400/70 transition hover:border-red-400/40 hover:text-red-400"
            >
              Delete channel
            </button>
          )}
        </section>
      </div>
    </div>
  );
}
