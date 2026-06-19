import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function ChannelNotFound() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-24 text-center">
      <p className="text-sm font-semibold uppercase tracking-[0.3em] text-wave-400">
        404
      </p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">
        This channel isn&apos;t on air
      </h1>
      <p className="mt-3 text-white/60">
        It may be unpublished, removed, or the link may be incorrect.
      </p>
      <Link
        href="/#channels"
        className="mt-8 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-5 py-2.5 text-sm font-medium text-white/80 hover:bg-white/10"
      >
        <ArrowLeft className="h-4 w-4" /> Back to directory
      </Link>
    </div>
  );
}
