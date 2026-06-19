import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";
import { SectionHeading } from "@/presentation/components/SectionHeading";
import { ChannelGrid } from "@/features/channels/components/ChannelGrid";

export default function HomePage() {
  return (
    <div className="mx-auto max-w-6xl px-6">
      {/* Hero */}
      <section className="relative flex flex-col items-center py-24 text-center sm:py-32">
        <span className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-medium text-white/70 animate-fade-up">
          <Sparkles className="h-3.5 w-3.5 text-wave-400" />
          Visual radio · web + VRChat
        </span>
        <h1 className="max-w-3xl text-5xl font-semibold leading-[1.05] tracking-tight sm:text-7xl animate-fade-up">
          Wave<span className="text-gradient">Palace</span>
        </h1>
        <p className="mt-6 max-w-2xl text-balance text-lg leading-relaxed text-white/65 animate-fade-up [animation-delay:80ms]">
          Curated music and shareable playback links for
          lounges, worlds, parties, and late-night digital spaces.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-3 animate-fade-up [animation-delay:160ms]">
          <Link
            href="#channels"
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-wave-500 to-glow-magenta px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-wave-600/30 transition hover:brightness-110"
          >
            Browse channels
            <ArrowRight className="h-4 w-4" />
          </Link>
          <a
            href="#channels"
            className="rounded-full border border-white/15 bg-white/5 px-6 py-3 text-sm font-semibold text-white/80 transition hover:bg-white/10"
          >
            How it works
          </a>
        </div>
      </section>

      {/* Directory */}
      <section id="channels" className="scroll-mt-24 pb-24">
        <div className="mb-10">
          <SectionHeading
            eyebrow="The Directory"
            title="Tune into a channel"
            description="Browse curated visual-audio channels by genre, mood, energy, and theme. Open one to play it in your browser and grab shareable web or VRChat links."
          />
        </div>
        <ChannelGrid />
      </section>
    </div>
  );
}
