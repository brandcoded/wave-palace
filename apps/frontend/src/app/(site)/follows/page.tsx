"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { deleteFollow, getMyFollows, type FollowView } from "@/features/follow/lib/followApi";

export default function MyFollowsPage() {
  const [follows, setFollows] = useState<FollowView[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMyFollows()
      .then(setFollows)
      .finally(() => setLoading(false));
  }, []);

  async function handleUnfollow(id: string) {
    await deleteFollow(id);
    setFollows((prev) => prev.filter((f) => f.id !== id));
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
            <li
              key={f.id}
              className="glass flex items-center justify-between rounded-2xl px-5 py-4"
            >
              <div>
                <p className="font-semibold text-white">{f.display_name}</p>
                <p className="text-xs text-white/40">
                  via {f.notification_channel}
                  {!f.confirmed && " · pending confirmation"}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <Link
                  href={`/channels/${f.channel_slug}`}
                  className="text-xs text-wave-400 hover:underline"
                >
                  Listen
                </Link>
                <button
                  onClick={() => handleUnfollow(f.id)}
                  className="text-xs text-white/30 hover:text-red-400"
                >
                  Unfollow
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
