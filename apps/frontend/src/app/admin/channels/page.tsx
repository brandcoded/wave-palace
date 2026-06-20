"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { listAdminChannels, updateChannel } from "@/features/admin/lib/adminApi";
import type { AdminChannel } from "@/features/admin/types/admin";
import { Plus, Eye, EyeOff, Loader2, Clock, CheckCircle, XCircle } from "lucide-react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

type ChannelMuxState = { state: "pending" | "running" | "done" | "error"; url: string | null; error: string | null };
type MuxJobStatus = { running: boolean; channels: Record<string, ChannelMuxState> };

export default function AdminChannelsPage() {
  const [channels, setChannels] = useState<AdminChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [muxingAll, setMuxingAll] = useState(false);
  const [muxStatus, setMuxStatus] = useState("");
  const [muxJob, setMuxJob] = useState<MuxJobStatus | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    listAdminChannels().then((data) => {
      setChannels(data);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  async function togglePublish(ch: AdminChannel) {
    const updated = await updateChannel(ch.slug, { isPublished: !ch.isPublished });
    setChannels((prev) => prev.map((c) => (c.slug === ch.slug ? { ...c, ...updated } : c)));
  }

  async function handleMuxAll() {
    setMuxingAll(true);
    setMuxStatus("");
    setMuxJob(null);
    try {
      const res = await fetch(`${API_BASE}/api/mux/all`, { method: "POST", credentials: "include" });
      if (!res.ok) throw new Error();
      pollRef.current = setInterval(async () => {
        try {
          const statusRes = await fetch(`${API_BASE}/api/mux/status`, { credentials: "include" });
          const data: MuxJobStatus = await statusRes.json();
          setMuxJob(data);
          if (!data.running) {
            clearInterval(pollRef.current!);
            pollRef.current = null;
            setMuxingAll(false);
            listAdminChannels().then(setChannels);
          }
        } catch {
          setMuxStatus("Could not fetch status — job may still be running.");
        }
      }, 3000);
    } catch {
      setMuxStatus("Update failed to start.");
      setMuxingAll(false);
    }
  }

  const hasOutdated = channels.some((ch) => ch.muxOutdated);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">Channels</h1>
        <div className="flex items-center gap-3">
          {hasOutdated && (
            <button
              onClick={handleMuxAll}
              disabled={muxingAll}
              className="flex items-center gap-2 rounded-lg bg-amber-500/20 px-4 py-2 text-sm font-medium text-amber-300 transition hover:bg-amber-500/30 disabled:opacity-50"
            >
              {muxingAll && <Loader2 className="h-4 w-4 animate-spin" />}
              Update All VR Videos
            </button>
          )}
          <Link
            href="/admin/channels/new"
            className="flex items-center gap-2 rounded-lg bg-white/10 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/20"
          >
            <Plus className="h-4 w-4" /> New Channel
          </Link>
        </div>
      </div>
      {muxStatus && (
        <div className="mb-4 rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-sm text-amber-100">
          {muxStatus}
        </div>
      )}
      {muxJob && (() => {
        const entries = Object.entries(muxJob.channels);
        const doneCount = entries.filter(([, c]) => c.state === "done").length;
        const totalCount = entries.length;
        const pct = totalCount > 0 ? (doneCount / totalCount) * 100 : 0;
        return (
          <div className="mb-4 min-h-[120px] rounded-xl border border-white/10 bg-white/5 p-4">
            <p className="mb-3 text-sm font-medium text-white">
              {muxJob.running ? "Updating VR videos…" : "VR video update complete"}
            </p>
            <div className="mb-1 flex items-center gap-3">
              <div className="flex-1 h-1.5 rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-amber-400 transition-all duration-500"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="shrink-0 text-xs text-white/50">{doneCount} / {totalCount} done</span>
            </div>
            <div className="mt-3 flex flex-col gap-1.5">
              {entries.map(([slug, ch]) => (
                <div key={slug} className="flex items-center gap-2 text-sm">
                  {ch.state === "done" && <CheckCircle className="h-4 w-4 shrink-0 text-emerald-400" />}
                  {ch.state === "running" && <Loader2 className="h-4 w-4 shrink-0 animate-spin text-amber-300" />}
                  {ch.state === "pending" && <Clock className="h-4 w-4 shrink-0 text-white/30" />}
                  {ch.state === "error" && <XCircle className="h-4 w-4 shrink-0 text-red-400" />}
                  <span className={
                    ch.state === "done" ? "text-white/80" :
                    ch.state === "running" ? "text-amber-200" :
                    ch.state === "error" ? "text-red-300" :
                    "text-white/40"
                  }>{slug}</span>
                  {ch.state === "running" && <span className="text-xs text-white/40">(running)</span>}
                  {ch.state === "pending" && <span className="text-xs text-white/30">(pending)</span>}
                  {ch.state === "error" && ch.error && <span className="text-xs text-red-400/70">{ch.error}</span>}
                </div>
              ))}
            </div>
          </div>
        );
      })()}

      {loading ? (
        <p className="text-sm text-white/40">Loading…</p>
      ) : (
        <>
          {/* Desktop table */}
          <table className="hidden lg:table w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-left text-xs text-white/40">
                <th className="pb-2 pr-4">Title</th>
                <th className="pb-2 pr-4">Genre</th>
                <th className="pb-2 pr-4">Mood</th>
                <th className="pb-2 pr-4 text-right">Plays</th>
                <th className="pb-2 text-center">Published</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {channels.map((ch) => (
                <tr key={ch.slug} className="border-b border-white/5">
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                      <Link
                        href={`/admin/channels/${ch.slug}`}
                        className="font-medium text-white hover:text-cyan-400 transition"
                      >
                        {ch.title}
                      </Link>
                      {ch.muxOutdated && (
                        <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-amber-300">
                          VR outdated
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3 pr-4 text-white/60">{ch.genre}</td>
                  <td className="py-3 pr-4 text-white/60">{ch.mood}</td>
                  <td className="py-3 pr-4 text-right text-white/60">{ch.playCount ?? 0}</td>
                  <td className="py-3 text-center">
                    <button
                      onClick={() => togglePublish(ch)}
                      className={`transition ${ch.isPublished ? "text-emerald-400 hover:text-emerald-300" : "text-white/30 hover:text-white/60"}`}
                      title={ch.isPublished ? "Published — click to unpublish" : "Unpublished — click to publish"}
                    >
                      {ch.isPublished ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                    </button>
                  </td>
                  <td className="py-3 pl-2">
                    <Link
                      href={`/admin/channels/${ch.slug}`}
                      className="text-xs text-white/30 hover:text-white/60"
                    >
                      Edit
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Mobile card list */}
          <div className="flex flex-col gap-3 lg:hidden">
            {channels.map((ch) => (
              <div
                key={ch.slug}
                className="rounded-xl border border-white/10 bg-white/5 p-4"
              >
                <div className="mb-3 flex items-start justify-between gap-2">
                  <div>
                    <Link
                      href={`/admin/channels/${ch.slug}`}
                      className="font-medium text-white leading-snug hover:text-cyan-400 transition"
                    >
                      {ch.title}
                    </Link>
                    {ch.muxOutdated && (
                      <div className="mt-1 inline-block rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-amber-300">
                        VR outdated
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => togglePublish(ch)}
                    className={`shrink-0 transition ${ch.isPublished ? "text-emerald-400" : "text-white/30"}`}
                    title={ch.isPublished ? "Published" : "Unpublished"}
                  >
                    {ch.isPublished ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                  </button>
                </div>
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-white/50">
                  {ch.genre && <span>{ch.genre}</span>}
                  {ch.mood && <span>{ch.mood}</span>}
                  <span>{ch.playCount ?? 0} plays</span>
                </div>
                <Link
                  href={`/admin/channels/${ch.slug}`}
                  className="mt-3 inline-block text-xs text-white/30 hover:text-white/60 transition"
                >
                  Edit →
                </Link>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
