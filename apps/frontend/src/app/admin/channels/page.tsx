"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listAdminChannels, updateChannel } from "@/features/admin/lib/adminApi";
import type { AdminChannel } from "@/features/admin/types/admin";
import { Plus, Eye, EyeOff, Loader2 } from "lucide-react";

export default function AdminChannelsPage() {
  const [channels, setChannels] = useState<AdminChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [muxingAll, setMuxingAll] = useState(false);
  const [muxStatus, setMuxStatus] = useState("");

  useEffect(() => {
    listAdminChannels().then((data) => {
      setChannels(data);
      setLoading(false);
    });
  }, []);

  async function togglePublish(ch: AdminChannel) {
    const updated = await updateChannel(ch.slug, { isPublished: !ch.isPublished });
    setChannels((prev) => prev.map((c) => (c.slug === ch.slug ? { ...c, ...updated } : c)));
  }

  async function handleMuxAll() {
    setMuxingAll(true);
    setMuxStatus("VR video update started — this may take several minutes per channel.");
    try {
      const res = await fetch("/api/mux/all", { method: "POST" });
      if (!res.ok) throw new Error("Failed to start mux job");
      setMuxStatus("Updates queued. Check back in a few minutes.");
    } catch {
      setMuxStatus("Update failed to start.");
    } finally {
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
