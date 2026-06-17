import { ShieldCheck } from "lucide-react";

export function RightsNotice() {
  return (
    <div className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-white/60">
      <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-wave-400" />
      <p>
        WavePalace does not grant music rights. All media must be owned,
        licensed, cleared, public-domain, or submitted with permission. External
        streaming links (Spotify, Apple Music, etc.) are attribution only and are
        never used as playback sources.
      </p>
    </div>
  );
}
