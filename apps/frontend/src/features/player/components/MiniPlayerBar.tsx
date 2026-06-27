"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Play, Pause, Music } from "lucide-react";
import { useAudioPlayer } from "@/features/player/context/AudioPlayerContext";

export function MiniPlayerBar() {
  const player = useAudioPlayer();
  const pathname = usePathname();

  // Hide when nothing is loaded or when already on the channel page.
  if (!player.channelSlug || pathname.startsWith("/channels/")) return null;

  return (
    <div className="fixed bottom-0 inset-x-0 z-50 border-t border-white/10 bg-ink-900/95 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
        {/* Thumbnail */}
        <div className="h-9 w-9 shrink-0 overflow-hidden rounded-lg bg-white/5">
          {player.coverImageUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={player.coverImageUrl} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full w-full items-center justify-center">
              <Music className="h-4 w-4 text-white/30" />
            </div>
          )}
        </div>

        {/* Channel + track info */}
        <div className="min-w-0 flex-1">
          <p className="truncate text-xs font-semibold text-white">{player.channelName}</p>
          {(player.trackTitle || player.trackArtist) && (
            <p className="truncate text-xs text-white/50">
              {player.trackArtist && <span>{player.trackArtist} — </span>}
              {player.trackTitle}
            </p>
          )}
        </div>

        {/* Play / pause */}
        <button
          onClick={() => (player.isPlaying ? player.pause() : player.resume())}
          aria-label={player.isPlaying ? "Pause" : "Resume"}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/10 text-white transition hover:bg-white/20 active:scale-95"
        >
          {player.isPlaying ? (
            <Pause className="h-4 w-4 fill-current" />
          ) : (
            <Play className="h-4 w-4 translate-x-px fill-current" />
          )}
        </button>

        {/* Deep-link back to the channel page */}
        {player.channelUrl && (
          <Link
            href={player.channelUrl}
            className="shrink-0 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/70 transition hover:bg-white/10 hover:text-white"
          >
            Open
          </Link>
        )}
      </div>
    </div>
  );
}
