"use client";

import { createContext, useContext, useRef, useState, useEffect, useCallback } from "react";

export interface PlayerTrack {
  url: string;
  title?: string | null;
  artist?: string | null;
}

/** @deprecated Use PlayChannelRequest + playChannel(). Kept for backward compat. */
export interface PlayRequest {
  channelSlug: string;
  channelName: string;
  audioUrl: string;
  channelUrl: string;
  coverImageUrl?: string | null;
}

export interface PlayChannelRequest {
  channelSlug: string;
  channelName: string;
  channelUrl: string;
  coverImageUrl?: string | null;
  tracks: PlayerTrack[];
  startIndex?: number;
}

interface AudioPlayerState {
  channelSlug: string | null;
  channelName: string | null;
  channelUrl: string | null;
  trackTitle: string | null;
  trackArtist: string | null;
  coverImageUrl: string | null;
  currentAudioUrl: string | null;
  playlist: PlayerTrack[];
  currentTrackIndex: number;
  isPlaying: boolean;
  volume: number;
  analyserNode: AnalyserNode | null;
  audioRef: React.RefObject<HTMLAudioElement>;
  // Primary actions
  playChannel: (request: PlayChannelRequest) => void;
  togglePlay: () => void;
  // Legacy / pass-through (MiniPlayerBar)
  play: (request: PlayRequest) => void;
  pause: () => void;
  resume: () => void;
  setVolume: (v: number) => void;
  updateTrack: (title: string | null, artist: string | null) => void;
}

const AudioPlayerContext = createContext<AudioPlayerState | null>(null);

export function useAudioPlayer(): AudioPlayerState {
  const ctx = useContext(AudioPlayerContext);
  if (!ctx) throw new Error("useAudioPlayer must be used inside AudioPlayerProvider");
  return ctx;
}

