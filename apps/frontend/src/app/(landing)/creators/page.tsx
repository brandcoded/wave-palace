import { LandingNav } from "@/features/landing/components/Nav";
import { Hero } from "@/features/landing/components/Hero";
import { PlayerMock } from "@/features/landing/components/PlayerMock";
import { HowItWorks } from "@/features/landing/components/HowItWorks";
import { Personas } from "@/features/landing/components/Personas";
import { ProofLine } from "@/features/landing/components/ProofLine";
import { LandingFooter } from "@/features/landing/components/Footer";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "WavePalace — For Creators",
  description:
    "Build a permanent looping channel that plays in VRChat worlds and links anywhere on the web. A live set lasts a night. A channel lasts.",
};

export default function CreatorsPage() {
  return (
    <div style={{ backgroundColor: "var(--wp-black)", color: "var(--wp-white)" }}>
      <LandingNav />
      <main>
        <Hero />
        <PlayerMock />
        <HowItWorks />
        <Personas />
        <ProofLine />
      </main>
      <LandingFooter />
    </div>
  );
}
