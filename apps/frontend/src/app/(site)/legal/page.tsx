import Link from "next/link";
import { ArrowRight, Shield, FileText, Lock } from "lucide-react";

export default function LegalIndexPage() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-20">
      <h1 className="mb-3 text-3xl font-bold text-white">Legal</h1>
      <p className="mb-12 text-white/55">
        Policies, rights, and reporting for WavePalace.
      </p>

      <div className="flex flex-col gap-4">
        <Link
          href="/legal/takedown"
          className="glass flex items-center gap-4 rounded-2xl p-6 transition hover:bg-white/5"
        >
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-red-400/10">
            <Shield className="h-5 w-5 text-red-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-white">Copyright Takedown (DMCA)</p>
            <p className="mt-0.5 text-sm text-white/50">
              Report infringing content on WavePalace channels.
            </p>
          </div>
          <ArrowRight className="h-4 w-4 shrink-0 text-white/30" />
        </Link>

        <div className="glass flex items-center gap-4 rounded-2xl p-6 opacity-50 cursor-default">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/5">
            <Lock className="h-5 w-5 text-white/40" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-white">Privacy Policy</p>
            <p className="mt-0.5 text-sm text-white/50">Coming soon.</p>
          </div>
        </div>

        <div className="glass flex items-center gap-4 rounded-2xl p-6 opacity-50 cursor-default">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white/5">
            <FileText className="h-5 w-5 text-white/40" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-white">Terms of Service</p>
            <p className="mt-0.5 text-sm text-white/50">Coming soon.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
