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
  listAdminChannels,
  listChannelOwners,
  generateChannelInvite,
  removeChannelOwner,
  moveChannelOwner,
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

// ---------------------------------------------------------------------------
// Video renderer templates — keep in sync with the renderer registry in
// apps/renderer/src/templates/index.ts. Adding a template = one entry here.
// ---------------------------------------------------------------------------

const TEMPLATE_OPTIONS: { id: string; label: string; description: string }[] = [
  {
    id: "split-screen",
    label: "Split Screen",
    description: "Square art panel + right-side now-playing info panel.",
  },
  {
    id: "full-bleed",
    label: "Full Bleed Overlay",
    description: "Full-frame backdrop with centered visualizer + bottom info band (matches the current VRChat video).",
  },
  // add new templates here to match the renderer registry
];

// ---------------------------------------------------------------------------
// Visualizer admin helpers
// ---------------------------------------------------------------------------

const VIZ_STYLE_LABELS: Record<string, string> = {
  none: "None", waveform: "Waveform", bars: "Bars",
  circular: "Circular", blob: "Blob", terrain: "Terrain",
};

const VIZ_THEME_COLORS: Record<string, string> = {
  violet: "#a78bfa", teal: "#2dd4bf", ember: "#fb923c",
  rose:   "#fb7185", ice:  "#bae6fd", frequency: "",
};

