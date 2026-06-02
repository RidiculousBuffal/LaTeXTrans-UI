import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { ArrowRightIcon, SearchIcon, ShieldCheckIcon } from "lucide-react"

import { listPublicTasks } from "@/lib/api"
import type { TaskListFilters } from "@/lib/types"
import { formatDateTime, formatPercent } from "@/lib/utils-format"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { Input } from "@/components/ui/input"
import { ListPagination } from "@/components/ui/list-pagination"
import { Skeleton } from "@/components/ui/skeleton"

const defaultFilters: TaskListFilters = { page: 1, page_size: 12, scope: "public" }

export function PublicTasksPage() {
  const [taskName, setTaskName] = useState("")
  const [filters, setFilters] = useState<TaskListFilters>(defaultFilters)

  const query = useQuery({
    queryKey: ["public-tasks", filters],
    queryFn: () => listPublicTasks(filters),
  })

  function handleSearch() {
    setFilters((prev) => ({ ...prev, task_name: taskName.trim(), page: 1, scope: "public" }))
  }

  function handlePageChange(page: number) {
    setFilters((prev) => ({ ...prev, page, scope: "public" }))
  }

  return (
    <div className="flex h-svh flex-col gap-4 overflow-hidden p-4">
      <Card className="shrink-0 border-none bg-[radial-gradient(circle_at_top_left,color-mix(in_oklab,var(--color-primary)_18%,white),transparent_42%),linear-gradient(135deg,color-mix(in_oklab,var(--color-primary)_16%,white),color-mix(in_oklab,var(--color-accent)_44%,white))] shadow-[0_18px_45px_-28px_color-mix(in_oklab,var(--color-primary)_28%,transparent)] dark:bg-[radial-gradient(circle_at_12%_18%,color-mix(in_oklab,var(--color-primary)_42%,transparent),transparent_38%),radial-gradient(circle_at_88%_14%,color-mix(in_oklab,var(--color-accent)_26%,transparent),transparent_34%),linear-gradient(135deg,oklch(0.24_0.03_248),oklch(0.18_0.035_238))] dark:shadow-[0_22px_60px_-34px_color-mix(in_oklab,var(--color-primary)_50%,transparent)]">
        <CardHeader>
          <Badge className="w-fit bg-primary/90 text-primary-foreground dark:bg-white/12 dark:text-white dark:ring-1 dark:ring-white/10">
            Public Tasks
          </Badge>
          <CardTitle className="text-3xl text-slate-950 dark:text-white">All public translation jobs</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <Input
            value={taskName}
            onChange={(e) => setTaskName(e.target.value)}
            placeholder="Search task name..."
            className="max-w-md border-white/60 bg-white/82 text-slate-900 placeholder:text-slate-500 dark:border-white/10 dark:bg-white/8 dark:text-white dark:placeholder:text-white/40"
          />
          <Button onClick={handleSearch}>
            <SearchIcon className="mr-2 size-4" />
            Search
          </Button>
          <Button
            variant="outline"
            className="border-white/55 bg-white/24 text-slate-900 hover:bg-white/36 dark:border-white/12 dark:bg-white/6 dark:text-white dark:hover:bg-white/12"
            asChild
          >
            <Link to="/gallery">Paper gallery</Link>
          </Button>
        </CardContent>
      </Card>

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 p-1">
        {query.isLoading ? (
          <Skeleton className="h-80 w-full" />
        ) : query.data?.items.length ? (
          <div className="grid gap-4">
            {query.data.items.map((task) => (
              <Card key={task.id}>
                <CardContent className="flex flex-col gap-3 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate font-medium">{task.task_name}</p>
                      <p className="truncate text-sm text-muted-foreground">{task.arxiv_id ?? task.source_archive_name ?? "manual upload"}</p>
                    </div>
                    <Badge variant="outline" className="gap-1"><ShieldCheckIcon className="size-3" />{task.visibility}</Badge>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
                    <span>{task.status}</span>
                    <span>{formatPercent(task.progress_percent)}</span>
                    <span>{task.created_by}</span>
                    <span>{formatDateTime(task.updated_at)}</span>
                  </div>
                  <div className="flex justify-end">
                    <Button asChild size="sm">
                      <Link to={`/public/tasks/${task.id}`}>Open detail <ArrowRightIcon className="ml-2 size-4" /></Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="flex min-h-full items-center justify-center">
            <Empty>
              <EmptyHeader>
                <EmptyMedia variant="icon"><ShieldCheckIcon /></EmptyMedia>
                <EmptyTitle>No public tasks yet</EmptyTitle>
                <EmptyDescription>Once a translation is marked public, it will appear here.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          </div>
        )}
      </div>

      <div className="shrink-0">
        {query.data ? (
          query.data.total > query.data.page_size ? (
            <ListPagination
              page={query.data.page}
              pageSize={query.data.page_size}
              total={query.data.total}
              onPageChange={handlePageChange}
            />
          ) : (
            <div className="flex min-h-16 items-center border-t px-1 text-sm text-muted-foreground">
              Showing {query.data.total} public task{query.data.total === 1 ? "" : "s"}.
            </div>
          )
        ) : (
          <div className="min-h-16 border-t" />
        )}
      </div>
    </div>
  )
}
