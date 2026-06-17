import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/presentation/components/AppShell";

export const metadata: Metadata = {
  title: "WavePalace — Visual radio for the web and VRChat",
  description:
    "Curated music channels, cinematic loops, and shareable playback links for lounges, worlds, parties, and late-night digital spaces.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
