import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { TaskStatus } from "@/lib/types"

const statusMeta: Record<
  TaskStatus,
  { label: string; className: string; variant: "outline" | "secondary" | "destructive" | "default" }
> = {
  PENDING: {
    label: "Pending",
    variant: "secondary",
    className: "border-transparent bg-muted text-foreground",
  },
  DOWNLOADING: {
    label: "Downloading",
    variant: "outline",
    className: "border-sky-200 bg-sky-50 text-sky-700",
  },
  PARSING: {
    label: "Parsing",
    variant: "outline",
    className: "border-amber-200 bg-amber-50 text-amber-700",
  },
  TRANSLATING: {
    label: "Translating",
    variant: "default",
    className: "bg-primary text-primary-foreground",
  },
  VALIDATING: {
    label: "Validating",
    variant: "outline",
    className: "border-violet-200 bg-violet-50 text-violet-700",
  },
  GENERATING: {
    label: "Generating",
    variant: "outline",
    className: "border-cyan-200 bg-cyan-50 text-cyan-700",
  },
  SUCCEEDED: {
    label: "Succeeded",
    variant: "outline",
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  FAILED: {
    label: "Failed",
    variant: "destructive",
    className: "border-destructive/20 bg-destructive/10 text-destructive",
  },
  CANCELED: {
    label: "Canceled",
    variant: "outline",
    className: "border-zinc-200 bg-zinc-100 text-zinc-700",
  },
}

export function StatusBadge({ status }: { status: TaskStatus }) {
  const meta = statusMeta[status]

  return (
    <Badge variant={meta.variant} className={cn("capitalize", meta.className)}>
      {meta.label}
    </Badge>
  )
}
