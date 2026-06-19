"use client";

import { useEffect, useRef, useState } from "react";
import { Play, Pause, Volume2, VolumeX, AlertTriangle, User } from "lucide-react";
import type { TrackItem } from "@/features/channels/types/channel";
import { recordPlay } from "@/features/channels/lib/channelApi";

interface ChannelPlayerProps {
  tracks: TrackItem[];
  coverImage: string;
  title: string;
  slug: string;
  visualLoopUrl?: string | null;
  hostName: string;
  genre: string;
  mood: string;
}

export function ChannelPlayer({ tracks, coverImage, title, slug, visualLoopUrl, hostName, genre, mood }: ChannelPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const playingRef = useRef(false);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(0.8);
  const [errored, setErrored] = useState(false);

  // When the track list changes (channel swap), reset to track 0.
  useEffect(() => {
    setCurrentIndex(0);
    setErrored(false);
  }, [tracks]);

  // Primary sync: keep video in lockstep with audio playing state.
  useEffect(() => {
    playing ? videoRef.current?.play() : videoRef.current?.pause();
  }, [playing]);

  // Called when the browser has buffered enough to play the current src.
  // Uses playingRef (not state) to avoid stale closure when advancing tracks.
  function handleCanPlay() {
    const a = audioRef.current;
    if (!a || !playingRef.current) return;
    a.play().catch(() => { setPlaying(false); playingRef.current = false; });
  }

  function handleEnded() {
    setCurrentIndex((i) => (i + 1) % tracks.length);
  }

  function togglePlay() {
    const a = audioRef.current;
    if (!a) return;
    if (a.paused) {
      playingRef.current = true;
      setPlaying(true);
      a.play().catch(() => { setPlaying(false); playingRef.current = false; });
      // Fire-and-forget play count — once per slug per session.
      if (typeof window !== "undefined") {
        const key = `wp_played_${slug}`;
        if (!sessionStorage.getItem(key)) {
          sessionStorage.setItem(key, "1");
          recordPlay(slug);
        }
      }
    } else {
      playingRef.current = false;
      a.pause();
      videoRef.current?.pause();
      setPlaying(false);
    }
  }

  function handleVolumeChange(e: React.ChangeEvent<HTMLInputElement>) {
    const a = audioRef.current;
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (a) {
      a.volume = val;
      a.muted = val === 0;
    }
    setMuted(val === 0);
  }

  function toggleMute() {
    const a = audioRef.current;
    if (!a) return;
    const next = !muted;
    a.muted = next;
    if (!next) a.volume = volume || 0.8;
    setMuted(next);
  }

  if (errored) {
    return (
      <div className="flex aspect-video w-full flex-col items-center justify-center gap-3 rounded-2xl border border-amber-400/30 bg-amber-400/5 p-6 text-center">
        <AlertTriangle className="h-8 w-8 text-amber-300" />
        <p className="text-sm font-medium text-amber-100">
          This media couldn&apos;t be loaded.
        </p>
        <p className="max-w-sm text-xs text-amber-100/70">
          The host may be offline, blocked, or the URL may need updating in seed
          data. Try again later.
        </p>
      </div>
    );
  }

  const currentTrack = tracks[currentIndex];
  const trackSrc = currentTrack?.url ?? "";

  return (
    <div className="group relative w-full overflow-hidden rounded-2xl border border-white/10 bg-black shadow-2xl shadow-black/50">
      {/* Visual backdrop: looping muted video when available, else static cover.
          Audio (incl. playlist cycling) is driven by the <audio> element below. */}
      {visualLoopUrl ? (
        <video
          ref={videoRef}
          src={visualLoopUrl}
          loop
          muted
          playsInline
          poster={coverImage}
          aria-hidden="true"
          className="aspect-video w-full object-cover"
        />
      ) : (
        <img
          src={coverImage}
          alt={`${title} channel art`}
          className="aspect-video w-full object-cover"
        />
      )}

      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        src={trackSrc}
        preload="auto"
        onCanPlay={handleCanPlay}
        onError={() => setErrored(true)}
        onPlay={() => { videoRef.current?.play(); setPlaying(true); }}
        onPause={() => { videoRef.current?.pause(); setPlaying(false); }}
        onEnded={handleEnded}
      />

      {/* Overlay — channel info (top) + now-playing + controls (bottom) */}
      <div className="absolute inset-x-0 bottom-0 flex flex-col gap-2 bg-gradient-to-t from-black/80 to-transparent px-4 pt-8 pb-4">
        {/* Row 1: title + host */}
        <div>
          <p className="truncate text-sm font-semibold leading-tight text-white">{title}</p>
          <p className="flex items-center gap-1 text-xs text-white/60">
            <User className="h-3 w-3 shrink-0" /> Hosted by {hostName}
          </p>
        </div>

        {/* Row 2: now-playing — only shown when track has metadata */}
        {currentTrack?.title && (
          <p className="truncate text-xs text-white/90">
            {currentTrack.artist && (
              <span className="text-white/60">{currentTrack.artist} — </span>
            )}
            {currentTrack.title}
          </p>
        )}

        {/* Row 3: controls + tags + track counter */}
        <div className="flex items-center gap-3">
          {/* Play / Pause */}
          <button
            onClick={togglePlay}
            aria-label={playing ? "Pause" : "Play"}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white/15 text-white backdrop-blur-sm transition hover:bg-white/25 active:scale-95"
          >
            {playing ? (
              <Pause className="h-5 w-5 fill-current" />
            ) : (
              <Play className="h-5 w-5 translate-x-px fill-current" />
            )}
          </button>

          {/* Mute toggle */}
          <button
            onClick={toggleMute}
            aria-label={muted ? "Unmute" : "Mute"}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white/70 transition hover:text-white"
          >
            {muted ? (
              <VolumeX className="h-4 w-4" />
            ) : (
              <Volume2 className="h-4 w-4" />
            )}
          </button>

          {/* Volume slider */}
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={muted ? 0 : volume}
            onChange={handleVolumeChange}
            aria-label="Volume"
            className="h-1 w-24 cursor-pointer appearance-none rounded-full bg-white/20 accent-white"
          />

          {/* Genre + mood tags + track counter */}
          <div className="ml-auto flex items-center gap-2">
            <div className="hidden sm:flex gap-1.5">
              <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-white/70">{genre}</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-white/70">{mood}</span>
            </div>
            {tracks.length > 1 && (
              <span className="text-xs font-medium text-white/50">
                Track {currentIndex + 1} of {tracks.length}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
