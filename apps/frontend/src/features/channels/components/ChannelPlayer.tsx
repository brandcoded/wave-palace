"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Play, Pause, Volume2, VolumeX, AlertTriangle, User, X } from "lucide-react";
import type { Sponsor, TrackItem } from "@/features/channels/types/channel";
import { recordPlay, recordSponsorImpression, recordSponsorClick } from "@/features/channels/lib/channelApi";
import { displayFollowerCount, displayListenerCount, displayWorldsCount } from "@/features/channels/lib/metrics";
import { makeFollowCode } from "@/features/channels/lib/followCode";
import { recordListenEvent, getOrCreateSessionKey } from "@/features/me/lib/meApi";
import { useAudioVisualizer } from "@/features/channels/hooks/useAudioVisualizer";
import type { VisualizerStyle, VisualizerTheme } from "@/features/channels/hooks/useAudioVisualizer";
import { useAudioPlayer } from "@/features/player/context/AudioPlayerContext";
import { useChannelFollowState } from "@/features/follow/hooks/useChannelFollowState";

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
  followerCount?: number;
  listenerCount?: number;
  worldsCount?: number;
}

export function ChannelPlayer({ tracks, coverImage, title, slug, visualLoopUrl, hostName, genre, mood, sponsor, visualizerStyle, visualizerTheme, visualizerBackdrop, followerCount, listenerCount, worldsCount }: ChannelPlayerProps) {
  const searchParams = useSearchParams();
  const player = useAudioPlayer();
  const followState = useChannelFollowState(slug);
  const videoRef  = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const vizStyle  = visualizerStyle  ?? "none";
  const vizTheme  = visualizerTheme  ?? "violet";
  const vizBackdrop = visualizerBackdrop ?? "overlay_video";
  const [muted, setMuted] = useState(false);
  const [errored, setErrored] = useState(false);
  const [sponsorDismissed, setSponsorDismissed] = useState(false);
  const lastListenKeyRef = useRef<string | null>(null);

  // Derived: true only when this channel is the active one and audio is playing.
  const playing = player.isPlaying && player.channelSlug === slug;

  // Track index comes from the context when this channel is active; 0 otherwise.
  const currentIndex = player.channelSlug === slug ? player.currentTrackIndex : 0;

  useAudioVisualizer(player.analyserNode, canvasRef, vizStyle, vizTheme, playing);

  // Autoplay on mount when navigated here with ?autoplay=1.
  // Guard with a ref so it fires at most once per mount even in StrictMode.
  const autoplayFiredRef = useRef(false);
  useEffect(() => {
    if (searchParams.get("autoplay") !== "1") return;
    if (autoplayFiredRef.current) return;
    autoplayFiredRef.current = true;
    player.playChannel({
      channelSlug: slug,
      channelName: title,
      channelUrl: `/channels/${slug}`,
      coverImageUrl: coverImage,
      tracks: tracks.map((t) => ({ url: t.url, title: t.title, artist: t.artist })),
      startIndex: 0,
    });
    if (typeof window !== "undefined") {
      const key = `wp_played_${slug}`;
      if (!sessionStorage.getItem(key)) {
        sessionStorage.setItem(key, "1");
        recordPlay(slug);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Attach error listener to the shared audio element for this channel's tracks.
  useEffect(() => {
    const audio = player.audioRef.current;
    if (!audio) return;
    function handleError() { setErrored(true); }
    audio.addEventListener("error", handleError);
    return () => audio.removeEventListener("error", handleError);
  }, [player.audioRef]);

  // Reset error state when navigating to a different channel.
  useEffect(() => {
    setErrored(false);
  }, [tracks]);

  // Fire listen history when a new track starts playing on this channel.
  useEffect(() => {
    if (!playing) return;
    const track = tracks[currentIndex];
    if (!track) return;
    const key = `${slug}:${currentIndex}:${track.title}`;
    if (lastListenKeyRef.current === key) return;
    lastListenKeyRef.current = key;
    const sk = typeof window !== "undefined" ? getOrCreateSessionKey() : null;
    recordListenEvent(slug, track.title || null, track.artist || null, sk);
  }, [currentIndex, playing, slug, tracks]);

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

  // Keep video in lockstep with audio playing state.
  useEffect(() => {
    playing ? videoRef.current?.play() : videoRef.current?.pause();
  }, [playing]);

  function togglePlay() {
    if (playing) {
      player.pause();
      videoRef.current?.pause();
    } else {
      player.playChannel({
        channelSlug: slug,
        channelName: title,
        channelUrl: `/channels/${slug}`,
        coverImageUrl: coverImage,
        tracks: tracks.map((t) => ({ url: t.url, title: t.title, artist: t.artist })),
        startIndex: currentIndex,
      });
      if (typeof window !== "undefined") {
        const key = `wp_played_${slug}`;
        if (!sessionStorage.getItem(key)) {
          sessionStorage.setItem(key, "1");
          recordPlay(slug);
        }
      }
    }
  }

  function handleVolumeChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = parseFloat(e.target.value);
    player.setVolume(val);
    const audio = player.audioRef.current;
    if (audio) audio.muted = val === 0;
    setMuted(val === 0);
  }

  function toggleMute() {
    const audio = player.audioRef.current;
    if (!audio) return;
    const next = !muted;
    audio.muted = next;
    if (!next && audio.volume === 0) audio.volume = 0.8;
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
              : "absolute inset-x-0 w-full top-1/2 h-[120px] -translate-y-1/2 pointer-events-none"
          }
          style={{ zIndex: 2 }}
        />
      )}

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
        {/* Row 1: title + host + metrics */}
        <div>
          <p className="truncate text-sm font-semibold leading-tight text-white">{title}</p>
          <p className="flex items-center gap-1 text-xs text-white/60">
            <User className="h-3 w-3 shrink-0" /> Hosted by {hostName}
          </p>
          {(() => {
            const listener = displayListenerCount(listenerCount);
            const followers = displayFollowerCount(followerCount);
            const worlds = displayWorldsCount(worldsCount);
            if (!listener && !followers && !worlds) return null;
            return (
              <p className="mt-0.5 flex flex-wrap items-center gap-x-2 text-[10px] text-white/40">
                {listener && (
                  <span className="flex items-center gap-1">
                    <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    {listener}
                  </span>
                )}
                {followers && <span>{followers}</span>}
                {worlds && <span>{worlds}</span>}
              </p>
            );
          })()}
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
            value={muted ? 0 : player.volume}
            onChange={handleVolumeChange}
            aria-label="Volume"
            className="h-1 w-24 cursor-pointer appearance-none rounded-full bg-white/20 accent-white"
          />

          <div className="ml-auto flex items-center gap-2">
            <div className="hidden sm:flex gap-1.5">
              {genre.map((g) => <span key={g} className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-white/70">{g}</span>)}
              {mood.map((m) => <span key={m} className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-white/70">{m}</span>)}
            </div>
            {!followState.isLoading && (
              followState.isFollowing ? (
                <button
                  onClick={followState.unfollow}
                  className={`rounded-full border px-2.5 py-0.5 font-mono text-xs font-semibold transition ${
                    followState.confirmingUnfollow
                      ? "border-red-400/40 text-red-300 hover:border-red-400/60"
                      : "border-white/20 text-white/50 hover:border-white/30 hover:text-white/70"
                  }`}
                >
                  {followState.confirmingUnfollow ? "Tap to confirm" : "Unfollow"}
                </button>
              ) : followCode ? (
                <Link
                  href={`/follow/${followCode}`}
                  className="rounded-full border border-wave-400/40 bg-wave-400/10 px-2.5 py-0.5 font-mono text-xs font-semibold text-wave-300 transition hover:bg-wave-400/20"
                  title="Follow this channel"
                >
                  follow
                </Link>
              ) : null
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
