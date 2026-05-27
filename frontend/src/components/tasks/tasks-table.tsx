import { Link } from "react-router-dom"

import { StatusBadge } from "@/components/tasks/status-badge"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type { TaskSummary } from "@/lib/types"
import { formatDateTime, formatPercent } from "@/lib/utils-format"

export function TasksTable({ tasks }: { tasks: TaskSummary[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Task</TableHead>
          <TableHead>Source</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Progress</TableHead>
          <TableHead>Owner</TableHead>
          <TableHead>Updated</TableHead>
          <TableHead className="text-right">Open</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {tasks.map((task) => (
          <TableRow key={task.id}>
            <TableCell className="align-top">
              <div className="flex flex-col gap-1">
                <p className="font-medium">{task.task_name}</p>
                <p className="text-xs text-muted-foreground">{task.id}</p>
                {task.error_message && (
                  <p className="max-w-md truncate text-xs text-destructive">
                    {task.error_message}
                  </p>
                )}
              </div>
            </TableCell>
            <TableCell className="align-top">
              <div className="flex flex-col gap-1">
                <Badge variant="secondary">{task.engine}</Badge>
                <Badge variant="outline">{task.source_type}</Badge>
                <span className="text-xs text-muted-foreground">
                  {task.arxiv_id ?? task.source_archive_name ?? "manual upload"}
                </span>
              </div>
            </TableCell>
            <TableCell className="align-top">
              <div className="flex flex-col gap-2">
                <StatusBadge status={task.status} />
              </div>
            </TableCell>
            <TableCell className="align-top text-sm">{formatPercent(task.progress_percent)}</TableCell>
            <TableCell className="align-top text-sm">{task.created_by}</TableCell>
            <TableCell className="align-top text-sm text-muted-foreground">
              {formatDateTime(task.updated_at)}
            </TableCell>
            <TableCell className="text-right">
              <Link className="text-sm font-medium text-primary hover:underline" to={`/tasks/${task.id}`}>
                Details
              </Link>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
