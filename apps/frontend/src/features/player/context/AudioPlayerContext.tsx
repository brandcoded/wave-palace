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

// ---------------------------------------------------------------------------
// Media Session helpers — module-level so they never close over React state.
// They take explicit values, so there is no stale-closure risk on the OS/lock-
// screen surface (a classic source of "lock-screen buttons stop working after
// the first track change" bugs). Each is a silent no-op when unsupported.
// ---------------------------------------------------------------------------

function mediaSessionSupported(): boolean {
  return typeof navigator !== "undefined" && "mediaSession" in navigator;
}

interface MediaMeta {
  title: string | null;
  artist: string | null;
  channelName: string | null;
  coverImageUrl: string | null;
}

function setMediaMetadata(meta: MediaMeta): void {
  if (!mediaSessionSupported() || typeof MediaMetadata === "undefined") return;
  try {
    navigator.mediaSession.metadata = new MediaMetadata({
      title: meta.title ?? meta.channelName ?? "WavePalace",
      artist: meta.artist ?? "",
      album: meta.channelName ?? "WavePalace",
      artwork: meta.coverImageUrl
        ? [
            { src: meta.coverImageUrl, sizes: "512x512", type: "image/jpeg" },
            { src: meta.coverImageUrl, sizes: "256x256", type: "image/jpeg" },
          ]
        : [],
    });
  } catch {
    // MediaMetadata construction can throw on malformed artwork URLs — ignore.
  }
}

function setMediaPlaybackState(playing: boolean): void {
  if (!mediaSessionSupported()) return;
  try {
    navigator.mediaSession.playbackState = playing ? "playing" : "paused";
  } catch {
    // ignore
  }
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
  // Latest media-session metadata. advanceTrack only changes the track-level
  // fields, so it reads channel-level fields (name, cover) back from here
  // rather than from React state (which would be stale in an empty-dep cb).
  const mediaMetaRef = useRef<MediaMeta>({
    title: null,
    artist: null,
    channelName: null,
    coverImageUrl: null,
  });

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
      // latencyHint "playback" → larger, more stable buffers. The default
      // ("interactive") uses tiny buffers tuned for low latency, which are more
      // prone to underruns; an underrun→catch-up is heard as a brief pitch/speed
      // bump (especially over Bluetooth/AirPods, which add latency). A music
      // player doesn't need low latency, so prefer playback-optimized buffering.
      const ctx = new AudioContext({ latencyHint: "playback" });
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

  // Merge metadata into the ref and push it to the OS in one step.
  const syncMediaMetadata = useCallback((partial: Partial<MediaMeta>) => {
    mediaMetaRef.current = { ...mediaMetaRef.current, ...partial };
    setMediaMetadata(mediaMetaRef.current);
  }, []);

  // Advance to the next track in the playlist. Shared by the audio "ended"
  // event and the lock-screen "nexttrack" handler, so cycling behaves
  // identically whether triggered by playback or the OS. Empty-dep useCallback:
  // reads only refs (never stale) so the lock-screen handler registered once on
  // mount stays correct across every track change.
  const advanceTrack = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
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
    syncMediaMetadata({ title: track.title ?? null, artist: track.artist ?? null });
    audio.src = track.url;
    audio.play().catch((err) => {
      if (playGenRef.current === gen && err.name !== "AbortError") {
        setIsPlaying(false);
      }
    });
  }, [syncMediaMetadata]);

  // Track cycling lives here so it works even when ChannelPlayer is unmounted
  // (e.g. MiniPlayerBar keeps audio going while the user browses the directory).
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const handleEnded = () => advanceTrack();
    audio.addEventListener("ended", handleEnded);
    return () => audio.removeEventListener("ended", handleEnded);
  }, [advanceTrack]);

  // Register lock-screen / OS media controls once. resume, pause and
  // advanceTrack are all stable empty-dep callbacks, so this effect runs once
  // and never re-binds — no duplicate handlers, no stale closures.
  useEffect(() => {
    if (!mediaSessionSupported()) return;
    const ms = navigator.mediaSession;
    try {
      ms.setActionHandler("play", () => resume());
      ms.setActionHandler("pause", () => pause());
      ms.setActionHandler("nexttrack", () => advanceTrack());
      ms.setActionHandler("previoustrack", null); // single-direction playlist
      ms.setActionHandler("stop", () => pause());
    } catch {
      // Some browsers reject specific actions — ignore unsupported ones.
    }
    return () => {
      try {
        ms.setActionHandler("play", null);
        ms.setActionHandler("pause", null);
        ms.setActionHandler("nexttrack", null);
        ms.setActionHandler("stop", null);
      } catch {
        // ignore
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [advanceTrack]);

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
    }
    // Always resume if suspended — a freshly-created AudioContext on desktop
    // Chrome starts suspended, and since audio is routed through the
    // MediaElementSource, a suspended context means total silence. This runs
    // inside the play gesture, so resume() is permitted.
    if (audioCtxRef.current?.state === "suspended") {
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

    syncMediaMetadata({
      title: track.title ?? null,
      artist: track.artist ?? null,
      channelName: request.channelName,
      coverImageUrl: request.coverImageUrl ?? null,
    });

    audio.play().catch((err) => {
      if (playGenRef.current === gen && err.name !== "AbortError") {
        setIsPlaying(false);
      }
    });
  }, [syncMediaMetadata]);

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
    }
    // Always resume if suspended (a new desktop-Chrome AudioContext starts
    // suspended → MediaElementSource routing yields silence otherwise).
    if (audioCtxRef.current?.state === "suspended") {
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
    syncMediaMetadata({
      channelName: request.channelName,
      coverImageUrl: request.coverImageUrl ?? null,
    });
  }, [syncMediaMetadata]);

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
    syncMediaMetadata({ title, artist });
  }, [syncMediaMetadata]);

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
        onPlay={() => {
          setIsPlaying(true);
          setMediaPlaybackState(true);
        }}
        onPause={() => {
          setIsPlaying(false);
          setMediaPlaybackState(false);
        }}
      />
      {children}
    </AudioPlayerContext.Provider>
  );
}
