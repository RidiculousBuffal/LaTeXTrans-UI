import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { ArchiveIcon } from "lucide-react"

import { listArchives } from "@/lib/api"
import type { TaskListFilters } from "@/lib/types"
import { TaskFilters } from "@/components/tasks/task-filters"
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
import { ListPagination } from "@/components/ui/list-pagination"
import { formatDateTime } from "@/lib/utils-format"
import { StatusBadge } from "@/components/tasks/status-badge"
import { useAuth } from "@/lib/auth-context"

const defaultFilters: TaskListFilters = {
  page: 1,
  page_size: 20,
  status: "",
  task_name: "",
  arxiv_id: "",
  scope: "mine",
  created_from: "",
  created_to: "",
}

export function ArchivesPage() {
  const [filters, setFilters] = useState<TaskListFilters>(defaultFilters)
  const { user } = useAuth()
  const currentPage = filters.page ?? defaultFilters.page ?? 1
  const currentPageSize = filters.page_size ?? defaultFilters.page_size ?? 20

  const archivesQuery = useQuery({
    queryKey: ["archives", filters],
    queryFn: () => listArchives(filters),
  })

  const scopeOptions = [
    { value: "mine", label: "My Tasks" },
    { value: "shared", label: "Shared with Me" },
    { value: "public", label: "Public" },
    ...(user?.role === "admin" ? [{ value: "all", label: "All (Admin)" }] : []),
  ]

  function handlePageChange(page: number) {
    setFilters((prev) => ({ ...prev, page }))
  }

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
          <div className="flex flex-wrap gap-2">
            {scopeOptions.map((opt) => (
              <Button
                key={opt.value}
                size="sm"
                variant={filters.scope === opt.value ? "default" : "outline"}
                onClick={() => setFilters((f) => ({ ...f, scope: opt.value as TaskListFilters["scope"], page: 1 }))}
              >
                {opt.label}
              </Button>
            ))}
          </div>
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
            Groups historical runs by arXiv ID so repeated translations are easier to reuse.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {archivesQuery.isLoading ? (
            <div className="flex flex-col gap-3">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : archivesQuery.data?.items.length ? (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Archive group</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Runs</TableHead>
                      <TableHead>Artifacts</TableHead>
                      <TableHead>Latest created</TableHead>
                      <TableHead className="text-right">Open</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {archivesQuery.data.items.map((group) => (
                      <TableRow key={group.group_key}>
                        <TableCell>
                          <div className="flex flex-col gap-1">
                            <p className="font-medium">
                              {group.arxiv_id ?? group.latest_task.task_name}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              Latest task: {group.latest_task.task_name}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {group.latest_task.source_archive_name ?? "Grouped archive history"}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col gap-2">
                            <StatusBadge status={group.latest_task.status} />
                          </div>
                        </TableCell>
                        <TableCell>{group.task_count}</TableCell>
                        <TableCell>{group.artifact_count}</TableCell>
                        <TableCell>{formatDateTime(group.latest_created_at)}</TableCell>
                        <TableCell className="text-right">
                          <Button asChild variant="outline">
                            <Link to={`/tasks/${group.latest_task.id}`}>Open latest</Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <ListPagination
                page={archivesQuery.data.page ?? currentPage}
                pageSize={archivesQuery.data.page_size ?? currentPageSize}
                total={archivesQuery.data.total}
                onPageChange={handlePageChange}
              />
            </>
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
