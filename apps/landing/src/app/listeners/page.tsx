import { Nav } from "@/components/Nav";
import { ListenerHero } from "@/components/ListenerHero";
import { PlayerMock } from "@/components/PlayerMock";
import { HowToListen } from "@/components/HowToListen";
import { WhyNotStreaming } from "@/components/WhyNotStreaming";
import { ListenerPersonas } from "@/components/ListenerPersonas";
import { ListenerProofLine } from "@/components/ListenerProofLine";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "WavePalace — Listen",
  description:
    "Curated music channels that play continuously — in your browser, in VRChat worlds, no account required. No algorithm. Just the dial.",
};

export default function ListenersPage() {
  return (
    <>
      <Nav />
      <main>
        <ListenerHero />
        <PlayerMock />
        <HowToListen />
        <WhyNotStreaming />
        <ListenerPersonas />
        <ListenerProofLine />
      </main>
      <Footer />
    </>
  );
}
