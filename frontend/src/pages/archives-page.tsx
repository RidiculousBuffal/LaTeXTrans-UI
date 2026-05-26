import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { ArchiveIcon } from "lucide-react"

import { listArchives } from "@/lib/api"
import type { TaskListFilters } from "@/lib/types"
import { TaskFilters } from "@/components/tasks/task-filters"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { formatDateTime } from "@/lib/utils-format"
import { StatusBadge } from "@/components/tasks/status-badge"

const defaultFilters: TaskListFilters = {
  page: 1,
  page_size: 20,
  status: "",
  task_name: "",
  arxiv_id: "",
  created_by: "",
}

export function ArchivesPage() {
  const [filters, setFilters] = useState<TaskListFilters>(defaultFilters)

  const archivesQuery = useQuery({
    queryKey: ["archives", filters],
    queryFn: () => listArchives(filters),
  })

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Archive explorer</CardTitle>
          <CardDescription>
            Search archived task outputs and jump back into the source task details.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <TaskFilters
            filters={filters}
            onChange={setFilters}
            onReset={() => setFilters(defaultFilters)}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Archived tasks</CardTitle>
          <CardDescription>
            Each row combines the task summary with its artifact count.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {archivesQuery.isLoading ? (
            <div className="flex flex-col gap-3">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : archivesQuery.data?.items.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Task</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Artifacts</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Open</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {archivesQuery.data.items.map((entry) => (
                  <TableRow key={entry.task.id}>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <p className="font-medium">{entry.task.task_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {entry.task.arxiv_id ?? entry.task.source_archive_name ?? "upload"}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-2">
                        <StatusBadge status={entry.task.status} />
                        <Badge variant="outline">{entry.task.current_stage}</Badge>
                      </div>
                    </TableCell>
                    <TableCell>{entry.artifact_count}</TableCell>
                    <TableCell>{formatDateTime(entry.task.created_at)}</TableCell>
                    <TableCell className="text-right">
                      <Button asChild variant="outline">
                        <Link to={`/tasks/${entry.task.id}`}>Open task</Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <Empty>
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <ArchiveIcon />
                </EmptyMedia>
                <EmptyTitle>No archived tasks found</EmptyTitle>
                <EmptyDescription>
                  Once tasks finish and artifacts are persisted, they will show up here.
                </EmptyDescription>
              </EmptyHeader>
              <EmptyContent>
                <Button asChild>
                  <Link to="/tasks/new">Create a task</Link>
                </Button>
              </EmptyContent>
            </Empty>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
