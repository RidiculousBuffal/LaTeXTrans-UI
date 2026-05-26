import { Progress } from "@/components/ui/progress"
import { StatusBadge } from "@/components/tasks/status-badge"
import type { TaskSummary } from "@/lib/types"
import { formatDateTime, formatPercent } from "@/lib/utils-format"

export function TaskProgressCard({ task }: { task: TaskSummary }) {
  const currentStageLabel = task.current_stage.startsWith("TRANSLATING::")
    ? task.current_stage.replace("TRANSLATING::", "")
    : task.current_stage

  return (
    <div className="flex flex-col gap-4 rounded-xl border bg-background p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium">{task.task_name}</p>
          <p className="text-sm text-muted-foreground">
            Current stage: {currentStageLabel}
          </p>
        </div>
        <StatusBadge status={task.status} />
      </div>
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Progress</span>
          <span>{formatPercent(task.progress_percent)}</span>
        </div>
        <Progress value={task.progress_percent} className="h-2" />
      </div>
      <div className="grid gap-3 text-sm text-muted-foreground sm:grid-cols-3">
        <div>
          <p className="font-medium text-foreground">Created</p>
          <p>{formatDateTime(task.created_at)}</p>
        </div>
        <div>
          <p className="font-medium text-foreground">Started</p>
          <p>{formatDateTime(task.started_at)}</p>
        </div>
        <div>
          <p className="font-medium text-foreground">Finished</p>
          <p>{formatDateTime(task.finished_at)}</p>
        </div>
      </div>
    </div>
  )
}
