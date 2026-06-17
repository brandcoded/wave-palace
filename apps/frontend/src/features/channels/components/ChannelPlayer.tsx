"use client";

import { useEffect, useRef, useState } from "react";
import { Play, Pause, Volume2, VolumeX, AlertTriangle } from "lucide-react";

interface ChannelPlayerProps {
  audioSrc: string;
  coverImage: string;
  title: string;
}

export function ChannelPlayer({ audioSrc, coverImage, title }: ChannelPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(0.8);
  const [errored, setErrored] = useState(false);

  useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    a.volume = volume;
    a.muted = false;
  }, [audioSrc]);

  function togglePlay() {
    const a = audioRef.current;
    if (!a) return;
    if (a.paused) {
      a.play();
      setPlaying(true);
    } else {
      a.pause();
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

  return (
    <div className="group relative w-full overflow-hidden rounded-2xl border border-white/10 bg-black shadow-2xl shadow-black/50">
      {/* Cover art */}
      <img
        src={coverImage}
        alt={`${title} channel art`}
        className="aspect-video w-full object-cover"
      />

      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        src={audioSrc}
        preload="auto"
        onError={() => setErrored(true)}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
      />

      {/* Controls overlay */}
      <div className="absolute inset-x-0 bottom-0 flex items-center gap-3 bg-gradient-to-t from-black/80 to-transparent px-4 py-4">
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
      </div>
    </div>
  );
}
