import { Headphones } from "lucide-react";

export function CompatibilityNotice() {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-glow-cyan/20 bg-glow-cyan/5 p-4 text-sm text-white/70">
      <Headphones className="mt-0.5 h-5 w-5 shrink-0 text-glow-cyan" />
      <p>
        VRChat playback depends on the media host, HTTPS, player settings, and
        world configuration. Use only media you own, licensed, cleared, or have
        permission to stream.
      </p>
    </div>
  );
}
