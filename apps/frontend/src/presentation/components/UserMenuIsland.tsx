"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bell, LayoutDashboard, LogOut, User } from "lucide-react";
import { getMe, getUnreadCount } from "@/features/me/lib/meApi";
import { logout } from "@/features/admin/lib/adminApi";
import type { CurrentUser } from "@/features/admin/types/admin";

export function UserMenuIsland() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    getMe().then((me) => {
      setUser(me);
      if (me) getUnreadCount().then(setUnread);
    });
  }, []);

  async function handleLogout() {
    await logout();
    setUser(null);
    setUnread(0);
    setOpen(false);
    window.location.href = "/";
  }

  if (!user) {
    return (
      <Link
        href="/admin/login"
        className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-white/70 transition hover:bg-white/10 hover:text-white"
      >
        Sign in
      </Link>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 transition hover:bg-white/10"
      >
        {user.avatar_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={user.avatar_url} alt="" className="h-5 w-5 rounded-full object-cover" />
        ) : (
          <User className="h-4 w-4 text-white/60" />
        )}
        <span className="max-w-[90px] truncate text-xs font-medium text-white/80">
          {user.display_name}
        </span>
        {unread > 0 && (
          <span className="flex h-4 w-4 items-center justify-center rounded-full bg-wave-500 text-[9px] font-bold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-10 z-50 w-44 rounded-2xl border border-white/10 bg-ink-900/95 p-1.5 shadow-2xl backdrop-blur-xl">
            <Link
              href="/home"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm text-white/80 transition hover:bg-white/8 hover:text-white"
            >
              <LayoutDashboard className="h-3.5 w-3.5" />
              Dashboard
            </Link>
            <Link
              href="/home"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm text-white/80 transition hover:bg-white/8 hover:text-white"
            >
              <Bell className="h-3.5 w-3.5" />
              Notifications
              {unread > 0 && (
                <span className="ml-auto flex h-4 w-4 items-center justify-center rounded-full bg-wave-500 text-[9px] font-bold text-white">
                  {unread > 9 ? "9+" : unread}
                </span>
              )}
            </Link>
            <div className="my-1 border-t border-white/8" />
            <button
              onClick={handleLogout}
              className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-sm text-white/50 transition hover:bg-white/8 hover:text-white"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign out
            </button>
          </div>
        </>
      )}
    </div>
  );
}
