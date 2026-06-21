import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, ExternalLink as ExternalLinkIcon } from "lucide-react";
import { getChannelBySlug, ApiError } from "@/features/channels/lib/channelApi";
import { ChannelPlayer } from "@/features/channels/components/ChannelPlayer";
import { CopyLinkButton } from "@/features/channels/components/CopyLinkButton";
import { CompatibilityNotice } from "@/features/channels/components/CompatibilityNotice";
import { RightsNotice } from "@/features/channels/components/RightsNotice";
import { GlassPanel } from "@/presentation/components/GlassPanel";
import { makeFollowCode } from "@/features/channels/lib/followCode";
import type { Channel } from "@/features/channels/types/channel";


export default async function ChannelDetailPage({
  params,
}: {
  params: { slug: string };
}) {
  let channel: Channel;
  try {
    channel = await getChannelBySlug(params.slug);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    // Backend unreachable or other error — show a friendly recoverable state.
    return (
      <div className="mx-auto max-w-3xl px-6 py-24 text-center">
        <h1 className="text-2xl font-semibold">We couldn&apos;t load this channel</h1>
        <p className="mt-3 text-white/60">
          The WavePalace API may be offline. Please check the backend is running
          and try again.
        </p>
        <Link
          href="/"
          className="mt-8 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-5 py-2.5 text-sm font-medium text-white/80 hover:bg-white/10"
        >
          <ArrowLeft className="h-4 w-4" /> Back to directory
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-12">
      <Link
        href="/#channels"
        className="mb-8 inline-flex items-center gap-2 text-sm text-white/55 transition hover:text-white"
      >
        <ArrowLeft className="h-4 w-4" /> All channels
      </Link>

      <div className="grid gap-10 lg:grid-cols-[1.6fr_1fr]">
        {/* Player + header */}
        <div className="flex flex-col gap-6">
          {/* Now Playing badge */}
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400 opacity-60" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-cyan-400" />
            </span>
            <span className="text-xs font-semibold uppercase tracking-widest text-cyan-400">
              Now Playing
            </span>
          </div>

          <ChannelPlayer
            tracks={channel.playlist?.length ? channel.playlist : [{ url: channel.audioUrl, title: "", artist: "" }]}
            slug={channel.slug}
            coverImage={channel.coverImageUrl}
            visualLoopUrl={channel.visualLoopUrl}
            title={channel.title}
            hostName={channel.hostName}
            genre={channel.genre}
            mood={channel.mood}
            sponsor={channel.sponsor}
          />

          <p className="max-w-2xl leading-relaxed text-white/70">
            {channel.description}
          </p>
        </div>

        {/* Actions panel */}
        <aside className="flex flex-col gap-5">
          <GlassPanel className="flex flex-col gap-4 p-6">
            <h2 className="text-sm font-semibold uppercase tracking-widest text-white/50">
              Share this channel
            </h2>
            <CopyLinkButton
              useCurrentUrl
              label="Copy Web Link"
              successMessage="Web link copied"
              variant="secondary"
            />
            <CopyLinkButton
              value={channel.vrchatPlaybackUrl}
              label="Copy VRChat Link"
              successMessage="VRChat link copied"
              variant="primary"
            />

            {(() => {
              const firstTrack = channel.playlist?.[0];
              const code = firstTrack
                ? makeFollowCode(channel.slug, firstTrack.title, 0)
                : null;
              return code ? (
                <Link
                  href={`/follow/${code}`}
                  className="flex w-full flex-col gap-1 rounded-2xl border border-wave-400/20 bg-wave-400/5 px-4 py-3 transition hover:bg-wave-400/10"
                >
                  <span className="text-xs font-semibold uppercase tracking-widest text-wave-400/70">
                    Follow this channel
                  </span>
                  <span className="text-sm text-white/65">
                    Enter code{" "}
                    <code className="font-mono font-bold text-wave-300">{code}</code>
                    {" "}at wavepalace.live
                  </span>
                </Link>
              ) : null;
            })()}

            {channel.externalLinks.length > 0 && (
              <div className="border-t border-white/10 pt-4">
                <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-white/40">
                  Listen elsewhere
                </p>
                <ul className="flex flex-col gap-1.5">
                  {channel.externalLinks.map((link) => (
                    <li key={link.url}>
                      <a
                        href={link.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 text-sm text-wave-400 hover:text-wave-300"
                      >
                        <ExternalLinkIcon className="h-3.5 w-3.5" />
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </GlassPanel>

          <CompatibilityNotice />
          <RightsNotice />
        </aside>
      </div>
    </div>
  );
}
