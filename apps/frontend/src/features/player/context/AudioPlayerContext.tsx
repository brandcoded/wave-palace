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

// iOS/Android keep a *bare* <audio> element playing when the screen locks, but
// an element captured by Web Audio via createMediaElementSource is routed
// through the AudioContext — which iOS suspends on lock, killing all audio. So
// on mobile we must NOT capture the element in Web Audio. The reactive
// visualizer (which needs the AnalyserNode) is therefore desktop-only; the
// cinematic cover-art / video backdrop still fills the player on mobile.
function isMobileClient(): boolean {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent;
  if (/Android|iPhone|iPad|iPod/i.test(ua)) return true;
  // iPadOS 13+ reports as "Macintosh" but is touch-capable.
  return navigator.maxTouchPoints > 1 && /Macintosh/i.test(ua);
}

interface MediaMeta {
  title: string | null;
  artist: string | null;
  channelName: string | null;
  coverImageUrl: string | null;
}

// Infer the artwork MIME type from the URL — iOS silently rejects artwork whose
// declared type doesn't match the actual image (a common "art won't show" cause).
function artworkType(url: string): string {
  const u = url.split("?")[0].toLowerCase();
  if (u.endsWith(".png")) return "image/png";
  if (u.endsWith(".webp")) return "image/webp";
  if (u.endsWith(".gif")) return "image/gif";
  return "image/jpeg";
}