function VisualizerThumbnail({ style, theme, selected, onClick }: {
  style: string; theme: string; selected: boolean; onClick: () => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef    = useRef<number>(0);
  const tRef      = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    function frame() {
      rafRef.current = requestAnimationFrame(frame);
      tRef.current += 0.028;
      const t = tRef.current;
      const c = canvas!.getContext("2d");
      if (!c) return;
      const W = 80, H = 48;
      c.clearRect(0, 0, W, H);

      const color = VIZ_THEME_COLORS[theme] || "#a78bfa";
      const n = 48;
      const freq = new Float32Array(n);
      for (let i = 0; i < n; i++) {
        const band = i / n;
        freq[i] = Math.min(1, Math.max(0,
          (band < 0.15 ? (Math.sin(t * 2.1) * 0.45 + 0.5) * 0.85 : 0) +
          (Math.sin(t * 1.3 + band * 9) * 0.28 + 0.35) * (band > 0.08 && band < 0.6 ? 0.65 : 0.1),
        ));
      }
      const td = new Float32Array(96);
      for (let i = 0; i < 96; i++) {
        td[i] = Math.sin(t * 2 + (i / 96) * Math.PI * 4) * 0.38 + 0.5 + Math.sin(t * 5 + i * 0.2) * 0.07;
      }

      if (style === "none") {
        c.beginPath(); c.strokeStyle = color + "50"; c.lineWidth = 1;
        c.moveTo(0, H / 2); c.lineTo(W, H / 2); c.stroke();
      } else if (style === "waveform") {
        c.beginPath(); c.strokeStyle = color + "cc"; c.lineWidth = 1.5;
        for (let i = 0; i < td.length - 1; i++) {
          const x1 = (i / td.length) * W, y1 = td[i] * H;
          const x2 = ((i+1) / td.length) * W, y2 = td[i+1] * H;
          const mx = (x1+x2)/2, my = (y1+y2)/2;
          if (i === 0) c.moveTo(x1, y1); else c.quadraticCurveTo(x1, y1, mx, my);
        }
        c.stroke();
      } else if (style === "bars") {
        for (let i = 0; i < n; i++) {
          const bW = W/n - 0.5, x = (i/n)*W, bH = freq[i]*H;
          c.fillStyle = (theme === "frequency" ? `hsl(${(i/n)*240},75%,60%)` : color) + "99";
          c.fillRect(x, H-bH, bW, bH);
        }
      } else if (style === "circular") {
        const cx = W/2, cy = H/2, r0 = Math.min(W,H)*0.22;
        for (let i = 0; i < n; i++) {
          const ang = (i/n)*Math.PI*2 - Math.PI/2;
          const r = r0 + freq[i]*r0*0.65;
          c.beginPath(); c.moveTo(cx+Math.cos(ang)*r0, cy+Math.sin(ang)*r0);
          c.lineTo(cx+Math.cos(ang)*r, cy+Math.sin(ang)*r);
          c.strokeStyle = color + "cc"; c.lineWidth = 1; c.stroke();
        }
        c.beginPath(); c.arc(cx, cy, r0, 0, Math.PI*2);
        c.strokeStyle = color + "30"; c.lineWidth = 0.75; c.stroke();
      } else if (style === "blob") {
        const m = 32, cx = W/2, cy = H/2, r0 = Math.min(W,H)*0.18;
        c.beginPath();
        for (let i = 0; i <= m; i++) {
          const idx = i%m, ang = (idx/m)*Math.PI*2-Math.PI/2;
          const r = r0 + freq[idx%n]*r0*0.7;
          const x = cx+Math.cos(ang)*r, y = cy+Math.sin(ang)*r;
          const nI = (idx+1)%m, nA = (nI/m)*Math.PI*2-Math.PI/2;
          const nr = r0 + freq[nI%n]*r0*0.7;
          const nx = cx+Math.cos(nA)*nr, ny = cy+Math.sin(nA)*nr;
          if (i===0) c.moveTo((x+nx)/2,(y+ny)/2); else c.quadraticCurveTo(x,y,(x+nx)/2,(y+ny)/2);
        }
        c.closePath(); c.fillStyle = color+"18"; c.fill();
        c.strokeStyle = color+"cc"; c.lineWidth = 1.5; c.stroke();
      } else if (style === "terrain") {
        c.beginPath();
        for (let i = 0; i <= n; i++) {
          const idx = i%n, x = (idx/n)*W, y = H - freq[idx]*H*0.8 - H*0.04;
          if (i===0) { c.moveTo(x,y); } else {
            const pi=(i-1)%n, px=(pi/n)*W, py=H-freq[pi]*H*0.8-H*0.04;
            c.quadraticCurveTo(px,py,(px+x)/2,(py+y)/2);
          }
        }
        c.lineTo(W,H); c.lineTo(0,H); c.closePath();
        c.fillStyle = color+"20"; c.fill(); c.strokeStyle = color+"bb"; c.lineWidth = 1.5; c.stroke();
      }
    }

    frame();
    return () => cancelAnimationFrame(rafRef.current);
  }, [style, theme]);

  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex flex-col items-center gap-1 rounded-lg border p-1 transition ${
        selected
          ? "border-cyan-400/60 bg-cyan-400/10"
          : "border-white/10 bg-white/5 hover:border-white/20"
      }`}
    >
      <canvas ref={canvasRef} width={80} height={48} className="rounded" />
      <span className={`text-[9px] font-semibold uppercase tracking-widest ${selected ? "text-cyan-300" : "text-white/40"}`}>
        {VIZ_STYLE_LABELS[style] ?? style}
      </span>
    </button>
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
  const [otherChannels, setOtherChannels] = useState<{ slug: string; title: string }[]>([]);
  const [movingOwner, setMovingOwner] = useState<string | null>(null);
  const [moveToast, setMoveToast] = useState<string | null>(null);

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
    listAdminChannels()
      .then((all) => setOtherChannels(all.filter((c) => c.slug !== slug).map((c) => ({ slug: c.slug, title: c.title }))))
      .catch(() => {});
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

  async function handleMoveOwner(ownerId: string, toSlug: string) {
    const target = otherChannels.find((c) => c.slug === toSlug);
    if (!target) return;
    setMovingOwner(ownerId);
    try {
      await moveChannelOwner(slug, ownerId, toSlug);
      setOwners((prev) => prev.filter((o) => o.id !== ownerId));
      setMoveToast(`Moved to ${target.title}`);
      setTimeout(() => setMoveToast(null), 3000);
    } catch {
      // error is shown inline via the select resetting — nothing more needed
    } finally {
      setMovingOwner(null);
    }
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
    } catch (err) {
      clearInterval(interval);
      muxIntervalRef.current = null;
      setMuxStatus(err instanceof Error ? err.message : "Update failed — try again.");
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

        {/* Visualizer */}
        <section className="flex flex-col gap-3">
          <h2 className="text-xs font-bold uppercase tracking-widest text-white/30">Audio Visualizer</h2>
          <p className="text-xs text-white/40">Shown on the web player during playback. VRChat mux burns a white version into the video.</p>

          <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
            {(["none", "waveform", "bars", "circular", "blob", "terrain"] as const).map((s) => (
              <VisualizerThumbnail
                key={s}
                style={s}
                theme={(form.visualizer_theme as string) ?? "violet"}
                selected={((form.visualizer_style as string) ?? "none") === s}
                onClick={() => setForm((prev) => ({ ...prev, visualizer_style: s }))}
              />
            ))}
          </div>

          {((form.visualizer_style as string) ?? "none") !== "none" && (
            <>
              <label className="text-xs font-medium text-white/50">Color theme</label>
              <div className="flex flex-wrap gap-2">
                {(["violet", "teal", "ember", "rose", "ice", "frequency"] as const).map((th) => (
                  <button
                    key={th}
                    type="button"
                    onClick={() => setForm((prev) => ({ ...prev, visualizer_theme: th }))}
                    className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium border transition ${
                      ((form.visualizer_theme as string) ?? "violet") === th
                        ? "border-white/40 bg-white/15 text-white"
                        : "border-white/10 bg-white/5 text-white/50 hover:bg-white/10"
                    }`}
                  >
                    {th === "frequency" ? (
                      <span className="h-3 w-3 rounded-full flex-shrink-0" style={{ background: "linear-gradient(90deg,#ef4444,#22c55e,#3b82f6)" }} />
                    ) : (
                      <span className="h-3 w-3 rounded-full flex-shrink-0" style={{ background: VIZ_THEME_COLORS[th] }} />
                    )}
                    {th}
                  </button>
                ))}
              </div>

              <label className="text-xs font-medium text-white/50">Backdrop mode</label>
              <div className="flex gap-2 flex-wrap">
                {(["overlay_video", "overlay_image", "replace"] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setForm((prev) => ({ ...prev, visualizer_backdrop: m }))}
                    className={`rounded-full px-3 py-1 text-xs font-medium border transition ${
                      ((form.visualizer_backdrop as string) ?? "overlay_video") === m
                        ? "border-cyan-400/60 bg-cyan-400/10 text-cyan-300"
                        : "border-white/10 bg-white/5 text-white/50 hover:bg-white/10"
                    }`}
                  >
                    {m === "overlay_video" ? "Video + strip" : m === "overlay_image" ? "Image + strip" : "Replace backdrop"}
                  </button>
                ))}
              </div>
            </>
          )}
        </section>

        {/* Video Renderer Template */}
        <section className="flex flex-col gap-3">
          <h2 className="text-xs font-bold uppercase tracking-widest text-white/30">Video Renderer Template</h2>
          <p className="text-xs text-white/40">Applied when rendering this channel&apos;s video stream overlay.</p>
          <div className="flex flex-col gap-2">
            {TEMPLATE_OPTIONS.map((opt) => {
              const selected = ((form.renderer_template as string) ?? "split-screen") === opt.id;
              return (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setForm((prev) => ({ ...prev, renderer_template: opt.id }))}
                  className={`flex flex-col gap-0.5 rounded-lg border px-4 py-3 text-left transition ${
                    selected
                      ? "border-cyan-400/60 bg-cyan-400/10"
                      : "border-white/10 bg-white/5 hover:border-white/20"
                  }`}
                >
                  <span className={`text-sm font-medium ${selected ? "text-cyan-300" : "text-white/80"}`}>
                    {opt.label}
                  </span>
                  <span className="text-[11px] text-white/40">{opt.description}</span>
                </button>
              );
            })}
          </div>
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

          {moveToast && (
            <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300">
              <CheckCircle className="h-3.5 w-3.5 shrink-0" />
              {moveToast}
            </div>
          )}

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
                  <div className="flex items-center gap-3">
                    {movingOwner === o.id ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-white/30" />
                    ) : (
                      otherChannels.length > 0 && (
                        <select
                          defaultValue=""
                          disabled={movingOwner !== null}
                          onChange={(e) => {
                            if (e.target.value) handleMoveOwner(o.id, e.target.value);
                            e.target.value = "";
                          }}
                          className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-white/70 outline-none focus:border-white/30 disabled:opacity-40"
                        >
                          <option value="" disabled>Move to…</option>
                          {otherChannels.map((c) => (
                            <option key={c.slug} value={c.slug}>{c.title}</option>
                          ))}
                        </select>
                      )
                    )}
                    <button
                      onClick={() => handleRemoveOwner(o.id)}
                      disabled={movingOwner !== null}
                      className="text-xs text-red-400/50 hover:text-red-400 disabled:opacity-40"
                    >
                      Remove
                    </button>
                  </div>
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
