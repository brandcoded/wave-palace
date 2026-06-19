"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listAdminChannels, updateChannel } from "@/features/admin/lib/adminApi";
import type { AdminChannel } from "@/features/admin/types/admin";
import { Plus, Eye, EyeOff } from "lucide-react";

export default function AdminChannelsPage() {
  const [channels, setChannels] = useState<AdminChannel[]>([]);
  const [loading, setLoading] = useState(true);

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

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">Channels</h1>
        <Link
          href="/admin/channels/new"
          className="flex items-center gap-2 rounded-lg bg-white/10 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/20"
        >
          <Plus className="h-4 w-4" /> New Channel
        </Link>
      </div>

      {loading ? (
        <p className="text-sm text-white/40">Loading…</p>
      ) : (
        <table className="w-full text-sm">
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
                  <Link
                    href={`/admin/channels/${ch.slug}`}
                    className="font-medium text-white hover:text-cyan-400 transition"
                  >
                    {ch.title}
                  </Link>
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
      )}
    </div>
  );
}