// Resolve to an absolute URL — iOS cannot fetch lock-screen artwork from a
// relative path.
function absoluteUrl(url: string): string {
  if (/^https?:\/\//i.test(url)) return url;
  if (typeof window !== "undefined") {
    try { return new URL(url, window.location.origin).href; } catch { /* ignore */ }
  }
  return url;
}

// Build artwork entries from a direct cover URL (used as the immediate value
// before the downscaled data-URL artwork is ready).
function urlArtwork(cover: string): MediaImage[] {
  const type = artworkType(cover);
  return ["96x96", "128x128", "192x192", "256x256", "384x384", "512x512"].map(
    (sizes) => ({ src: cover, sizes, type }),
  );
}

function setMediaMetadata(meta: MediaMeta, artwork?: MediaImage[]): void {
  if (!mediaSessionSupported() || typeof MediaMetadata === "undefined") return;
  const cover = meta.coverImageUrl ? absoluteUrl(meta.coverImageUrl) : null;
  try {
    navigator.mediaSession.metadata = new MediaMetadata({
      title: meta.title ?? meta.channelName ?? "WavePalace",
      artist: meta.artist ?? "",
      album: meta.channelName ?? "WavePalace",
      // Prefer explicit (downscaled, self-contained data-URL) artwork when
      // provided; otherwise fall back to the direct cover URL.
      artwork: artwork ?? (cover ? urlArtwork(cover) : []),
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
  // Whether the user intends playback to continue. Gates auto-advance so a
  // stray "ended"/"error" event fired around a pause (common on mobile) can
  // never restart playback — the core mobile pause-loop fix. Set true by every
  // play path, false by every pause path.
  const intendedPlayingRef = useRef(false);
  // Runaway-advance guard: timestamp + streak of rapid ended/error events. Real
  // tracks never end within ~1.5s of each other repeatedly, so a streak means a
  // failed/zero-length source is hot-looping play→ended→play; we stop instead.
  const lastEndedAtRef = useRef(0);
  const endedStreakRef = useRef(0);
  // Cache of downscaled data-URL artwork keyed by absolute cover URL. iOS fails
  // to render large remote artwork and then shows a blank now-playing card
  // (title included), so we hand it small self-contained data URLs instead.
  const artworkCacheRef = useRef<Map<string, MediaImage[]>>(new Map());

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
    // Mobile: leave the <audio> as a bare media element (survives screen lock)
    // and skip the Web Audio graph. analyserNode stays null → the visualizer
    // hook draws nothing, and the backdrop fills the player. Desktop only below.
    if (isMobileClient()) return;
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

  // Downscale a cover image to small square data-URL artwork in-canvas. iOS
  // rejects large remote artwork (and then blanks the whole now-playing card),
  // but reliably renders small self-contained data URLs. Cached per cover URL.
  // Returns null on failure (e.g. canvas tainted), leaving the direct-URL
  // fallback in place. Requires the cover to be CORS-readable (R2 sends
  // Access-Control-Allow-Origin: * on GET, so the crossOrigin load isn't tainted).
  const buildArtwork = useCallback(async (cover: string): Promise<MediaImage[] | null> => {
    const cached = artworkCacheRef.current.get(cover);
    if (cached) return cached;
    if (typeof document === "undefined" || typeof Image === "undefined") return null;
    try {
      const img = new Image();
      img.crossOrigin = "anonymous";
      await new Promise<void>((resolve, reject) => {
        img.onload = () => resolve();
        img.onerror = () => reject(new Error("artwork load failed"));
        img.src = cover;
      });
      const render = (size: number): MediaImage | null => {
        const canvas = document.createElement("canvas");
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext("2d");
        if (!ctx) return null;
        // Cover-fit crop to a centered square.
        const scale = Math.max(size / img.width, size / img.height);
        const w = img.width * scale;
        const h = img.height * scale;
        ctx.drawImage(img, (size - w) / 2, (size - h) / 2, w, h);
        return { src: canvas.toDataURL("image/jpeg", 0.9), sizes: `${size}x${size}`, type: "image/jpeg" };
      };
      const imgs = [render(512), render(256), render(128)].filter(Boolean) as MediaImage[];
      if (imgs.length === 0) return null;
      artworkCacheRef.current.set(cover, imgs);
      return imgs;
    } catch {
      return null;
    }
  }, []);

  // Merge metadata into the ref and push it to the OS. Title/artist bind
  // immediately (no artwork dependency); the downscaled artwork is applied
  // asynchronously once ready so a slow/failed image can't delay the title.
  const syncMediaMetadata = useCallback((partial: Partial<MediaMeta>) => {
    mediaMetaRef.current = { ...mediaMetaRef.current, ...partial };
    const cover = mediaMetaRef.current.coverImageUrl
      ? absoluteUrl(mediaMetaRef.current.coverImageUrl)
      : null;
    // Immediate: title/artist + cached artwork if we already have it.
    setMediaMetadata(mediaMetaRef.current, cover ? artworkCacheRef.current.get(cover) : undefined);
    // Async: build/lookup downscaled artwork, then re-apply if cover unchanged.
    if (cover) {
      buildArtwork(cover).then((art) => {
        if (art && mediaMetaRef.current.coverImageUrl && absoluteUrl(mediaMetaRef.current.coverImageUrl) === cover) {
          setMediaMetadata(mediaMetaRef.current, art);
        }
      });
    }
  }, [buildArtwork]);

  // Advance to the next track in the playlist. Shared by the audio "ended"
  // event and the lock-screen "nexttrack" handler, so cycling behaves
  // identically whether triggered by playback or the OS. Empty-dep useCallback:
  // reads only refs (never stale) so the lock-screen handler registered once on
  // mount stays correct across every track change.
  const advanceTrack = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    // Pause-intent gate: if the user paused (or we stopped on a runaway), a
    // stray ended/error must NOT restart playback. This is the central fix.
    if (!intendedPlayingRef.current) return;
    const len = playlistRef.current.length;
    if (len === 0) return;
    const gen = ++playGenRef.current;
    if (len === 1) {
      // Single track: restart in place. Native `loop` normally handles end-of-
      // track for single-track playlists; this path only runs for an explicit
      // "nexttrack" action and never reloads the src (no chance to interact
      // with the pause race).
      audio.currentTime = 0;
      audio.play().catch((err) => {
        if (playGenRef.current === gen && err.name !== "AbortError") setIsPlaying(false);
      });
      return;
    }
    const nextIdx = (currentTrackIndexRef.current + 1) % len;
    const track = playlistRef.current[nextIdx];
    if (!track) return;
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
    const handleEndedOrError = () => {
      // Paused → a stray ended/error must keep playback stopped.
      if (!intendedPlayingRef.current) return;
      const now = Date.now();
      if (now - lastEndedAtRef.current < 1500) {
        endedStreakRef.current += 1;
      } else {
        endedStreakRef.current = 0;
      }
      lastEndedAtRef.current = now;
      // Runaway guard: repeated rapid ended/error events mean a failing or
      // zero-length source is hot-looping. Stop rather than cycle forever.
      if (endedStreakRef.current >= 2) {
        intendedPlayingRef.current = false;
        audio.pause();
        setIsPlaying(false);
        return;
      }
      advanceTrack();
    };
    // A track that actually starts playing clears the failure streak, so a
    // recovered playlist isn't permanently held by an earlier hiccup. Also
    // re-assert the now-playing metadata + state HERE: iOS reads lock-screen
    // info when the audio session goes active, so metadata set earlier (during
    // playChannel, before audio.play() resolved) is often dropped — re-applying
    // it on "playing" is what makes the art + title appear on the lock screen.
    const handlePlaying = () => {
      endedStreakRef.current = 0;
      const cover = mediaMetaRef.current.coverImageUrl
        ? absoluteUrl(mediaMetaRef.current.coverImageUrl)
        : null;
      setMediaMetadata(mediaMetaRef.current, cover ? artworkCacheRef.current.get(cover) : undefined);
      setMediaPlaybackState(true);
    };
    audio.addEventListener("ended", handleEndedOrError);
    audio.addEventListener("error", handleEndedOrError);
    audio.addEventListener("playing", handlePlaying);
    return () => {
      audio.removeEventListener("ended", handleEndedOrError);
      audio.removeEventListener("error", handleEndedOrError);
      audio.removeEventListener("playing", handlePlaying);
    };
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
      // Seek-to-start (like Spotify). Must be non-null: some iOS versions hide
      // the entire lock-screen widget if previoustrack has no handler.
      ms.setActionHandler("previoustrack", () => {
        const audio = audioRef.current;
        if (audio) audio.currentTime = 0;
      });
      ms.setActionHandler("stop", () => pause());
    } catch {
      // Some browsers reject specific actions — ignore unsupported ones.
    }
    return () => {
      try {
        ms.setActionHandler("play", null);
        ms.setActionHandler("pause", null);
        ms.setActionHandler("nexttrack", null);
        ms.setActionHandler("previoustrack", null);
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

    // User intends playback; reset the runaway-failure streak for the new start.
    intendedPlayingRef.current = true;
    endedStreakRef.current = 0;
    // Single-track playlists loop natively (no advanceTrack restart that could
    // race with a pause); multi-track advance via the "ended" handler.
    audio.loop = request.tracks.length === 1;

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
      intendedPlayingRef.current = true;
      if (audioCtxRef.current?.state === "suspended") {
        audioCtxRef.current.resume().catch(() => {});
      }
      audio.play().catch(() => setIsPlaying(false));
      setIsPlaying(true);
    } else {
      intendedPlayingRef.current = false;
      audio.pause();
      setIsPlaying(false);
    }
  }, []);

  const play = useCallback((request: PlayRequest) => {
    const audio = audioRef.current;
    if (!audio) return;
    const gen = ++playGenRef.current;
    // Legacy single-URL path: intend playback, loop natively, clear streak.
    intendedPlayingRef.current = true;
    endedStreakRef.current = 0;
    audio.loop = true;
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
    // Clear intent BEFORE pausing so any ended/error the pause itself emits
    // (mobile can) is gated out of advanceTrack and can't restart playback.
    intendedPlayingRef.current = false;
    audioRef.current?.pause();
    setIsPlaying(false);
  }, []);

  const resume = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    intendedPlayingRef.current = true;
    endedStreakRef.current = 0;
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
        playsInline
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
