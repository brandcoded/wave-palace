"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { checkSession, logout as apiLogout } from "./adminApi";

interface AuthState {
  checked: boolean;
  authed: boolean;
  logout: () => Promise<void>;
}

const AdminAuthContext = createContext<AuthState>({
  checked: false,
  authed: false,
  logout: async () => {},
});

export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const [checked, setChecked] = useState(false);
  const [authed, setAuthed] = useState(false);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    checkSession()
      .then(() => {
        setAuthed(true);
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
    router.replace("/admin/login");
  }

  return (
    <AdminAuthContext.Provider value={{ checked, authed, logout }}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  return useContext(AdminAuthContext);
}
