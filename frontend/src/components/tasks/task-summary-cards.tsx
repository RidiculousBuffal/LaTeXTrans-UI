import { ActivityIcon, ArchiveIcon, CheckCircle2Icon, OctagonAlertIcon } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { FailureSummary, PaginatedTasks } from "@/lib/types"

type TaskSummaryCardsProps = {
  tasks: PaginatedTasks | undefined
  failures: FailureSummary | undefined
}

export function TaskSummaryCards({ tasks, failures }: TaskSummaryCardsProps) {
  const total = tasks?.total ?? 0
  const active =
    tasks?.items.filter(
      (task) =>
        task.status !== "SUCCEEDED" &&
        task.status !== "FAILED" &&
        task.status !== "CANCELED"
    ).length ?? 0
  const succeeded =
    tasks?.items.filter((task) => task.status === "SUCCEEDED").length ?? 0
  const failed = failures?.total_failed ?? 0

  const items = [
    { label: "Visible tasks", value: total, icon: ArchiveIcon },
    { label: "Active now", value: active, icon: ActivityIcon },
    { label: "Succeeded", value: succeeded, icon: CheckCircle2Icon },
    { label: "Recent failed", value: failed, icon: OctagonAlertIcon },
  ]

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <Card key={item.label}>
          <CardHeader className="flex flex-row items-center justify-between gap-3">
            <CardTitle>{item.label}</CardTitle>
            <item.icon />
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold tracking-tight">{item.value}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
