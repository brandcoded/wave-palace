"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Play, Pause, Volume2, VolumeX, AlertTriangle, User, X } from "lucide-react";
import type { Sponsor, TrackItem } from "@/features/channels/types/channel";
import { recordPlay, recordSponsorImpression, recordSponsorClick } from "@/features/channels/lib/channelApi";
import { makeFollowCode } from "@/features/channels/lib/followCode";
import { useAudioVisualizer } from "@/features/channels/hooks/useAudioVisualizer";
import type { VisualizerStyle, VisualizerTheme } from "@/features/channels/hooks/useAudioVisualizer";

interface ChannelPlayerProps {
  tracks: TrackItem[];
  coverImage: string;
  title: string;
  slug: string;
  visualLoopUrl?: string | null;
  hostName: string;
  genre: string[];
  mood: string[];
  sponsor?: Sponsor | null;
  visualizerStyle?: VisualizerStyle;
  visualizerTheme?: VisualizerTheme;
  visualizerBackdrop?: "overlay_video" | "overlay_image" | "replace";
}

export function ChannelPlayer({ tracks, coverImage, title, slug, visualLoopUrl, hostName, genre, mood, sponsor, visualizerStyle, visualizerTheme, visualizerBackdrop }: ChannelPlayerProps) {
  const audioRef  = useRef<HTMLAudioElement>(null);
  const videoRef  = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const vizStyle  = visualizerStyle  ?? "none";
  const vizTheme  = visualizerTheme  ?? "violet";
  const vizBackdrop = visualizerBackdrop ?? "overlay_video";
  const [currentIndex, setCurrentIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const playingRef = useRef(false);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(0.8);
  const [errored, setErrored] = useState(false);
  const [sponsorDismissed, setSponsorDismissed] = useState(false);

  useAudioVisualizer(audioRef, canvasRef, vizStyle, vizTheme, playing);

  const sponsorActive =
    sponsor != null &&
    sponsor.isActive &&
    (() => {
      const now = Date.now();
      if (sponsor.startDate && now < new Date(sponsor.startDate).getTime()) return false;
      if (sponsor.endDate && now > new Date(sponsor.endDate).getTime()) return false;
      return true;
    })();

  // Fire impression once per slug per session when sponsor is live.
  useEffect(() => {
    if (!sponsorActive) return;
    const key = `wp_sponsor_${slug}`;
    if (typeof window !== "undefined" && !sessionStorage.getItem(key)) {
      sessionStorage.setItem(key, "1");
      recordSponsorImpression(slug);
    }
  }, [slug, sponsorActive]);

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

  function handleSponsorClick() {
    if (!sponsorActive || !sponsor?.clickUrl) return;
    recordSponsorClick(slug);
    window.open(sponsor.clickUrl, "_blank", "noopener,noreferrer");
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
  const followCode = currentTrack?.title
    ? makeFollowCode(slug, currentTrack.title, currentIndex)
    : null;
  const showBug = sponsorActive && sponsor!.placement === "bug" && sponsor!.logoUrl;
  const showLowerThird = sponsorActive && sponsor!.placement !== "bug";
  const showTakeover = sponsorActive && !playing && !sponsorDismissed;

  return (
    <div className="group relative w-full overflow-hidden rounded-2xl border border-white/10 bg-black shadow-2xl shadow-black/50">
      {/* Visual backdrop — hidden in replace mode */}
      {vizBackdrop !== "replace" && (vizBackdrop === "overlay_video" && visualLoopUrl ? (
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
      ))}

      {/* Replace mode: placeholder so the player keeps its aspect ratio */}
      {vizBackdrop === "replace" && (
        <div className="aspect-video w-full bg-black" />
      )}

      {/* Audio-reactive canvas visualizer */}
      {vizStyle !== "none" && (
        <canvas
          ref={canvasRef}
          className={
            vizBackdrop === "replace"
              ? "absolute inset-0 h-full w-full pointer-events-none"
              : "absolute inset-x-0 bottom-0 h-[120px] pointer-events-none"
          }
          style={{ zIndex: 2 }}
        />
      )}

      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        src={trackSrc}
        preload="auto"
        crossOrigin="anonymous"
        onCanPlay={handleCanPlay}
        onError={() => setErrored(true)}
        onPlay={() => { videoRef.current?.play(); setPlaying(true); }}
        onPause={() => { videoRef.current?.pause(); setPlaying(false); }}
        onEnded={handleEnded}
      />

      {/* Sponsor bug — corner logo (top-right) for placement="bug" */}
      {showBug && (
        <button
          onClick={handleSponsorClick}
          aria-label={`Sponsor: ${sponsor!.name}`}
          className="absolute top-3 right-3 rounded-lg bg-black/50 p-1.5 backdrop-blur-sm transition hover:bg-black/70"
        >
          <img
            src={sponsor!.logoUrl!}
            alt={sponsor!.name}
            className="h-7 w-auto max-w-[80px] object-contain"
          />
        </button>
      )}

      {/* Pause takeover — sponsor card when paused */}
      {showTakeover && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="relative mx-6 flex max-w-xs flex-col items-center gap-3 rounded-2xl border border-white/15 bg-black/80 px-6 py-5 text-center shadow-xl">
            <button
              onClick={() => setSponsorDismissed(true)}
              aria-label="Dismiss sponsor"
              className="absolute right-2 top-2 text-white/30 hover:text-white/60 transition"
            >
              <X className="h-4 w-4" />
            </button>
            {sponsor!.logoUrl && (
              <img
                src={sponsor!.logoUrl}
                alt={sponsor!.name}
                className="h-10 w-auto max-w-[140px] object-contain"
              />
            )}
            {sponsor!.text && (
              <p className="text-xs text-white/70">{sponsor!.text}</p>
            )}
            <p className="text-xs font-semibold text-white/50 uppercase tracking-widest">
              {sponsor!.name}
            </p>
            {sponsor!.clickUrl && (
              <button
                onClick={handleSponsorClick}
                className="rounded-full bg-white/10 px-4 py-1.5 text-xs font-medium text-white transition hover:bg-white/20"
              >
                Learn more
              </button>
            )}
          </div>
        </div>
      )}

      {/* Overlay — channel info + now-playing + controls */}
      <div className="absolute inset-x-0 bottom-0 flex flex-col gap-2 bg-gradient-to-t from-black/80 to-transparent px-4 pt-8 pb-4">
        {/* Row 1: title + host */}
        <div>
          <p className="truncate text-sm font-semibold leading-tight text-white">{title}</p>
          <p className="flex items-center gap-1 text-xs text-white/60">
            <User className="h-3 w-3 shrink-0" /> Hosted by {hostName}
          </p>
        </div>

        {/* Row 2: now-playing */}
        {currentTrack?.title && (
          <p className="truncate text-xs text-white/90">
            {currentTrack.artist && (
              <span className="text-white/60">{currentTrack.artist} — </span>
            )}
            {currentTrack.title}
          </p>
        )}

        {/* Row 3: sponsor lower-third */}
        {showLowerThird && (
          <button
            onClick={handleSponsorClick}
            className={`flex items-center gap-2 ${sponsor!.clickUrl ? "cursor-pointer hover:opacity-80" : "cursor-default"} transition`}
          >
            {sponsor!.logoUrl && (
              <img
                src={sponsor!.logoUrl}
                alt={sponsor!.name}
                className="h-4 w-auto max-w-[48px] object-contain opacity-70"
              />
            )}
            <span className="text-xs text-white/45">
              {sponsor!.text || `Sponsored by ${sponsor!.name}`}
            </span>
          </button>
        )}

        {/* Row 4: controls + tags + track counter */}
        <div className="flex items-center gap-3">
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

          <div className="ml-auto flex items-center gap-2">
            <div className="hidden sm:flex gap-1.5">
              {genre.map((g) => <span key={g} className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-white/70">{g}</span>)}
              {mood.map((m) => <span key={m} className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-white/70">{m}</span>)}
            </div>
            {followCode && (
              <Link
                href={`/follow/${followCode}`}
                className="rounded-full border border-wave-400/40 bg-wave-400/10 px-2.5 py-0.5 font-mono text-xs font-semibold text-wave-300 transition hover:bg-wave-400/20"
                title="Follow this channel"
              >
                follow
              </Link>
            )}
            {tracks.length > 1 && (
              <span className="text-xs font-medium text-white/50">
                {currentIndex + 1}/{tracks.length}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
