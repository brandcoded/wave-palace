"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Bell,
  BookmarkCheck,
  ChevronRight,
  Heart,
  Pause,
  Play,
  Radio,
  Sparkles,
  User,
} from "lucide-react";
import { relativeTime } from "@/lib/relativeTime";
import { useAudioPlayer } from "@/features/player/context/AudioPlayerContext";
import {
  getHistory,
  getMe,
  getNotifications,
  getOwnedChannels,
  getOrCreateSessionKey,
  getRecommendations,
  getSaves,
  getFollowedSlugs,
  markAllRead,
  mergeListenHistory,
  type HistoryResponse,
  type Notification,
  type NotificationsResponse,
} from "@/features/me/lib/meApi";
import { getChannels } from "@/features/channels/lib/channelApi";
import { getFollowerCount } from "@/features/follow/lib/followApi";
import type { Channel } from "@/features/channels/types/channel";
import type { CurrentUser } from "@/features/admin/types/admin";

type ChannelRec = Channel & { _reason: string | null };

const tagClass =
  "rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-white/60";

function MiniChannelCard({ channel, reason }: { channel: Channel; reason?: string | null }) {
  const player = useAudioPlayer();
  const isActive = player.channelSlug === channel.slug;
  const isPlaying = isActive && player.isPlaying;

  function handlePlay(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (isPlaying) {
      player.pause();
    } else {
      const tracks = channel.playlist?.length
        ? channel.playlist.map((t) => ({ url: t.url, title: t.title, artist: t.artist }))
        : [{ url: channel.audioUrl, title: null, artist: null }];
      player.playChannel({
        channelSlug: channel.slug,
        channelName: channel.title,
        channelUrl: `/channels/${channel.slug}`,
        coverImageUrl: channel.coverImageUrl,
        tracks,
        startIndex: 0,
      });
    }
  }

  return (
    <Link
      href={`/channels/${channel.slug}`}
      className="group flex items-center gap-3 rounded-2xl border border-white/8 bg-white/3 px-4 py-3 transition hover:border-wave-500/30 hover:bg-white/6"
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={channel.coverImageUrl as string}
        alt={channel.title}
        className="h-12 w-12 rounded-xl object-cover"
      />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-white">{channel.title}</p>
        <p className="truncate text-xs text-white/45">
          {(Array.isArray(channel.genre) ? channel.genre : []).slice(0, 2).join(" · ")}
          {reason ? <span className="ml-1 text-wave-400"> · {reason}</span> : null}
        </p>
      </div>
      <button
        onClick={handlePlay}
        aria-label={isPlaying ? `Pause ${channel.title}` : `Play ${channel.title}`}
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition text-white/30 group-hover:text-wave-400 hover:bg-white/10 active:scale-95"
      >
        {isPlaying ? (
          <Pause className="h-4 w-4 fill-current" />
        ) : (
          <Play className="h-4 w-4 fill-current" />
        )}
      </button>
    </Link>
  );
}

function EventRow({ event }: { event: HistoryResponse["recent"][0] }) {
  return (
    <Link
      href={`/channels/${event.channel_slug}`}
      className="flex items-center gap-3 rounded-xl px-3 py-2.5 transition hover:bg-white/5"
    >
      <Radio className="h-3.5 w-3.5 shrink-0 text-wave-400" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-white/80">
          {event.track_title || event.channel_slug}
        </p>
        {event.track_artist && (
          <p className="truncate text-xs text-white/40">{event.track_artist}</p>
        )}
      </div>
      <span className="shrink-0 text-xs text-white/30">{relativeTime(event.started_at)}</span>
    </Link>
  );
}

