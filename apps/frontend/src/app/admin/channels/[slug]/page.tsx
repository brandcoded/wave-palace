"use client";

import { useEffect, useRef, useState } from "react";
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
  validateChannelUrls,
  updateChannelSponsor,
  getOptions,
  createCode,
  deactivateCode,
  listCodes,
  listChannelOwners,
  generateChannelInvite,
  removeChannelOwner,
  type AdminCode,
  type ChannelOwner,
} from "@/features/admin/lib/adminApi";
import type { AdminChannel, Sponsor, URLCheckResult, SubmissionOptions } from "@/features/admin/types/admin";
import type { TrackItem } from "@/features/channels/types/channel";
import { GripVertical, Trash2, Plus, Loader2, CheckCircle, AlertTriangle, XCircle, AlertCircle } from "lucide-react";
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
  const [muxElapsed, setMuxElapsed] = useState(0);
  const muxIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [codes, setCodes] = useState<AdminCode[]>([]);
  const [codesBusy, setCodesBusy] = useState(false);
  const [codeCopied, setCodeCopied] = useState<string | null>(null);
  const [validating, setValidating] = useState(false);
  const [urlResults, setUrlResults] = useState<URLCheckResult[] | null>(null);
  const [sponsorForm, setSponsorForm] = useState<Sponsor | null>(null);
  const [savingSponsor, setSavingSponsor] = useState(false);
  const [channelOptions, setChannelOptions] = useState<SubmissionOptions>({ genre: [], mood: [], energy: [], theme: [] });
  const [owners, setOwners] = useState<ChannelOwner[]>([]);
  const [inviteUrl, setInviteUrl] = useState<string | null>(null);
  const [inviteBusy, setInviteBusy] = useState(false);
  const [inviteCopied, setInviteCopied] = useState(false);

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
      setSponsorForm((ch as AdminChannel & { sponsor?: Sponsor | null }).sponsor ?? null);
    });
    getOptions().then(setChannelOptions).catch(() => {});
    listCodes().then((all) => setCodes(all.filter((c) => c.channel_slug === slug))).catch(() => {});
    listChannelOwners(slug).then(setOwners).catch(() => {});
  }, [slug]);

  async function handleGenerateInvite() {
    setInviteBusy(true);
    try {
      const invite = await generateChannelInvite(slug);
      setInviteUrl(invite.invite_url);
      setInviteCopied(false);
    } finally {
      setInviteBusy(false);
    }
  }

  async function handleRemoveOwner(ownerId: string) {
    if (!window.confirm("Remove this host from the channel?")) return;
    const next = owners.filter((o) => o.id !== ownerId);
    await removeChannelOwner(slug, next.map((o) => o.id));
    setOwners(next);
  }

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
    // owner_ids is managed via the invite/remove actions, not this form — drop it
    // so a content save can't clobber ownership changed since page load.
    const { owner_ids: _ownerIds, ...rest } = form;
    await updateChannel(slug, { ...rest, playlist });
    setSaving(false);
    router.push("/admin/channels");
  }

  function formatElapsed(s: number): string {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, "0")}`;
  }

  async function handleMuxVideo() {
    setMuxing(true);
    setMuxStatus("");
    setMuxElapsed(0);
    const interval = setInterval(() => setMuxElapsed((s) => s + 1), 1000);
    muxIntervalRef.current = interval;
    try {
      await muxChannel(slug);
      clearInterval(interval);
      muxIntervalRef.current = null;
      setMuxStatus("Done — VRChat video updated.");
      if (channel) setChannel({ ...channel, muxOutdated: false });
      setTimeout(() => setMuxStatus(""), 4000);
    } catch {
      clearInterval(interval);
      muxIntervalRef.current = null;
      setMuxStatus("Update failed — try again.");
    } finally {
      setMuxing(false);
    }
  }

  async function handleDelete() {
    await deleteChannel(slug);
    router.push("/admin/channels");
  }

  async function handleSaveSponsor() {
    setSavingSponsor(true);
    try {
      await updateChannelSponsor(slug, sponsorForm);
    } finally {
      setSavingSponsor(false);
    }
  }

  async function handleClearSponsor() {
    setSavingSponsor(true);
    try {
      await updateChannelSponsor(slug, null);
      setSponsorForm(null);
    } finally {
      setSavingSponsor(false);
    }
  }

  function setSponsorField<K extends keyof Sponsor>(key: K, value: Sponsor[K]) {
    setSponsorForm((prev) => ({
      ...(prev ?? {
        name: "", logoUrl: null, text: "", clickUrl: null,
        placement: "lower_third" as const, startDate: null, endDate: null,
        isActive: true, isFeatured: false, impressionCount: 0, clickCount: 0,
      }),
      [key]: value,
    }));
  }

  async function handleValidateUrls() {
    setValidating(true);
    setUrlResults(null);
    try {
      const results = await validateChannelUrls(slug);
      setUrlResults(results);
    } catch {
      setUrlResults([]);
    } finally {
      setValidating(false);
    }
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

      {channel.muxOutdated && (
        <div className="mb-6 rounded-lg border border-amber-400/30 bg-amber-400/5 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 shrink-0 text-amber-400 mt-0.5" />
            <div className="flex-1">
              <p className="font-medium text-amber-100">VR video is out of date</p>
              <p className="mt-1 text-sm text-amber-100/70">
                Channel info, tracks, or sponsor changed since the last video update.
              </p>
              <button
                onClick={handleMuxVideo}
                disabled={muxing}
                className="mt-3 rounded-lg bg-amber-500/20 px-3 py-1.5 text-sm font-medium text-amber-300 transition hover:bg-amber-500/30 disabled:opacity-50 flex items-center gap-2"
              >
                {muxing && <Loader2 className="h-4 w-4 animate-spin" />}
                {muxing ? `Updating VR Video… ${formatElapsed(muxElapsed)}` : "Update VR Video"}
              </button>
              {muxStatus && (
                <p className="mt-2 text-sm text-amber-100">{muxStatus}</p>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-col gap-8">
        {/* Channel info */}
        <section className="flex flex-col gap-4">
          <h2 className="text-xs font-bold uppercase tracking-widest text-white/30">Channel info</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Title" name="title" form={form} setField={setField} />
            <Field label="Host name" name="hostName" form={form} setField={setField} />
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <MultiSelectChips
              label="Genre"
              options={channelOptions.genre}
              value={(form.genre as string[]) ?? []}
              onChange={(vals) => setField("genre", vals as AdminChannel["genre"])}
            />
            <MultiSelectChips
              label="Mood"
              options={channelOptions.mood}
              value={(form.mood as string[]) ?? []}
              onChange={(vals) => setField("mood", vals as AdminChannel["mood"])}
            />
            <MultiSelectChips
              label="Energy"
              options={channelOptions.energy}
              value={(form.energy as string[]) ?? []}
              onChange={(vals) => setField("energy", vals as AdminChannel["energy"])}
            />
            <MultiSelectChips
              label="Theme"
              options={channelOptions.theme}
              value={(form.theme as string[]) ?? []}
              onChange={(vals) => setField("theme", vals as AdminChannel["theme"])}
            />
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
          <Field label="Visual loop URL (MP4)" name="visualLoopUrl" form={form} setField={setField} />
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

        {/* VRChat mux & streaming */}
        <section className="flex flex-col gap-3">
          <h2 className="text-xs font-bold uppercase tracking-widest text-white/30">VRChat — mux &amp; streaming</h2>

          {/* Streaming toggle */}
          <label className="flex items-center gap-2 text-sm text-white/60">
            <input
              type="checkbox"
              checked={(form.streamingActive as boolean) ?? false}
              onChange={(e) => setField("streamingActive", e.target.checked)}
              className="accent-cyan-400"
            />
            Streaming active (VRChat uses live stream URL)
          </label>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-white/50">Live stream URL for VRChat</label>
            <input
              type="text"
              value={(form.vrchatFallbackUrl as string) ?? ""}
              onChange={(e) => setField("vrchatFallbackUrl", e.target.value)}
              placeholder="https://…/live.m3u8 or .ts"
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-white/30"
            />
          </div>

          {/* Mux controls */}
          <p className="text-xs text-white/40">Re-mux after changing tracks, cover image, or visual loop.</p>
          <div className="flex items-center gap-3">
            <button
              onClick={handleMuxVideo}
              disabled={muxing}
              className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/70 transition hover:bg-white/10 disabled:opacity-50"
            >
              {muxing && <Loader2 className="h-4 w-4 animate-spin" />}
              {muxing ? `Re-muxing… ${formatElapsed(muxElapsed)}` : "Re-mux for VRChat"}
            </button>
            {!muxing && muxStatus && <span className="text-xs text-white/50">{muxStatus}</span>}
          </div>
          {form.vrchatPlaybackUrl && (
            <p className="truncate text-xs text-white/30">{form.vrchatPlaybackUrl as string}</p>
          )}
        </section>

        {/* Sponsor */}
        <section className="flex flex-col gap-4">
          <h2 className="text-xs font-bold uppercase tracking-widest text-white/30">Sponsor</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-white/50">Sponsor name</label>
              <input
                value={sponsorForm?.name ?? ""}
                onChange={(e) => setSponsorField("name", e.target.value)}
                placeholder="e.g. Neon Drinks Co."
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-white/30"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-white/50">Placement</label>
              <select
                value={sponsorForm?.placement ?? "lower_third"}
                onChange={(e) => setSponsorField("placement", e.target.value as Sponsor["placement"])}
                className="rounded-lg border border-white/10 bg-black/60 px-3 py-2 text-sm text-white outline-none focus:border-white/30"
              >
                <option value="lower_third">Lower third</option>
                <option value="bug">Bug (corner logo)</option>
                <option value="backdrop">Backdrop</option>
              </select>
            </div>
            <div className="flex flex-col gap-1.5 sm:col-span-2">
              <label className="text-xs font-medium text-white/50">Logo URL</label>
              <input
                value={sponsorForm?.logoUrl ?? ""}
                onChange={(e) => setSponsorField("logoUrl", e.target.value || null)}
                placeholder="https://…"
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-white/30"
              />
            </div>
            <div className="flex flex-col gap-1.5 sm:col-span-2">
              <label className="text-xs font-medium text-white/50">Display text</label>
              <input
                value={sponsorForm?.text ?? ""}
                onChange={(e) => setSponsorField("text", e.target.value)}
                placeholder="Brought to you by …"
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-white/30"
              />
            </div>
            <div className="flex flex-col gap-1.5 sm:col-span-2">
              <label className="text-xs font-medium text-white/50">Click URL</label>
              <input
                value={sponsorForm?.clickUrl ?? ""}
                onChange={(e) => setSponsorField("clickUrl", e.target.value || null)}
                placeholder="https://…"
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-white/30"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-white/50">Start date (optional)</label>
              <input
                type="datetime-local"
                value={sponsorForm?.startDate?.slice(0, 16) ?? ""}
                onChange={(e) => setSponsorField("startDate", e.target.value ? e.target.value + ":00Z" : null)}
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-white/30 [color-scheme:dark]"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-white/50">End date (optional)</label>
              <input
                type="datetime-local"
                value={sponsorForm?.endDate?.slice(0, 16) ?? ""}
                onChange={(e) => setSponsorField("endDate", e.target.value ? e.target.value + ":00Z" : null)}
                className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-white/30 [color-scheme:dark]"
              />
            </div>
          </div>
          <div className="flex gap-6">
            <label className="flex items-center gap-2 text-sm text-white/60">
              <input
                type="checkbox"
                checked={sponsorForm?.isActive ?? true}
                onChange={(e) => setSponsorField("isActive", e.target.checked)}
                className="accent-cyan-400"
              />
              Active
            </label>
            <label className="flex items-center gap-2 text-sm text-white/60">
              <input
                type="checkbox"
                checked={sponsorForm?.isFeatured ?? false}
                onChange={(e) => setSponsorField("isFeatured", e.target.checked)}
                className="accent-cyan-400"
              />
              Featured (pin to top of directory)
            </label>
          </div>
          {sponsorForm && (
            <p className="text-xs text-white/30">
              Impressions: {sponsorForm.impressionCount ?? 0} · Clicks: {sponsorForm.clickCount ?? 0}
            </p>
          )}
          <div className="flex gap-3">
            <button
              onClick={handleSaveSponsor}
              disabled={savingSponsor}
              className="rounded-lg bg-white/10 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/20 disabled:opacity-50"
            >
              {savingSponsor ? "Saving…" : "Save sponsor"}
            </button>
            {sponsorForm && (
              <button
                onClick={handleClearSponsor}
                disabled={savingSponsor}
                className="rounded-lg border border-white/10 px-4 py-2 text-sm text-white/50 transition hover:border-white/20 hover:text-white/70 disabled:opacity-50"
              >
                Clear sponsor
              </button>
            )}
          </div>
        </section>

        {/* URL checker */}
        <section className="flex flex-col gap-3">
          <h2 className="text-xs font-bold uppercase tracking-widest text-white/30">URL health</h2>
          <p className="text-xs text-white/40">Check that all audio and video URLs are reachable and VRChat-compatible.</p>
          <button
            onClick={handleValidateUrls}
            disabled={validating}
            className="flex min-h-[40px] items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/70 transition hover:bg-white/10 disabled:opacity-50"
          >
            {validating && <Loader2 className="h-4 w-4 animate-spin" />}
            {validating ? "Checking…" : "Check URLs"}
          </button>
          {urlResults !== null && (
            <div className="flex flex-col gap-2">
              {urlResults.length === 0 ? (
                <p className="text-xs text-white/40">No URLs to check on this channel.</p>
              ) : (
                urlResults.map((r) => (
                  <div
                    key={r.url}
                    className={`rounded-lg border px-3 py-2 text-xs ${
                      !r.ok
                        ? "border-red-400/20 bg-red-400/5"
                        : r.warnings.length > 0
                        ? "border-amber-400/20 bg-amber-400/5"
                        : "border-emerald-400/20 bg-emerald-400/5"
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      {!r.ok ? (
                        <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
                      ) : r.warnings.length > 0 ? (
                        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
                      ) : (
                        <CheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                      )}
                      <div className="flex flex-col gap-1 min-w-0">
                        <span className="break-all text-white/60">{r.url}</span>
                        {r.warnings.map((w, i) => (
                          <span key={i} className={r.ok ? "text-amber-300/80" : "text-red-300/80"}>
                            {w}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </section>

        {/* Ownership (Slice 11) */}
        <section className="flex flex-col gap-4 border-t border-white/10 pt-6">
          <h2 className="text-xs font-bold uppercase tracking-widest text-white/40">Ownership</h2>

          {owners.length === 0 ? (
            <p className="text-xs text-white/30">No hosts assigned. Generate an invite link to onboard one.</p>
          ) : (
            <ul className="space-y-2">
              {owners.map((o) => (
                <li key={o.id} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-4 py-2">
                  <div className="flex items-center gap-3">
                    {o.avatar_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={o.avatar_url} alt="" className="h-7 w-7 rounded-full object-cover ring-1 ring-white/10" />
                    ) : (
                      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white/10 text-xs font-semibold text-white/60">
                        {o.display_name.charAt(0).toUpperCase()}
                      </span>
                    )}
                    <span className="text-sm text-white/80">{o.display_name}</span>
                  </div>
                  <button
                    onClick={() => handleRemoveOwner(o.id)}
                    className="text-xs text-red-400/50 hover:text-red-400"
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="flex flex-col gap-2">
            <button
              onClick={handleGenerateInvite}
              disabled={inviteBusy}
              className="self-start rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold text-white/60 transition hover:bg-white/10 hover:text-white disabled:opacity-40"
            >
              {inviteBusy ? "Generating…" : "Generate Invite Link"}
            </button>
            {inviteUrl && (
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center gap-2">
                  <input
                    readOnly
                    value={inviteUrl}
                    onFocus={(e) => e.target.select()}
                    className="flex-1 rounded-lg border border-white/10 bg-black/60 px-3 py-2 text-xs text-white/70 outline-none"
                  />
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(inviteUrl);
                      setInviteCopied(true);
                      setTimeout(() => setInviteCopied(false), 2000);
                    }}
                    className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/60 transition hover:bg-white/10"
                  >
                    {inviteCopied ? "Copied!" : "Copy"}
                  </button>
                </div>
                <p className="text-xs text-amber-300/70">This link expires in 7 days and can only be used once.</p>
              </div>
            )}
          </div>

          <label className="flex items-start gap-2 text-sm text-white/60">
            <input
              type="checkbox"
              checked={!(form.auto_publish ?? true)}
              onChange={(e) => setField("auto_publish", !e.target.checked)}
              className="mt-0.5 accent-cyan-400"
            />
            <span>
              Require music director approval before host can publish changes
              <span className="mt-0.5 block text-xs text-white/30">
                When on, host edits go to pending review instead of publishing directly.
              </span>
            </span>
          </label>
        </section>

        {/* Follow Codes */}
        <section className="flex flex-col gap-4 border-t border-white/10 pt-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-widest text-white/40">Follow Codes</h2>
            <button
              onClick={async () => {
                setCodesBusy(true);
                try {
                  const code = await createCode(slug, slug);
                  setCodes((prev) => [code, ...prev]);
                } finally {
                  setCodesBusy(false);
                }
              }}
              disabled={codesBusy}
              className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold text-white/60 transition hover:bg-white/10 hover:text-white disabled:opacity-40"
            >
              {codesBusy ? "Generating…" : "+ Generate code"}
            </button>
          </div>
          {codes.filter((c) => c.active).length === 0 ? (
            <p className="text-xs text-white/30">No active codes for this channel.</p>
          ) : (
            <ul className="space-y-2">
              {codes.filter((c) => c.active).map((c) => (
                <li key={c.code} className="flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-4 py-2">
                  <span className="font-mono font-bold tracking-widest text-wave-400">{c.code}</span>
                  <div className="flex gap-3">
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(`${window.location.origin}/follow/${c.code}`);
                        setCodeCopied(c.code);
                        setTimeout(() => setCodeCopied(null), 2000);
                      }}
                      className="text-xs text-white/40 hover:text-white"
                    >
                      {codeCopied === c.code ? "Copied!" : "Copy link"}
                    </button>
                    <button
                      onClick={async () => {
                        await deactivateCode(c.code);
                        setCodes((prev) => prev.map((x) => x.code === c.code ? { ...x, active: false } : x));
                      }}
                      className="text-xs text-red-400/50 hover:text-red-400"
                    >
                      Deactivate
                    </button>
                  </div>
                </li>
              ))}
            </ul>
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
