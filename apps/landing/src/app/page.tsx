import { Nav } from "@/components/Nav";
import { Hero } from "@/components/Hero";
import { PlayerMock } from "@/components/PlayerMock";
import { HowItWorks } from "@/components/HowItWorks";
import { Personas } from "@/components/Personas";
import { ProofLine } from "@/components/ProofLine";
import { Footer } from "@/components/Footer";

export default function LandingPage() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <PlayerMock />
        <HowItWorks />
        <Personas />
        <ProofLine />
      </main>
      <Footer />
    </>
  );
}
