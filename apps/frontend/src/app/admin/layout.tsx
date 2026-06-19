"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Music2, Users, Settings, LogOut, Menu, X } from "lucide-react";
import { AdminAuthProvider, useAdminAuth } from "@/features/admin/lib/adminAuth";

const NAV = [
  { href: "/admin/submissions", label: "Submissions", icon: Users },
  { href: "/admin/channels",    label: "Channels",    icon: Music2 },
  { href: "/admin/options",     label: "Options",     icon: Settings },
];

function NavLinks({ pathname, onClick }: { pathname: string; onClick?: () => void }) {
  return (
    <>
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            onClick={onClick}
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
    </>
  );
}

function AdminShell({ children }: { children: React.ReactNode }) {
  const { checked, authed, logout } = useAdminAuth();
  const pathname = usePathname();
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Close drawer on navigation
  useEffect(() => { setDrawerOpen(false); }, [pathname]);

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
      {/* Desktop sidebar — hidden below lg */}
      <aside className="hidden lg:flex w-56 shrink-0 flex-col border-r border-white/10 bg-black/60 px-3 py-6">
        <p className="mb-6 px-3 text-xs font-bold uppercase tracking-widest text-white/30">
          WavePalace Admin
        </p>
        <nav className="flex flex-col gap-1">
          <NavLinks pathname={pathname} />
        </nav>
        <button
          onClick={logout}
          className="mt-auto flex items-center gap-2 px-3 py-2 text-xs text-white/30 hover:text-white/60 transition"
        >
          <LogOut className="h-3.5 w-3.5" /> Sign out
        </button>
      </aside>

      {/* Mobile top bar — visible below lg */}
      <div className="fixed inset-x-0 top-0 z-40 flex items-center justify-between border-b border-white/10 bg-black/80 px-4 py-3 backdrop-blur-sm lg:hidden">
        <p className="text-xs font-bold uppercase tracking-widest text-white/40">
          WavePalace Admin
        </p>
        <button
          onClick={() => setDrawerOpen(true)}
          aria-label="Open navigation"
          className="flex h-9 w-9 items-center justify-center rounded-lg text-white/60 hover:bg-white/10 hover:text-white transition"
        >
          <Menu className="h-5 w-5" />
        </button>
      </div>

      {/* Mobile drawer overlay */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setDrawerOpen(false)}
          />
          {/* Drawer panel */}
          <aside className="absolute inset-y-0 left-0 flex w-64 flex-col border-r border-white/10 bg-black/95 px-3 py-6 backdrop-blur-xl">
            <div className="mb-6 flex items-center justify-between px-3">
              <p className="text-xs font-bold uppercase tracking-widest text-white/30">
                WavePalace Admin
              </p>
              <button
                onClick={() => setDrawerOpen(false)}
                className="text-white/40 hover:text-white transition"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <nav className="flex flex-col gap-1">
              <NavLinks pathname={pathname} onClick={() => setDrawerOpen(false)} />
            </nav>
            <button
              onClick={() => { setDrawerOpen(false); logout(); }}
              className="mt-auto flex items-center gap-2 px-3 py-2 text-xs text-white/30 hover:text-white/60 transition"
            >
              <LogOut className="h-3.5 w-3.5" /> Sign out
            </button>
          </aside>
        </div>
      )}

      {/* Main content — offset top on mobile to clear the sticky top bar */}
      <main className="flex-1 overflow-auto p-4 pt-16 lg:p-8">
        {children}
      </main>
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