export function AudioPlayerProvider({ children }: { children: React.ReactNode }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  // Generation counter: each new playChannel call increments this. Async callbacks
  // check gen === playGenRef.current before acting so stale requests are dropped.
  const playGenRef = useRef(0);
  // Mutable refs for onEnded (avoids stale closures in the empty-dep effect).
  const playlistRef = useRef<PlayerTrack[]>([]);
  const currentTrackIndexRef = useRef(0);
  const currentAudioUrlRef = useRef<string | null>(null);

  const [channelSlug, setChannelSlug] = useState<string | null>(null);
  const [channelName, setChannelName] = useState<string | null>(null);
  const [channelUrl, setChannelUrl] = useState<string | null>(null);
  const [trackTitle, setTrackTitle] = useState<string | null>(null);
  const [trackArtist, setTrackArtist] = useState<string | null>(null);
  const [coverImageUrl, setCoverImageUrl] = useState<string | null>(null);
  const [currentAudioUrl, setCurrentAudioUrl] = useState<string | null>(null);
  const [playlist, setPlaylist] = useState<PlayerTrack[]>([]);
  const [currentTrackIndex, setCurrentTrackIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolumeState] = useState(0.8);
  const [analyserNode, setAnalyserNode] = useState<AnalyserNode | null>(null);

  // Resume suspended AudioContext when tab regains focus (iOS requirement).
  useEffect(() => {
    const handler = () => {
      if (document.visibilityState === "visible" && audioCtxRef.current?.state === "suspended") {
        audioCtxRef.current.resume().catch(() => {});
      }
    };
    document.addEventListener("visibilitychange", handler);
    return () => document.removeEventListener("visibilitychange", handler);
  }, []);

  function initAudioContext(audio: HTMLAudioElement) {
    if (audioCtxRef.current) return;
    try {
      const ctx = new AudioContext();
      const an = ctx.createAnalyser();
      an.fftSize = 2048;
      an.smoothingTimeConstant = 0.88;
      const src = ctx.createMediaElementSource(audio);
      src.connect(an);
      an.connect(ctx.destination);
      audioCtxRef.current = ctx;
      setAnalyserNode(an);
    } catch {
      // Never interrupt playback on AudioContext failure.
    }
  }

  // Track cycling lives here so it works even when ChannelPlayer is unmounted
  // (e.g. MiniPlayerBar keeps audio going while the user browses the directory).
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const handleEnded = () => {
      const len = playlistRef.current.length;
      if (len === 0) return;
      const nextIdx = (currentTrackIndexRef.current + 1) % len;
      const track = playlistRef.current[nextIdx];
      if (!track) return;
      const gen = ++playGenRef.current;
      currentTrackIndexRef.current = nextIdx;
      currentAudioUrlRef.current = track.url;
      setCurrentTrackIndex(nextIdx);
      setCurrentAudioUrl(track.url);
      setTrackTitle(track.title ?? null);
      setTrackArtist(track.artist ?? null);
      audio.src = track.url;
      audio.play().catch((err) => {
        if (playGenRef.current === gen && err.name !== "AbortError") {
          setIsPlaying(false);
        }
      });
    };
    audio.addEventListener("ended", handleEnded);
    return () => audio.removeEventListener("ended", handleEnded);
  }, []);

  const playChannel = useCallback((request: PlayChannelRequest) => {
    const audio = audioRef.current;
    if (!audio) return;
    const startIdx = request.startIndex ?? 0;
    const track = request.tracks[startIdx];
    if (!track) return;

    const gen = ++playGenRef.current;

    // Only swap src when the track actually changes; avoids seek-to-start when
    // resuming the same track that is already loaded.
    const isSameTrack = currentAudioUrlRef.current === track.url;
    if (!isSameTrack) {
      audio.pause();
      audio.src = track.url;
      currentAudioUrlRef.current = track.url;
    }

    if (!audioCtxRef.current) {
      initAudioContext(audio);
    } else if (audioCtxRef.current.state === "suspended") {
      audioCtxRef.current.resume().catch(() => {});
    }

    // Update mutable refs before the async play so onEnded always sees fresh state.
    playlistRef.current = request.tracks;
    currentTrackIndexRef.current = startIdx;

    setChannelSlug(request.channelSlug);
    setChannelName(request.channelName);
    setChannelUrl(request.channelUrl);
    setCoverImageUrl(request.coverImageUrl ?? null);
    setPlaylist(request.tracks);
    setCurrentTrackIndex(startIdx);
    setCurrentAudioUrl(track.url);
    setTrackTitle(track.title ?? null);
    setTrackArtist(track.artist ?? null);
    setIsPlaying(true);

    audio.play().catch((err) => {
      if (playGenRef.current === gen && err.name !== "AbortError") {
        setIsPlaying(false);
      }
    });
  }, []);

  // Context-level togglePlay: smart toggle on whatever is currently loaded.
  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      if (audioCtxRef.current?.state === "suspended") {
        audioCtxRef.current.resume().catch(() => {});
      }
      audio.play().catch(() => setIsPlaying(false));
      setIsPlaying(true);
    } else {
      audio.pause();
      setIsPlaying(false);
    }
  }, []);

  const play = useCallback((request: PlayRequest) => {
    const audio = audioRef.current;
    if (!audio) return;
    const gen = ++playGenRef.current;
    if (currentAudioUrlRef.current !== request.audioUrl) {
      audio.pause();
      audio.src = request.audioUrl;
      currentAudioUrlRef.current = request.audioUrl;
    }
    if (!audioCtxRef.current) {
      initAudioContext(audio);
    } else if (audioCtxRef.current.state === "suspended") {
      audioCtxRef.current.resume().catch(() => {});
    }
    audio.play().catch((err) => {
      if (playGenRef.current === gen && err.name !== "AbortError") {
        setIsPlaying(false);
      }
    });
    setChannelSlug(request.channelSlug);
    setChannelName(request.channelName);
    setChannelUrl(request.channelUrl);
    setCoverImageUrl(request.coverImageUrl ?? null);
    setCurrentAudioUrl(request.audioUrl);
    setIsPlaying(true);
  }, []);

  const pause = useCallback(() => {
    audioRef.current?.pause();
    setIsPlaying(false);
  }, []);

  const resume = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (audioCtxRef.current?.state === "suspended") {
      audioCtxRef.current.resume().catch(() => {});
    }
    audio.play().catch(() => setIsPlaying(false));
    setIsPlaying(true);
  }, []);

  const setVolume = useCallback((v: number) => {
    if (audioRef.current) audioRef.current.volume = v;
    setVolumeState(v);
  }, []);

  const updateTrack = useCallback((title: string | null, artist: string | null) => {
    setTrackTitle(title);
    setTrackArtist(artist);
  }, []);

  const value: AudioPlayerState = {
    channelSlug,
    channelName,
    channelUrl,
    trackTitle,
    trackArtist,
    coverImageUrl,
    currentAudioUrl,
    playlist,
    currentTrackIndex,
    isPlaying,
    volume,
    analyserNode,
    audioRef,
    playChannel,
    togglePlay,
    play,
    pause,
    resume,
    setVolume,
    updateTrack,
  };

  return (
    <AudioPlayerContext.Provider value={value}>
      {/* Persistent audio element — never unmounts. */}
      <audio
        ref={audioRef}
        crossOrigin="anonymous"
        preload="none"
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
      />
      {children}
    </AudioPlayerContext.Provider>
  );
}
