"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { GlassPanel } from "@/presentation/components/GlassPanel";
import { SignInPanel } from "@/features/admin/components/SignInPanel";
import { checkSession, acceptHostInvite } from "@/features/admin/lib/adminApi";

type State =
  | { status: "loading" }
  | { status: "needs_login" }
  | { status: "accepting" }
  | { status: "accepted"; channelTitle: string }
  | { status: "error"; message: string };

function HostJoinInner() {
  const params = useSearchParams();
  const token = params.get("token") ?? "";
  const [state, setState] = useState<State>({ status: "loading" });

  const accept = useCallback(async () => {
    setState({ status: "accepting" });
    try {
      const res = await acceptHostInvite(token);
      setState({ status: "accepted", channelTitle: res.channel_title });
    } catch (e) {
      setState({
        status: "error",
        message:
          e instanceof Error
            ? e.message
            : "This invite link has expired or already been used.",
      });
    }
  }, [token]);

  const resolve = useCallback(async () => {
    if (!token) {
      setState({ status: "error", message: "Missing invite token." });
      return;
    }
    try {
      await checkSession();
      await accept();
    } catch {
      setState({ status: "needs_login" });
    }
  }, [token, accept]);

  useEffect(() => {
    resolve();
  }, [resolve]);

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <GlassPanel className="w-full max-w-sm p-8">
        {state.status === "loading" && (
          <p className="text-sm text-white/50">Checking your invite…</p>
        )}

        {state.status === "needs_login" && (
          <>
            <h1 className="mb-2 text-lg font-semibold text-white">
              Accept your host invitation
            </h1>
            <p className="mb-6 text-sm text-white/50">
              Sign in to accept your WavePalace host invitation.
            </p>
            <SignInPanel onSuccess={accept} />
          </>
        )}

        {state.status === "accepting" && (
          <p className="text-sm text-white/50">Accepting your invitation…</p>
        )}

        {state.status === "accepted" && (
          <>
            <h1 className="mb-2 text-lg font-semibold text-white">
              You&rsquo;re now a host of {state.channelTitle}.
            </h1>
            <p className="mb-6 text-sm text-white/50">
              Manage your channel from your host dashboard.
            </p>
            <Link
              href="/host"
              className="inline-block rounded-lg bg-white/10 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/20"
            >
              Go to your dashboard →
            </Link>
          </>
        )}

        {state.status === "error" && (
          <>
            <h1 className="mb-2 text-lg font-semibold text-white">Invite unavailable</h1>
            <p className="text-sm text-white/50">
              This invite link has expired or already been used. Contact your music
              director for a new one.
            </p>
          </>
        )}
      </GlassPanel>
    </div>
  );
}

export default function HostJoinPage() {
  return (
    <Suspense fallback={null}>
      <HostJoinInner />
    </Suspense>
  );
}
