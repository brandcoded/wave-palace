/** Atmospheric animated background blobs. Decorative only. */
export function GradientBackdrop() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-ink-950"
    >
      <div className="absolute -top-40 -left-32 h-[40rem] w-[40rem] rounded-full bg-wave-600/30 blur-3xl animate-drift" />
      <div className="absolute top-1/3 -right-40 h-[36rem] w-[36rem] rounded-full bg-glow-cyan/20 blur-3xl animate-drift [animation-delay:-6s]" />
      <div className="absolute bottom-0 left-1/4 h-[32rem] w-[32rem] rounded-full bg-glow-magenta/20 blur-3xl animate-drift [animation-delay:-12s]" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_-20%,rgba(124,58,237,0.25),transparent_60%)]" />
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-ink-950/40 to-ink-950" />
    </div>
  );
}
