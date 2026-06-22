"use client";

import { useEffect, useState } from "react";
import { ShieldCheck, UserX, UserCheck, RefreshCw } from "lucide-react";
import { listUsers, updateUserRoles, updateUserActive } from "@/features/admin/lib/adminApi";
import { useAdminAuth } from "@/features/admin/lib/adminAuth";
import type { AdminUser, UserRole } from "@/features/admin/types/admin";

const ALL_ROLES: UserRole[] = ["admin", "music_director"];

const ROLE_LABEL: Record<UserRole, string> = {
  admin: "Admin",
  music_director: "Music Director",
};

function RoleBadge({ role }: { role: UserRole }) {
  const colors: Record<UserRole, string> = {
    admin: "bg-violet-500/20 text-violet-300 border border-violet-500/30",
    music_director: "bg-sky-500/20 text-sky-300 border border-sky-500/30",
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[role]}`}>
      {ROLE_LABEL[role]}
    </span>
  );
}

function RoleEditor({ user, onSave }: { user: AdminUser; onSave: (u: AdminUser) => void }) {
  const [roles, setRoles] = useState<UserRole[]>(user.roles);
  const [saving, setSaving] = useState(false);

  function toggle(role: UserRole) {
    setRoles((prev) =>
      prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role]
    );
  }

  async function save() {
    setSaving(true);
    try {
      const updated = await updateUserRoles(user.id, roles);
      onSave(updated);
    } finally {
      setSaving(false);
    }
  }

  const changed = JSON.stringify([...roles].sort()) !== JSON.stringify([...user.roles].sort());

  return (
    <div className="flex flex-wrap items-center gap-2">
      {ALL_ROLES.map((role) => (
        <button
          key={role}
          onClick={() => toggle(role)}
          className={`rounded-full border px-2 py-0.5 text-xs font-medium transition ${
            roles.includes(role)
              ? role === "admin"
                ? "bg-violet-500/20 text-violet-300 border-violet-500/40"
                : "bg-sky-500/20 text-sky-300 border-sky-500/40"
              : "bg-white/5 text-white/30 border-white/10 hover:border-white/20"
          }`}
        >
          {ROLE_LABEL[role]}
        </button>
      ))}
      {changed && (
        <button
          onClick={save}
          disabled={saving}
          className="rounded-full bg-white/10 px-2.5 py-0.5 text-xs font-medium text-white transition hover:bg-white/20 disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      )}
    </div>
  );
}

function UserRow({
  user,
  currentUserId,
  onUpdate,
}: {
  user: AdminUser;
  currentUserId: string;
  onUpdate: (u: AdminUser) => void;
}) {
  const [toggling, setToggling] = useState(false);
  const isMe = user.id === currentUserId;

  async function toggleActive() {
    setToggling(true);
    try {
      const updated = await updateUserActive(user.id, !user.is_active);
      onUpdate(updated);
    } finally {
      setToggling(false);
    }
  }

  return (
    <tr className={`border-b border-white/5 transition ${user.is_active ? "" : "opacity-40"}`}>
      <td className="py-3 pr-4">
        <div className="flex items-center gap-2.5">
          {user.avatar_url ? (
            <img src={user.avatar_url} alt="" className="h-7 w-7 rounded-full object-cover" />
          ) : (
            <div className="h-7 w-7 rounded-full bg-white/10 flex items-center justify-center text-white/30 text-xs">
              {user.display_name[0]?.toUpperCase()}
            </div>
          )}
          <div>
            <p className="text-sm font-medium text-white">
              {user.display_name}
              {isMe && <span className="ml-1.5 text-xs text-white/30">(you)</span>}
            </p>
            {user.email && <p className="text-xs text-white/40">{user.email}</p>}
          </div>
        </div>
      </td>
      <td className="py-3 pr-4">
        <div className="flex flex-wrap gap-1">
          {user.discord_user_id && (
            <span className="rounded-full bg-indigo-500/20 border border-indigo-500/30 px-2 py-0.5 text-xs text-indigo-300">
              Discord
            </span>
          )}
          {user.email && (
            <span className="rounded-full bg-white/10 border border-white/10 px-2 py-0.5 text-xs text-white/40">
              Email
            </span>
          )}
        </div>
      </td>
      <td className="py-3 pr-4">
        <RoleEditor user={user} onSave={onUpdate} />
      </td>
      <td className="py-3 text-xs text-white/30">
        {user.last_login_at ? new Date(user.last_login_at).toLocaleDateString() : "Never"}
      </td>
      <td className="py-3 pl-4 text-right">
        {!isMe && (
          <button
            onClick={toggleActive}
            disabled={toggling}
            title={user.is_active ? "Deactivate" : "Reactivate"}
            className="rounded-lg p-1.5 text-white/30 transition hover:bg-white/10 hover:text-white disabled:opacity-50"
          >
            {user.is_active ? <UserX className="h-4 w-4" /> : <UserCheck className="h-4 w-4" />}
          </button>
        )}
      </td>
    </tr>
  );
}

export default function AdminUsersPage() {
  const { roles } = useAdminAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Derive current user id from /api/auth/me — we have it in context via checkSession
  // but we don't store it in context. Instead we find the bootstrap admin by convention.
  const [currentUserId, setCurrentUserId] = useState("");

  useEffect(() => {
    if (!roles.includes("admin")) return;
    load();
  }, [roles]);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const data = await listUsers();
      setUsers(data);
    } catch {
      setError("Failed to load users.");
    } finally {
      setLoading(false);
    }
  }

  function handleUpdate(updated: AdminUser) {
    setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
  }

  if (!roles.includes("admin")) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <ShieldCheck className="h-10 w-10 text-white/20" />
        <p className="text-white/40 text-sm">Admin access required.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Users</h1>
          <p className="mt-0.5 text-sm text-white/40">
            Manage identities, roles, and access.
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg bg-white/10 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-white/20 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {error && (
        <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-white/30 text-sm">Loading…</p>
      ) : (
        <div className="glass rounded-2xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/10">
                <th className="pb-3 pt-4 px-5 text-left text-xs font-semibold uppercase tracking-wider text-white/30">User</th>
                <th className="pb-3 pt-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-white/30">Auth</th>
                <th className="pb-3 pt-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-white/30">Roles</th>
                <th className="pb-3 pt-4 pr-4 text-left text-xs font-semibold uppercase tracking-wider text-white/30">Last login</th>
                <th className="pb-3 pt-4 pl-4 pr-5 text-right text-xs font-semibold uppercase tracking-wider text-white/30">Actions</th>
              </tr>
            </thead>
            <tbody className="px-5">
              {users.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-sm text-white/30">
                    No users yet.
                  </td>
                </tr>
              )}
              {users.map((u) => (
                <UserRow
                  key={u.id}
                  user={u}
                  currentUserId={currentUserId}
                  onUpdate={handleUpdate}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
