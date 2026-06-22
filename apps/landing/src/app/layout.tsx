import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "WavePalace — Creator-owned channels",
  description:
    "WavePalace is where DJs, artists, and curators build permanent looping channels that play in VRChat worlds and link anywhere on the web.",
  metadataBase: new URL("https://wavepalace.live"),
  openGraph: {
    title: "WavePalace — Creator-owned channels",
    description:
      "WavePalace is where DJs, artists, and curators build permanent looping channels that play in VRChat worlds and link anywhere on the web.",
    url: "https://wavepalace.live",
    siteName: "WavePalace",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body>{children}</body>
    </html>
  );
}
