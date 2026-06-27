"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  deleteFollow,
  getMyFollows,
  updateFollowPrefs,
  type FollowView,
} from "@/features/follow/lib/followApi";

// User-specific, auth-gated page that reads query params client-side — render
// on demand instead of static prerender (avoids the useSearchParams CSR bailout
// that otherwise fails the production build).
export const dynamic = "force-dynamic";

function isEarlyListener(follow: FollowView): boolean {
  if (!follow.channel_created_at) return false;
  const followedAt = new Date(follow.created_at).getTime();
  const channelLaunchedAt = new Date(follow.channel_created_at).getTime();
  const ninetyDays = 90 * 24 * 60 * 60 * 1000;
  return followedAt - channelLaunchedAt <= ninetyDays;
}

// Expandable notification-preference row
function FollowRow({
  follow,
  onUnfollow,
  onPrefsChange,
}: {
  follow: FollowView;
  onUnfollow: (id: string) => void;
  onPrefsChange: (updated: FollowView) => void;
}) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const confirmTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleUnfollowClick() {
    if (!confirming) {
      setConfirming(true);
      confirmTimerRef.current = setTimeout(() => setConfirming(false), 2000);
      return;
    }
    clearTimeout(confirmTimerRef.current!);
    setConfirming(false);
    onUnfollow(follow.id);
  }

  async function toggle(
    field: "notify_new_tracks" | "notify_channel_live" | "notify_digest"
  ) {
    setSaving(true);
    try {
      const updated = await updateFollowPrefs(follow.id, {
        [field]: !follow[field],
      });
      onPrefsChange(updated);
    } finally {
      setSaving(false);
    }
  }

  return (
    <li className="glass rounded-2xl overflow-hidden">
      {/* Main row */}
      <div className="flex items-center justify-between px-5 py-4">
        <div>
          <div className="flex items-center gap-2">
            <p className="font-semibold text-white">{follow.display_name}</p>
            {isEarlyListener(follow) && (
              <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-2 py-0.5 text-[10px] font-semibold text-amber-300">
                Early listener
              </span>
            )}
          </div>
          <p className="text-xs text-white/40">
            via {follow.notification_channel}
            {!follow.confirmed && " · pending confirmation"}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href={`/channels/${follow.channel_slug}`}
            className="text-xs text-wave-400 hover:underline"
          >
            Listen
          </Link>
          <button
            onClick={() => setOpen((o) => !o)}
            className="text-xs text-white/40 hover:text-white/70"
            aria-expanded={open}
          >
            {open ? "Close" : "Preferences"}
          </button>
          <button
            onClick={handleUnfollowClick}
            className={`text-xs transition ${
              confirming
                ? "text-red-400 hover:text-red-300"
                : "text-white/30 hover:text-red-400"
            }`}
          >
            {confirming ? "Confirm?" : "Unfollow"}
          </button>
        </div>
      </div>

      {/* Expandable preferences panel */}
      {open && (
        <div className="border-t border-white/5 px-5 py-4">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-white/30">
            Notify me when…
          </p>
          <div className="flex flex-col gap-2">
            <PrefToggle
              label="New tracks are added"
              checked={follow.notify_new_tracks}
              disabled={saving}
              onChange={() => toggle("notify_new_tracks")}
            />
            <PrefToggle
              label="Channel goes live"
              checked={follow.notify_channel_live}
              disabled={saving}
              onChange={() => toggle("notify_channel_live")}
            />
            <PrefToggle
              label="Weekly digest"
              checked={follow.notify_digest}
              disabled={saving}
              onChange={() => toggle("notify_digest")}
            />
          </div>
        </div>
      )}
    </li>
  );
}

function PrefToggle({
  label,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  checked: boolean;
  disabled: boolean;
  onChange: () => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-3">
      <button
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={onChange}
        className={`relative h-5 w-9 rounded-full transition-colors ${
          checked ? "bg-wave-500" : "bg-white/10"
        } disabled:opacity-50`}
      >
        <span
          className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${
            checked ? "translate-x-4" : "translate-x-0"
          }`}
        />
      </button>
      <span className="text-sm text-white/70">{label}</span>
    </label>
  );
}

function MyFollowsContent() {
  const [follows, setFollows] = useState<FollowView[]>([]);
  const [loading, setLoading] = useState(true);
  const [banner, setBanner] = useState<string | null>(null);
  const unsubscribeHandled = useRef(false);
  const searchParams = useSearchParams();

  useEffect(() => {
    getMyFollows()
      .then(setFollows)
      .finally(() => setLoading(false));
  }, []);

  // Handle ?unsubscribe={follow_id} deep link
  useEffect(() => {
    if (unsubscribeHandled.current) return;
    const followId = searchParams.get("unsubscribe");
    if (!followId) return;
    unsubscribeHandled.current = true;

    deleteFollow(followId).then(() => {
      setFollows((prev) => prev.filter((f) => f.id !== followId));
      setBanner("You've been unsubscribed.");
    });
  }, [searchParams]);

  async function handleUnfollow(id: string) {
    await deleteFollow(id);
    setFollows((prev) => prev.filter((f) => f.id !== id));
  }

  function handlePrefsChange(updated: FollowView) {
    setFollows((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-20 text-center text-white/40">
        Loading…
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-20">
      <h1 className="mb-8 text-2xl font-bold text-white">My Follows</h1>

      {banner && (
        <div className="mb-6 rounded-2xl bg-white/5 px-5 py-3 text-sm text-white/70">
          {banner}
        </div>
      )}

      {follows.length === 0 ? (
        <div className="glass rounded-3xl p-10 text-center">
          <p className="mb-4 text-white/60">You haven&apos;t followed any channels yet.</p>
          <p className="mb-6 text-sm text-white/40">
            Scan a code in-world or enter a 6-character code in the header to follow a channel.
          </p>
          <Link
            href="/"
            className="rounded-full border border-white/10 bg-white/5 px-6 py-2.5 text-sm font-semibold text-white hover:bg-white/10"
          >
            Browse channels
          </Link>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {follows.map((f) => (
            <FollowRow
              key={f.id}
              follow={f}
              onUnfollow={handleUnfollow}
              onPrefsChange={handlePrefsChange}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

export default function MyFollowsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[40vh] items-center justify-center">
          <p className="text-white/30">Loading…</p>
        </div>
      }
    >
      <MyFollowsContent />
    </Suspense>
  );
}
