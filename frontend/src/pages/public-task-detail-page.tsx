import { useQuery } from "@tanstack/react-query"
import { Link, useParams } from "react-router-dom"
import { ArrowLeftIcon, DownloadIcon } from "lucide-react"

import { getPublicTask, listPublicArtifacts } from "@/lib/api"
import { formatDateTime, formatFileSize } from "@/lib/utils-format"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { StatusBadge } from "@/components/tasks/status-badge"
import { ProgressTimeline } from "@/components/tasks/progress-timeline"

export function PublicTaskDetailPage() {
  const { taskId = "" } = useParams()
  const taskQuery = useQuery({
    queryKey: ["public-task", taskId],
    queryFn: () => getPublicTask(taskId),
    enabled: Boolean(taskId),
  })
  const artifactsQuery = useQuery({
    queryKey: ["public-task-artifacts", taskId],
    queryFn: () => listPublicArtifacts(taskId),
    enabled: Boolean(taskId),
  })
  const task = taskQuery.data

  return (
    <div className="flex flex-col gap-6 p-4">
      <Button asChild variant="outline" className="w-fit">
        <Link to="/public/tasks"><ArrowLeftIcon className="mr-2 size-4" />Back to public tasks</Link>
      </Button>
      {taskQuery.isLoading || !task ? (
        <Skeleton className="h-96 w-full" />
      ) : (
        <>
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={task.status} />
                <span className="text-sm text-muted-foreground">{task.visibility}</span>
              </div>
              <CardTitle>{task.task_name}</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 text-sm text-muted-foreground md:grid-cols-2">
              <div><p className="font-medium text-foreground">Created</p><p>{formatDateTime(task.created_at)}</p></div>
              <div><p className="font-medium text-foreground">Progress</p><p>{task.progress_percent}%</p></div>
              <div><p className="font-medium text-foreground">Source</p><p>{task.arxiv_id ?? task.source_archive_name ?? "manual upload"}</p></div>
              <div><p className="font-medium text-foreground">Owner</p><p>{task.created_by}</p></div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Timeline</CardTitle></CardHeader>
            <CardContent className={'max-h-[480px] overflow-y-auto'}><ProgressTimeline events={task.events} /></CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Artifacts</CardTitle></CardHeader>
            <CardContent className="grid gap-3">
              {(artifactsQuery.data?.items ?? []).map((artifact) => (
                <div key={artifact.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3">
                  <div>
                    <p className="font-medium">{artifact.file_name}</p>
                    <p className="text-sm text-muted-foreground">{artifact.content_type} · {formatFileSize(artifact.file_size)}</p>
                  </div>
                  <Button asChild size="sm" variant="outline">
                    <a href={artifact.download_url} target="_blank" rel="noreferrer"><DownloadIcon className="mr-2 size-4" />Download</a>
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
