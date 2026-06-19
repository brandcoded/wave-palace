import { AppShell } from "@/presentation/components/AppShell";

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
