"use client";

import { useState } from "react";
import Link from "next/link";
import { Heart, Play, User } from "lucide-react";
import type { Channel } from "@/features/channels/types/channel";
import { unsaveChannel } from "@/features/me/lib/meApi";

const tagClass =
  "rounded-full border border-white/10 bg-white/5 px-2.5 py-0.5 text-[11px] font-medium text-white/70";

const isFeaturedSponsor = (channel: Channel): boolean => {
  const s = channel.sponsor;
  if (!s || !s.isActive || !s.isFeatured) return false;
  const now = Date.now();
  if (s.startDate && now < new Date(s.startDate).getTime()) return false;
  if (s.endDate && now > new Date(s.endDate).getTime()) return false;
  return true;
};

interface ChannelCardProps {
  channel: Channel;
  initialSaved?: boolean;
}

const API_BASE =
  typeof process !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://localhost:8000")
    : "http://localhost:8000";

export function ChannelCard({ channel, initialSaved = false }: ChannelCardProps) {
  const [saved, setSaved] = useState(initialSaved);
  const [savePending, setSavePending] = useState(false);
  const featured = isFeaturedSponsor(channel);

  async function handleSaveToggle(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (savePending) return;
    setSavePending(true);
    const next = !saved;
    setSaved(next); // optimistic
    try {
      if (next) {
        const res = await fetch(`${API_BASE}/api/me/saves/${channel.slug}`, {
          method: "POST",
          credentials: "include",
        });
        if (res.status === 401) {
          setSaved(false);
          window.location.href = "/admin/login";
          return;
        }
        if (!res.ok) setSaved(false);
      } else {
        await unsaveChannel(channel.slug);
      }
    } catch {
      setSaved(!next);
    } finally {
      setSavePending(false);
    }
  }

  return (
    <Link
      href={`/channels/${channel.slug}`}
      className="group relative flex flex-col overflow-hidden rounded-3xl border border-white/10 bg-ink-900/60 transition duration-300 hover:-translate-y-1 hover:border-wave-500/40 hover:shadow-2xl hover:shadow-wave-600/20"
    >
      <div className="relative aspect-[16/10] overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={channel.coverImageUrl}
          alt={`${channel.title} cover art`}
          className="h-full w-full object-cover transition duration-500 group-hover:scale-105"
          loading="lazy"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-ink-950 via-ink-950/30 to-transparent" />
        <div className="absolute bottom-3 left-3 flex flex-wrap gap-1.5">
          {channel.genre.map((g) => <span key={g} className={tagClass}>{g}</span>)}
          {channel.mood.map((m) => <span key={m} className={tagClass}>{m}</span>)}
        </div>
        <div className="absolute right-3 top-3 flex items-center gap-2">
          {featured && (
            <span className="rounded-full bg-wave-500/80 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-white backdrop-blur-sm">
              Sponsored
            </span>
          )}
          <button
            onClick={handleSaveToggle}
            aria-label={saved ? "Unsave channel" : "Save channel"}
            className={`flex h-8 w-8 items-center justify-center rounded-full transition ${
              saved
                ? "bg-wave-500/80 text-white"
                : "bg-black/40 text-white/50 opacity-0 group-hover:opacity-100 hover:text-white"
            }`}
          >
            <Heart className="h-3.5 w-3.5" fill={saved ? "currentColor" : "none"} />
          </button>
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-wave-500/90 text-white opacity-0 shadow-lg transition duration-300 group-hover:opacity-100">
            <Play className="h-4 w-4 translate-x-[1px]" fill="currentColor" />
          </div>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-3 p-5">
        <h3 className="text-lg font-semibold tracking-tight">{channel.title}</h3>
        <p className="line-clamp-2 text-sm leading-relaxed text-white/55">
          {channel.description}
        </p>
        <div className="mt-auto flex items-center justify-between pt-2">
          <span className="flex items-center gap-1.5 text-xs text-white/50">
            <User className="h-3.5 w-3.5" />
            {channel.hostName}
          </span>
          <div className="flex flex-wrap gap-1.5">
            {channel.energy.map((e) => <span key={e} className={tagClass}>{e}</span>)}
            {channel.theme.map((t) => <span key={t} className={tagClass}>{t}</span>)}
          </div>
        </div>
      </div>
    </Link>
  );
}
