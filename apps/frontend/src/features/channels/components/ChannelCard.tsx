import Link from "next/link";
import { Play, User } from "lucide-react";
import type { Channel } from "@/features/channels/types/channel";

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

export function ChannelCard({ channel }: { channel: Channel }) {
  const featured = isFeaturedSponsor(channel);
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
        <div className="absolute bottom-3 left-3 flex gap-2">
          <span className={tagClass}>{channel.genre}</span>
          <span className={tagClass}>{channel.mood}</span>
        </div>
        <div className="absolute right-3 top-3 flex items-center gap-2">
          {featured && (
            <span className="rounded-full bg-wave-500/80 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-white backdrop-blur-sm">
              Sponsored
            </span>
          )}
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
          <div className="flex gap-1.5">
            <span className={tagClass}>{channel.energy}</span>
            <span className={tagClass}>{channel.theme}</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
