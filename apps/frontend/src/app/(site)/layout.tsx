import { AppShell } from "@/presentation/components/AppShell";
import { AudioPlayerProvider } from "@/features/player/context/AudioPlayerContext";
import { MiniPlayerBar } from "@/features/player/components/MiniPlayerBar";

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <AudioPlayerProvider>
      <AppShell>{children}</AppShell>
      <MiniPlayerBar />
    </AudioPlayerProvider>
  );
}
