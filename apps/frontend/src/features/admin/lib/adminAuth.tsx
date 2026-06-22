"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { checkSession, logout as apiLogout } from "./adminApi";
import type { UserRole } from "@/features/admin/types/admin";

interface AuthState {
  checked: boolean;
  authed: boolean;
  seedMode: boolean;
  roles: UserRole[];
  displayName: string;
  logout: () => Promise<void>;
}

const AdminAuthContext = createContext<AuthState>({
  checked: false,
  authed: false,
  seedMode: false,
  roles: [],
  displayName: "",
  logout: async () => {},
});

export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const [checked, setChecked] = useState(false);
  const [authed, setAuthed] = useState(false);
  const [seedMode, setSeedMode] = useState(false);
  const [roles, setRoles] = useState<UserRole[]>([]);
  const [displayName, setDisplayName] = useState("");
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    checkSession()
      .then((user) => {
        setAuthed(true);
        setSeedMode(Boolean(user.seedMode));
        setRoles(user.roles ?? []);
        setDisplayName(user.display_name ?? "");
        setChecked(true);
      })
      .catch(() => {
        setAuthed(false);
        setChecked(true);
        if (!pathname.startsWith("/admin/login")) {
          router.replace("/admin/login");
        }
      });
  }, [pathname, router]);

  async function logout() {
    await apiLogout();
    setAuthed(false);
    setRoles([]);
    router.replace("/admin/login");
  }

  return (
    <AdminAuthContext.Provider value={{ checked, authed, seedMode, roles, displayName, logout }}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  return useContext(AdminAuthContext);
}
