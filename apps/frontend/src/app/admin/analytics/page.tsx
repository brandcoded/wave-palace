"use client";

import { useEffect, useState } from "react";
import { getAnalytics } from "@/features/admin/lib/adminApi";
import type { AnalyticsSummary, ChannelStat } from "@/features/admin/types/admin";

function fmt(n: number) {
  return n.toLocaleString("en-US");
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="glass rounded-2xl px-5 py-4 flex flex-col gap-1">
      <span className="text-2xl font-bold text-white">{value}</span>
      <span className="text-xs font-semibold uppercase tracking-widest text-white/40">{label}</span>
    </div>
  );
}

function FollowPill({
  label,
  count,
  color,
}: {
  label: string;
  count: number;
  color: string;
}) {
  return (
    <div className={`flex items-center gap-2 rounded-full border px-4 py-1.5 ${color}`}>
      <span className="text-sm font-bold">{fmt(count)}</span>
      <span className="text-xs text-white/60">{label}</span>
    </div>
  );
}

function StreamingBadge({ active }: { active: boolean }) {
  return active ? (
    <span className="text-emerald-400">✅</span>
  ) : (
    <span className="text-white/20">—</span>
  );
}

function ChannelRow({ ch }: { ch: ChannelStat }) {
  const muted = !ch.is_published;
  return (
    <tr className={`border-b border-white/5 last:border-0 ${muted ? "opacity-40" : ""}`}>
      <td className="px-4 py-3">
        <div className="font-medium text-white">{ch.title}</div>
        <div className="text-xs text-white/40 font-mono">{ch.slug}</div>
      </td>
      <td className="px-4 py-3 text-white/70 text-sm">{ch.host_name}</td>
      <td className="px-4 py-3 text-white text-sm font-mono">{fmt(ch.play_count)}</td>
      <td className="px-4 py-3 text-white/80 text-sm">{fmt(ch.follow_count)}</td>
      <td className="px-4 py-3 text-white/60 text-sm">{ch.follow_breakdown.discord}</td>
      <td className="px-4 py-3 text-white/60 text-sm">{ch.follow_breakdown.email}</td>
      <td className="px-4 py-3 text-white/60 text-sm">{ch.follow_breakdown.browser_push}</td>
      <td className="px-4 py-3 text-white/60 text-sm">
        {ch.active_code_count > 0 ? (
          <span className="font-mono">{ch.active_code_count} active</span>
        ) : (
          <span className="text-white/20">—</span>
        )}
      </td>
      <td className="px-4 py-3">
        <StreamingBadge active={ch.streaming_active} />
      </td>
    </tr>
  );
}

export default function AdminAnalyticsPage() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAnalytics()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">Analytics</h1>
        <p className="text-white/40 text-sm">Loading…</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-white">Analytics</h1>
        <p className="text-red-400 text-sm">{error ?? "Failed to load analytics."}</p>
      </div>
    );
  }

  const generatedAt = new Date(data.generated_at).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  });

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-white">Analytics</h1>

      {/* Summary stat cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total Plays" value={fmt(data.total_plays)} />
        <StatCard label="Total Follows" value={fmt(data.total_follows)} />
        <StatCard
          label="Channels Live"
          value={`${data.published_channels} / ${data.total_channels}`}
        />
        <StatCard label="With Sponsor" value={fmt(data.channels_with_sponsor)} />
      </div>

      {/* Follow breakdown */}
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-xs font-semibold uppercase tracking-widest text-white/40 mr-1">
          Follows by channel
        </span>
        <FollowPill
          label="Discord"
          count={data.follow_breakdown.discord}
          color="border-indigo-400/30 bg-indigo-400/10 text-indigo-300"
        />
        <FollowPill
          label="Email"
          count={data.follow_breakdown.email}
          color="border-sky-400/30 bg-sky-400/10 text-sky-300"
        />
        <FollowPill
          label="Browser Push"
          count={data.follow_breakdown.browser_push}
          color="border-violet-400/30 bg-violet-400/10 text-violet-300"
        />
      </div>

      {/* Channel leaderboard */}
      <div className="glass rounded-2xl overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10">
              {[
                "Channel",
                "Host",
                "Plays",
                "Follows",
                "Discord",
                "Email",
                "Push",
                "Codes",
                "Streaming",
              ].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-widest text-white/40 whitespace-nowrap"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.top_channels.map((ch) => (
              <ChannelRow key={ch.slug} ch={ch} />
            ))}
          </tbody>
        </table>
        <p className="px-4 py-3 text-xs text-white/25 border-t border-white/5">
          Generated at {generatedAt} · Unpublished channels shown muted
        </p>
      </div>
    </div>
  );
}
