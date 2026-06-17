"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/shared/lib/cn";

interface CopyLinkButtonProps {
  /** Static value to copy. Ignored when useCurrentUrl is true. */
  value?: string;
  /** When true, copies the live page URL (window.location.href) at click time. */
  useCurrentUrl?: boolean;
  label: string;
  successMessage: string;
  variant?: "primary" | "secondary";
}

export function CopyLinkButton({
  value,
  useCurrentUrl = false,
  label,
  successMessage,
  variant = "secondary",
}: CopyLinkButtonProps) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);
  const [shownValue, setShownValue] = useState(value ?? "");

  async function handleCopy() {
    const target = useCurrentUrl ? window.location.href : value ?? "";
    setShownValue(target);
    try {
      await navigator.clipboard.writeText(target);
      setFailed(false);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard access can fail (permissions/insecure context).
      setFailed(true);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={handleCopy}
        aria-live="polite"
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold transition focus-visible:outline-none",
          variant === "primary"
            ? "bg-gradient-to-r from-wave-500 to-glow-magenta text-white shadow-lg shadow-wave-600/30 hover:brightness-110"
            : "border border-white/15 bg-white/5 text-white/85 hover:bg-white/10"
        )}
      >
        {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
        {copied ? successMessage : label}
      </button>

      {failed && (
        <div className="rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
          <p className="mb-1 font-medium">Copy failed — here is the link:</p>
          <code className="block break-all text-amber-100/90">{shownValue}</code>
        </div>
      )}
    </div>
  );
}
