import Link from "next/link";
import { CheckCircle } from "lucide-react";

export const metadata = {
  title: "Request Received — WavePalace",
};

export default function TakedownSubmittedPage() {
  return (
    <div className="mx-auto max-w-lg px-6 py-24 text-center">
      <div className="mb-6 flex justify-center">
        <CheckCircle className="h-14 w-14 text-emerald-400" />
      </div>
      <h1 className="mb-3 text-2xl font-bold text-white">Request received</h1>
      <p className="mb-8 text-white/60">
        Your takedown request has been submitted. We&apos;ll review it and
        respond to your email within 5 business days.
      </p>
      <Link
        href="/"
        className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-5 py-2.5 text-sm font-medium text-white/80 transition hover:bg-white/10"
      >
        Back to WavePalace
      </Link>
    </div>
  );
}
