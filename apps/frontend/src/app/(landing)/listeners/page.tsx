import { LandingNav } from "@/features/landing/components/Nav";
import { ListenerHero } from "@/features/landing/components/ListenerHero";
import { PlayerMock } from "@/features/landing/components/PlayerMock";
import { HowToListen } from "@/features/landing/components/HowToListen";
import { WhyNotStreaming } from "@/features/landing/components/WhyNotStreaming";
import { ListenerPersonas } from "@/features/landing/components/ListenerPersonas";
import { ListenerProofLine } from "@/features/landing/components/ListenerProofLine";
import { LandingFooter } from "@/features/landing/components/Footer";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "WavePalace — For Listeners",
  description:
    "Curated music channels that play continuously — in your browser, in VRChat worlds, no account required. No algorithm. Just the dial.",
};

export default function ListenersPage() {
  return (
    <div style={{ backgroundColor: "var(--wp-black)", color: "var(--wp-white)" }}>
      <LandingNav />
      <main>
        <ListenerHero />
        <PlayerMock />
        <HowToListen />
        <WhyNotStreaming />
        <ListenerPersonas />
        <ListenerProofLine />
      </main>
      <LandingFooter />
    </div>
  );
}
