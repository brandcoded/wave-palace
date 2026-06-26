import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { resolveCode } from "@/features/follow/lib/followApi";
import type { CurrentUser } from "@/features/admin/types/admin";
import { FollowForm } from "./FollowForm";

interface Props {
  params: { code: string };
}

export default async function FollowCodePage({ params }: Props) {
  const info = await resolveCode(params.code.toUpperCase());
  if (!info) notFound();

  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
    "http://localhost:8000";

  const discordInitiateUrl = `${API_BASE_URL}/api/auth/discord/initiate?code=${info.code}`;

  // Resolve the current user server-side so FollowForm renders the right UI
  // on first paint with no loading flash — works for all browsers including
  // VRChat's in-world browser and mobile QR scans.
  let currentUser: CurrentUser | null = null;
  try {
    const cookieStore = cookies();
    const sessionCookie = cookieStore.get("wp_session");
    if (sessionCookie?.value) {
      const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
        headers: { Cookie: `wp_session=${sessionCookie.value}` },
        cache: "no-store",
      });
      if (res.ok) currentUser = await res.json();
    }
  } catch {
    // Non-fatal — fall through to logged-out form
  }

  return (
    <div className="mx-auto max-w-lg px-6 py-20">
      <div className="glass rounded-3xl p-8 text-center">
        {info.cover_image_url && (
          <img
            src={info.cover_image_url}
            alt={info.display_name}
            className="mx-auto mb-6 h-28 w-28 rounded-2xl object-cover"
          />
        )}
        <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-wave-400">
          You scanned a code for
        </p>
        <h1 className="mb-1 text-2xl font-bold text-white">{info.display_name}</h1>
        {info.host_name && (
          <p className="mb-2 text-sm text-white/50">hosted by {info.host_name}</p>
        )}
        {(info.track_title || info.track_artist) && (
          <p className="mb-4 text-sm text-white/70">
            You were listening to{" "}
            {info.track_title && (
              <span className="font-semibold text-white">{info.track_title}</span>
            )}
            {info.track_title && info.track_artist && " by "}
            {info.track_artist && (
              <span className="font-semibold text-white">{info.track_artist}</span>
            )}
          </p>
        )}
        {(info.genre?.length || info.mood?.length) && (
          <p className="mb-8 text-xs text-white/40">
            {[...(info.genre ?? []), ...(info.mood ?? [])].join(" · ")}
          </p>
        )}

        <p className="mb-6 text-sm text-white/60">
          {info.track_artist
            ? `Follow this channel and never miss when ${info.track_artist} drops new music or goes live.`
            : "Follow this channel to get notified about events, guest DJs, and new music."}
        </p>

        <FollowForm code={info.code} discordInitiateUrl={discordInitiateUrl} currentUser={currentUser} />
      </div>
    </div>
  );
}
