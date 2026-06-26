import Link from "next/link";
import { Disc3 } from "lucide-react";
import { GradientBackdrop } from "./GradientBackdrop";
import { RightsNotice } from "@/features/channels/components/RightsNotice";
import { CodeInput } from "./CodeInput";
import { UserMenuIsland } from "./UserMenuIsland";


export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col">
      <GradientBackdrop />

      <header className="sticky top-0 z-30 border-b border-white/5 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="group flex items-center gap-2">
            <Disc3 className="h-6 w-6 text-wave-400 transition-transform group-hover:rotate-90" />
            <span className="text-lg font-semibold tracking-tight">
              Wave<span className="text-gradient">Palace</span>
            </span>
          </Link>
          <nav className="flex items-center gap-3">
            <CodeInput />
            <Link
              href="/submit"
              className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white/70 transition hover:bg-white/10 hover:text-white"
            >
              Submit
            </Link>
            <Link
              href="/#channels"
              className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white/80 transition hover:bg-white/10"
            >
              Browse channels
            </Link>
            <UserMenuIsland />
          </nav>
        </div>
      </header>

      <main className="flex-1">{children}</main>

      <footer className="border-t border-white/5">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <RightsNotice />
          <div className="mt-6 flex items-center gap-4">
            <p className="text-xs text-white/40">
              © {new Date().getFullYear()} WavePalace — Visual radio for the web and VRChat.
            </p>
            <Link href="/brand" className="text-xs text-white/30 transition hover:text-white/60">
              Brand Kit
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
