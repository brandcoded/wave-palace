"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

function ConfirmContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const [channelSlug, setChannelSlug] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setStatus("error");
      return;
    }
    fetch(`${API_BASE_URL}/api/follows/confirm?token=${encodeURIComponent(token)}`, {
      method: "POST",
      credentials: "include",
    })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data) => {
        setChannelSlug(data.channel_slug ?? null);
        setStatus("ok");
      })
      .catch(() => setStatus("error"));
  }, [token]);

  return (
    <div className="glass rounded-3xl p-8">
      {status === "loading" && (
        <p className="text-white/60">Confirming your follow…</p>
      )}
      {status === "ok" && (
        <>
          <p className="mb-2 text-2xl">✓</p>
          <h1 className="mb-3 text-xl font-bold text-white">You&apos;re in!</h1>
          <p className="mb-6 text-sm text-white/60">
            You&apos;ll receive email notifications for{" "}
            {channelSlug ? (
              <Link href={`/channels/${channelSlug}`} className="text-wave-400 underline">
                {channelSlug}
              </Link>
            ) : (
              "this channel"
            )}
            .
          </p>
          <Link
            href="/"
            className="rounded-full bg-wave-500 px-6 py-2.5 text-sm font-semibold text-white hover:bg-wave-400"
          >
            Browse channels
          </Link>
        </>
      )}
      {status === "error" && (
        <>
          <p className="mb-3 text-xl font-bold text-white">Link expired or invalid</p>
          <p className="mb-6 text-sm text-white/60">
            This confirmation link has expired or was already used. Scan your code again to
            re-follow.
          </p>
          <Link
            href="/"
            className="rounded-full border border-white/10 bg-white/5 px-6 py-2.5 text-sm font-semibold text-white hover:bg-white/10"
          >
            Go home
          </Link>
        </>
      )}
    </div>
  );
}

export default function FollowConfirmPage() {
  return (
    <div className="mx-auto max-w-lg px-6 py-20 text-center">
      <Suspense fallback={<div className="glass rounded-3xl p-8 text-white/40">Loading…</div>}>
        <ConfirmContent />
      </Suspense>
    </div>
  );
}
