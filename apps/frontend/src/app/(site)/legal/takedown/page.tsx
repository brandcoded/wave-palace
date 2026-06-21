import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { TakedownForm } from "./TakedownForm";

export const metadata = {
  title: "Copyright Takedown — WavePalace",
};

export default function TakedownPage() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-12">
      <Link
        href="/legal"
        className="mb-8 inline-flex items-center gap-2 text-sm text-white/50 transition hover:text-white"
      >
        <ArrowLeft className="h-4 w-4" /> Legal
      </Link>

      <h1 className="mb-2 text-3xl font-bold text-white">
        Copyright Takedown Request
      </h1>
      <p className="mb-8 text-white/55">
        If you believe content on WavePalace infringes your copyright, complete
        this form. We will review your claim and respond within 5 business days.
      </p>

      <TakedownForm />
    </div>
  );
}
