import type { Status } from "@/lib/types";

export const STATUS_META: Record<Status, { icon: string; label: string }> = {
  waiting: { icon: "○", label: "WAITING" },
  running: { icon: "●", label: "RUNNING" },
  completed: { icon: "✓", label: "COMPLETED" },
  rejected: { icon: "✕", label: "REJECTED" },
  error: { icon: "!", label: "ERROR" },
};

export function StatusBadge({ status }: { status: Status }) {
  const { icon, label } = STATUS_META[status];
  return (
    <span className={`badge badge--${status}`}>
      <span className="badge__icon" aria-hidden>
        {icon}
      </span>
      {label}
    </span>
  );
}
