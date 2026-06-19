"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Music2, Users, Settings, LogOut } from "lucide-react";
import { AdminAuthProvider, useAdminAuth } from "@/features/admin/lib/adminAuth";

const NAV = [
  { href: "/admin/submissions", label: "Submissions", icon: Users },
  { href: "/admin/channels",    label: "Channels",    icon: Music2 },
  { href: "/admin/options",     label: "Options",     icon: Settings },
];

function AdminShell({ children }: { children: React.ReactNode }) {
  const { checked, authed, logout } = useAdminAuth();
  const pathname = usePathname();

  if (!checked) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <span className="text-white/40 text-sm">Checking session…</span>
      </div>
    );
  }

  if (!authed && pathname !== "/admin/login") return null;

  if (!authed) return <>{children}</>;

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="flex w-56 shrink-0 flex-col border-r border-white/10 bg-black/60 px-3 py-6">
        <p className="mb-6 px-3 text-xs font-bold uppercase tracking-widest text-white/30">
          WavePalace Admin
        </p>
        <nav className="flex flex-col gap-1">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  active
                    ? "bg-white/10 text-white"
                    : "text-white/50 hover:bg-white/5 hover:text-white"
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {label}
              </Link>
            );
          })}
        </nav>
        <button
          onClick={logout}
          className="mt-auto flex items-center gap-2 px-3 py-2 text-xs text-white/30 hover:text-white/60 transition"
        >
          <LogOut className="h-3.5 w-3.5" /> Sign out
        </button>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto p-8">{children}</main>
    </div>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminAuthProvider>
      <AdminShell>{children}</AdminShell>
    </AdminAuthProvider>
  );
}
