import { cn } from "@/shared/lib/cn";

export function GlassPanel({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={cn("glass rounded-3xl", className)}>{children}</div>
  );
}
