import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { ArrowRightIcon } from "lucide-react"

import { getFailureSummary, listTasks } from "@/lib/api"
import { getTaskListPollingInterval } from "@/hooks/use-polling"
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
import { ListPagination } from "@/components/ui/list-pagination"
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

export function TasksPage() {
  const [filters, setFilters] = useState<TaskListFilters>(defaultFilters)
  const { user } = useAuth()
  const currentPage = filters.page ?? defaultFilters.page ?? 1
  const currentPageSize = filters.page_size ?? defaultFilters.page_size ?? 20

  const tasksQuery = useQuery({
    queryKey: ["tasks", filters],
    queryFn: () => listTasks(filters),
    refetchInterval: (query) => getTaskListPollingInterval(query.state.data?.items),
  })

  const failuresQuery = useQuery({
    queryKey: ["failure-summary"],
    queryFn: () => getFailureSummary(10),
    refetchInterval: 10_000,
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
     <div className="flex flex-col gap-6">
          <Card className="overflow-visible">
            <CardHeader>
              <CardTitle>Task workspace</CardTitle>
              <CardDescription>
                Manage running translation jobs, inspect task health, and jump into failures quickly.
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
            <CardContent className="flex flex-col gap-4 max-h-[480px]">
              {tasksQuery.isLoading ? (
                <div className="flex flex-col gap-3">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : tasksQuery.data && tasksQuery.data.items.length > 0 ? (
                <>
                  <div className="overflow-x-auto">
                    <TasksTable tasks={tasksQuery.data.items} />
                  </div>
                  <ListPagination
                    page={tasksQuery.data.page ?? currentPage}
                    pageSize={tasksQuery.data.page_size ?? currentPageSize}
                    total={tasksQuery.data.total}
                    onPageChange={handlePageChange}
                  />
                </>
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
    </div>
  )
}