function NotifRow({ notif, onRead }: { notif: Notification; onRead: (id: string) => void }) {
  return (
    <div
      className={`flex items-start gap-3 rounded-xl px-3 py-2.5 transition ${
        notif.read ? "opacity-50" : "bg-wave-500/5"
      }`}
    >
      <Bell className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${notif.read ? "text-white/30" : "text-wave-400"}`} />
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white/80">{notif.title}</p>
        {notif.body && <p className="text-xs text-white/40">{notif.body}</p>}
        <p className="text-xs text-white/30">{relativeTime(notif.created_at)}</p>
        {notif.link && (
          <Link href={notif.link} className="mt-0.5 block text-xs text-wave-400 hover:underline">
            View →
          </Link>
        )}
      </div>
      {!notif.read && (
        <button
          onClick={() => onRead(notif.id)}
          className="shrink-0 text-xs text-white/30 hover:text-white/60"
        >
          Dismiss
        </button>
      )}
    </div>
  );
}

function SectionHeading({ icon, title, href }: { icon: React.ReactNode; title: string; href?: string }) {
  return (
    <div className="mb-4 flex items-center justify-between">
      <h2 className="flex items-center gap-2 text-base font-semibold text-white">
        {icon}
        {title}
      </h2>
      {href && (
        <Link href={href} className="flex items-center gap-1 text-xs text-white/40 hover:text-white/70">
          View all <ChevronRight className="h-3 w-3" />
        </Link>
      )}
    </div>
  );
}

function greeting(name: string): string {
  const h = new Date().getHours();
  if (h < 12) return `Good morning, ${name}`;
  if (h < 18) return `Good afternoon, ${name}`;
  return `Good evening, ${name}`;
}

export default function HomePage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState<HistoryResponse>({ recent: [], top_channel: null, last_channel: null });
  const [notifs, setNotifs] = useState<NotificationsResponse>({ notifications: [], unread_count: 0 });
  const [recs, setRecs] = useState<ChannelRec[]>([]);
  const [followedChannels, setFollowedChannels] = useState<Channel[]>([]);
  const [savedChannels, setSavedChannels] = useState<Channel[]>([]);
  const [ownedChannels, setOwnedChannels] = useState<Channel[]>([]);
  const [followerCounts, setFollowerCounts] = useState<Record<string, number>>({});
  const [allChannels, setAllChannels] = useState<Channel[]>([]);
  const [loadError, setLoadError] = useState(false);
  const mergedRef = useRef(false);

  useEffect(() => {
    (async () => {
      try {
        const me = await getMe();
        if (!me) {
          router.replace("/");
          return;
        }
        setUser(me);

        // Merge anonymous listen history once per session
        if (!mergedRef.current) {
          mergedRef.current = true;
          const sk = getOrCreateSessionKey();
          if (sk) mergeListenHistory(sk);
        }

        // allSettled: one failing endpoint degrades its section to empty
        // instead of blanking the whole dashboard.
        const [rHist, rSaved, rNotif, rRec, rFollowed, rOwned, rChannels] =
          await Promise.allSettled([
            getHistory(),
            getSaves(),
            getNotifications(),
            getRecommendations(),
            getFollowedSlugs(),
            getOwnedChannels(),
            getChannels().catch(() => [] as Channel[]),
          ]);

        const anyFailed = [rHist, rSaved, rNotif, rRec, rFollowed, rOwned, rChannels].some(
          (r) => r.status === "rejected",
        );

        const hist =
          rHist.status === "fulfilled"
            ? rHist.value
            : { recent: [], top_channel: null, last_channel: null };
        const savedSlugs = rSaved.status === "fulfilled" ? rSaved.value : [];
        const notifications =
          rNotif.status === "fulfilled" ? rNotif.value : { notifications: [], unread_count: 0 };
        const recData = rRec.status === "fulfilled" ? rRec.value : [];
        const followedSlugs = rFollowed.status === "fulfilled" ? rFollowed.value : [];
        const owned = rOwned.status === "fulfilled" ? rOwned.value : [];
        const channels = rChannels.status === "fulfilled" ? rChannels.value : [];

        setHistory(hist);
        setNotifs(notifications);
        setLoadError(anyFailed);

        const bySlug = new Map(channels.map((c) => [c.slug, c]));

        setAllChannels(channels);
        setFollowedChannels(
          followedSlugs.flatMap((s) => { const c = bySlug.get(s); return c ? [c] : []; }),
        );
        setSavedChannels(
          savedSlugs.flatMap((s) => { const c = bySlug.get(s); return c ? [c] : []; }),
        );

        const recChannels: ChannelRec[] = recData.flatMap((r) => {
          const slug = r.slug as string;
          const base = bySlug.get(slug) ?? (r as unknown as Channel);
          if (!slug) return [];
          return [{ ...base, _reason: (r._reason as string | null) ?? null }];
        });
        setRecs(recChannels.slice(0, 6));

        const ownedMapped = (owned as Record<string, unknown>[]).flatMap((o) => {
          const c = bySlug.get(o.slug as string);
          return c ? [c] : [];
        });
        setOwnedChannels(ownedMapped);

        // Fetch follower counts for owned channels in parallel.
        if (ownedMapped.length > 0) {
          const counts = await Promise.all(
            ownedMapped.map((c) => getFollowerCount(c.slug).then((n) => [c.slug, n] as const))
          );
          setFollowerCounts(Object.fromEntries(counts));
        }
      } catch {
        // getMe() or an unexpected error — render a recoverable state rather
        // than hanging forever on the loading screen.
        setLoadError(true);
      } finally {
        setLoading(false);
      }
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleMarkAllRead() {
    await markAllRead();
    setNotifs((prev) => ({
      notifications: prev.notifications.map((n) => ({ ...n, read: true })),
      unread_count: 0,
    }));
  }

  function handleNotifRead(id: string) {
    setNotifs((prev) => ({
      notifications: prev.notifications.map((n) => (n.id === id ? { ...n, read: true } : n)),
      unread_count: Math.max(0, prev.unread_count - 1),
    }));
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <p className="text-white/30">Loading your dashboard…</p>
      </div>
    );
  }

  // getMe() failed entirely — show a recoverable state instead of crashing on
  // user!.display_name below.
  if (!user) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-md flex-col items-center justify-center px-6 text-center">
        <p className="mb-2 font-semibold text-white">We couldn&apos;t load your dashboard</p>
        <p className="mb-6 text-sm text-white/50">
          Please check your connection and try again.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="rounded-full bg-wave-500/20 px-5 py-2.5 text-sm font-semibold text-wave-300 hover:bg-wave-500/30"
        >
          Retry
        </button>
      </div>
    );
  }

  const recentEvents = history.recent.slice(0, 8);
  const unreadNotifs = notifs.notifications.filter((n) => !n.read);

  // Taste reflection: top 3 tags from the user's most-listened channels.
  const tasteReflection = (() => {
    if (history.recent.length === 0 || allChannels.length === 0) return null;
    const bySlug = new Map(allChannels.map((c) => [c.slug, c]));
    const tagCounts = new Map<string, number>();
    for (const event of history.recent) {
      const ch = bySlug.get(event.channel_slug);
      if (!ch) continue;
      for (const tag of [...(ch.genre ?? []), ...(ch.mood ?? [])]) {
        tagCounts.set(tag, (tagCounts.get(tag) ?? 0) + 1);
      }
    }
    const sorted = [...tagCounts.entries()].sort((a, b) => b[1] - a[1]).map(([t]) => t);
    if (sorted.length < 2) return null;
    return sorted.slice(0, 3).join(" · ");
  })();

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      {loadError && (
        <div className="mb-6 rounded-xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-100/90">
          Some sections couldn&apos;t load. Showing what we could —{" "}
          <button onClick={() => window.location.reload()} className="underline hover:text-amber-100">
            refresh to retry
          </button>
          .
        </div>
      )}

      {/* Greeting + resume */}
      <section className="mb-10">
        <h1 className="mb-1 text-3xl font-semibold tracking-tight text-white">
          {greeting(user!.display_name.split(" ")[0])}
        </h1>
        <p className="text-white/45">Your personal radio dashboard.</p>
        {tasteReflection && (
          <p className="mt-1 text-sm text-white/35">
            Your sound: <span className="text-wave-300/70">{tasteReflection}</span>
          </p>
        )}
      </section>

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Notifications */}
        {notifs.notifications.length > 0 && (
          <section id="notifications" className="lg:col-span-2">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="flex items-center gap-2 text-base font-semibold text-white">
                <Bell className="h-4 w-4 text-wave-400" />
                Notifications
                {notifs.unread_count > 0 && (
                  <span className="ml-1 rounded-full bg-wave-500 px-2 py-0.5 text-[10px] font-bold text-white">
                    {notifs.unread_count}
                  </span>
                )}
              </h2>
              {notifs.unread_count > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="text-xs text-white/40 hover:text-white/70"
                >
                  Mark all read
                </button>
              )}
            </div>
            <div className="glass rounded-2xl p-2 flex flex-col gap-1">
              {notifs.notifications.slice(0, 5).map((n) => (
                <NotifRow key={n.id} notif={n} onRead={handleNotifRead} />
              ))}
            </div>
          </section>
        )}

        {/* Followed channels */}
        {followedChannels.length > 0 && (
          <section>
            <SectionHeading
              icon={<Radio className="h-4 w-4 text-wave-400" />}
              title="Channels you follow"
              href="/follows"
            />
            <div className="flex flex-col gap-2">
              {followedChannels.slice(0, 4).map((c) => (
                <MiniChannelCard key={c.slug} channel={c} />
              ))}
            </div>
          </section>
        )}

        {/* Recently played */}
        {recentEvents.length > 0 && (
          <section>
            <SectionHeading
              icon={<Radio className="h-4 w-4 text-wave-400" />}
              title="Recently played"
            />
            <div className="glass rounded-2xl p-2 flex flex-col">
              {recentEvents.map((e) => (
                <EventRow key={e.id} event={e} />
              ))}
            </div>
          </section>
        )}

        {/* Saved channels */}
        {savedChannels.length > 0 && (
          <section>
            <SectionHeading
              icon={<Heart className="h-4 w-4 text-wave-400" />}
              title="Saved channels"
            />
            <div className="flex flex-col gap-2">
              {savedChannels.slice(0, 4).map((c) => (
                <MiniChannelCard key={c.slug} channel={c} />
              ))}
            </div>
          </section>
        )}

        {/* Recommendations */}
        {recs.length > 0 && (
          <section className={savedChannels.length === 0 ? "lg:col-span-2" : ""}>
            <SectionHeading
              icon={<Sparkles className="h-4 w-4 text-wave-400" />}
              title="Recommended for you"
            />
            <div className="flex flex-col gap-2">
              {recs.map((c) => (
                <MiniChannelCard key={c.slug} channel={c} reason={c._reason} />
              ))}
            </div>
          </section>
        )}

        {/* Creator panel */}
        {ownedChannels.length > 0 && (
          <section className="lg:col-span-2">
            <SectionHeading
              icon={<User className="h-4 w-4 text-wave-400" />}
              title="Your channels"
            />
            <div className="grid gap-2 sm:grid-cols-2">
              {ownedChannels.map((c) => (
                <Link
                  key={c.slug}
                  href={`/admin/channels/${c.slug}`}
                  className="group flex items-center gap-3 rounded-2xl border border-white/8 bg-white/3 px-4 py-3 transition hover:border-wave-500/30 hover:bg-white/6"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={c.coverImageUrl as string}
                    alt={c.title}
                    className="h-10 w-10 rounded-xl object-cover"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-white">{c.title}</p>
                    <p className="text-xs text-white/40">
                      {c.isPublished ? "Published" : "Unpublished"}
                      {" · "}
                      {(followerCounts[c.slug] ?? 0) > 0
                        ? `${followerCounts[c.slug].toLocaleString()} followers`
                        : "No followers yet"}
                    </p>
                  </div>
                  <ChevronRight className="h-4 w-4 shrink-0 text-white/30 group-hover:text-wave-400" />
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Empty state */}
        {recentEvents.length === 0 &&
          savedChannels.length === 0 &&
          followedChannels.length === 0 &&
          recs.length === 0 && (
            <section className="lg:col-span-2">
              <div className="glass rounded-3xl p-10 text-center">
                <Sparkles className="mx-auto mb-3 h-8 w-8 text-wave-400" />
                <p className="mb-2 font-semibold text-white">Welcome to WavePalace</p>
                <p className="mb-6 text-sm text-white/50">
                  Browse channels to start listening. Your history and recommendations will appear here.
                </p>
                <Link
                  href="/#channels"
                  className="inline-flex items-center gap-2 rounded-full bg-wave-500/20 px-5 py-2.5 text-sm font-semibold text-wave-300 hover:bg-wave-500/30"
                >
                  Browse channels
                  <ChevronRight className="h-4 w-4" />
                </Link>
              </div>
            </section>
          )}
      </div>
    </div>
  );
}
