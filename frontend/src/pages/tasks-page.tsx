import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { ArrowRightIcon } from "lucide-react"

import { getFailureSummary, listTasks } from "@/lib/api"
import { getTaskPollingInterval } from "@/hooks/use-polling"
import type { TaskListFilters } from "@/lib/types"
import { TaskFilters } from "@/components/tasks/task-filters"
import { TaskSummaryCards } from "@/components/tasks/task-summary-cards"
import { TasksTable } from "@/components/tasks/tasks-table"
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
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { formatDateTime } from "@/lib/utils-format"

const defaultFilters: TaskListFilters = {
  page: 1,
  page_size: 20,
  status: "",
  task_name: "",
  arxiv_id: "",
  created_by: "",
}

export function TasksPage() {
  const [filters, setFilters] = useState<TaskListFilters>(defaultFilters)

  const tasksQuery = useQuery({
    queryKey: ["tasks", filters],
    queryFn: () => listTasks(filters),
    refetchInterval: (query) =>
      getTaskPollingInterval(query.state.data?.items[0]?.status),
  })

  const failuresQuery = useQuery({
    queryKey: ["failure-summary"],
    queryFn: () => getFailureSummary(10),
    refetchInterval: 10_000,
  })

  return (
    <div className="flex flex-col gap-6">
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <div className="flex flex-col gap-6">
          <Card className="overflow-visible">
            <CardHeader>
              <CardTitle>Task workspace</CardTitle>
              <CardDescription>
                Manage running translation jobs, inspect task health, and jump into failures quickly.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-5">
              <TaskSummaryCards tasks={tasksQuery.data} failures={failuresQuery.data} />
              <Separator />
              <TaskFilters
                filters={filters}
                onChange={setFilters}
                onReset={() => setFilters(defaultFilters)}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-start justify-between gap-4">
              <div className="flex flex-col gap-1">
                <CardTitle>Recent tasks</CardTitle>
                <CardDescription>
                  Polling every 5 seconds while tasks are still active.
                </CardDescription>
              </div>
              <Button asChild>
                <Link to="/tasks/new">
                  Create task
                  <ArrowRightIcon data-icon="inline-end" />
                </Link>
              </Button>
            </CardHeader>
            <CardContent>
              {tasksQuery.isLoading ? (
                <div className="flex flex-col gap-3">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : tasksQuery.data && tasksQuery.data.items.length > 0 ? (
                <TasksTable tasks={tasksQuery.data.items} />
              ) : (
                <Empty>
                  <EmptyHeader>
                    <EmptyMedia variant="icon">
                      <ArrowRightIcon />
                    </EmptyMedia>
                    <EmptyTitle>No tasks matched these filters</EmptyTitle>
                    <EmptyDescription>
                      Create a new task or loosen the current filters.
                    </EmptyDescription>
                  </EmptyHeader>
                  <EmptyContent>
                    <Button asChild>
                      <Link to="/tasks/new">Create your first task</Link>
                    </Button>
                  </EmptyContent>
                </Empty>
              )}
            </CardContent>
          </Card>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Failure pulse</CardTitle>
            <CardDescription>
              Recent failed tasks and failed stage counts from the backend summary endpoint.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {failuresQuery.isLoading ? (
              <>
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-20 w-full" />
              </>
            ) : (
              <>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(failuresQuery.data?.failed_stage_counts ?? {}).map(
                    ([stage, count]) => (
                      <Badge key={stage} variant="outline">
                        {stage}: {count}
                      </Badge>
                    )
                  )}
                </div>
                <Separator />
                <div className="flex flex-col gap-3">
                  {failuresQuery.data?.recent_failed_tasks.length ? (
                    failuresQuery.data.recent_failed_tasks.map((task) => (
                      <Link
                        key={task.id}
                        to={`/tasks/${task.id}`}
                        className="rounded-xl border p-3 transition-colors hover:bg-muted/40"
                      >
                        <div className="flex items-center justify-between gap-3">
                          <p className="font-medium">{task.task_name}</p>
                          <Badge variant="destructive">{task.current_stage}</Badge>
                        </div>
                        <p className="mt-1 text-sm text-muted-foreground">
                          {task.error_message ?? "No error summary provided."}
                        </p>
                        <p className="mt-2 text-xs text-muted-foreground">
                          Updated {formatDateTime(task.updated_at)}
                        </p>
                      </Link>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No recent failed tasks.
                    </p>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </section>
    </div>
  )
}
