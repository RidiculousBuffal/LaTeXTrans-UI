import { CheckCircle2Icon, CircleIcon, Clock3Icon, XCircleIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import type { TaskEvent } from "@/lib/types"
import { formatDateTime } from "@/lib/utils-format"
import { StatusBadge } from "@/components/tasks/status-badge"

export function ProgressTimeline({ events }: { events: TaskEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-muted-foreground">No task events yet.</p>
  }

  return (
    <div className="flex flex-col gap-3">
      {events.map((event, index) => {
        const isLast = index === events.length - 1
        const Icon =
          event.status === "FAILED"
            ? XCircleIcon
            : event.status === "SUCCEEDED"
              ? CheckCircle2Icon
              : index === 0
                ? Clock3Icon
                : CircleIcon

        return (
          <div key={event.id} className="flex gap-3">
            <div className="flex w-5 flex-col items-center">
              <div className="mt-0.5 rounded-full border bg-background p-1">
                <Icon className="size-3.5" />
              </div>
              {!isLast && <div className="mt-1 min-h-8 w-px flex-1 bg-border" />}
            </div>
            <div className={cn("flex min-w-0 flex-1 flex-col gap-1 pb-2", isLast && "pb-0")}>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={event.status} />
                <span className="text-sm font-medium">{event.stage}</span>
                <span className="text-xs text-muted-foreground">
                  {formatDateTime(event.created_at)}
                </span>
              </div>
              <p className="text-sm text-foreground">{event.message}</p>
              {Object.keys(event.details_json ?? {}).length > 0 && (
                <pre className="overflow-x-auto rounded-lg bg-muted p-3 text-xs text-muted-foreground">
                  {JSON.stringify(event.details_json, null, 2)}
                </pre>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
