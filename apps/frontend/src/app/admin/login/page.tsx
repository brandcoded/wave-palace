"use client";

import { useRouter } from "next/navigation";
import { GlassPanel } from "@/presentation/components/GlassPanel";
import { SignInPanel } from "@/features/admin/components/SignInPanel";

export default function AdminLoginPage() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <GlassPanel className="w-full max-w-sm p-8">
        <h1 className="mb-6 text-lg font-semibold text-white">Admin</h1>
        <SignInPanel onSuccess={() => router.replace("/admin/submissions")} />
      </GlassPanel>
    </div>
  );
}
