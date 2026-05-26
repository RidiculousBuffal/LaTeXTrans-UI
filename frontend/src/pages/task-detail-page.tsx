import { useMemo } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { Link, useParams } from "react-router-dom"
import { toast } from "sonner"
import {
  ArrowLeftIcon,
  DownloadIcon,
  Loader2Icon,
  RefreshCwIcon,
  SquareIcon,
} from "lucide-react"

import { cancelTask, getTask, listArtifacts, listLogs, retryTask } from "@/lib/api"
import { queryClient } from "@/lib/query-client"
import { getTaskDetailPollingInterval } from "@/hooks/use-polling"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ProgressTimeline } from "@/components/tasks/progress-timeline"
import { TaskProgressCard } from "@/components/tasks/task-progress-card"
import { StatusBadge } from "@/components/tasks/status-badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import { formatDateTime, formatFileSize, getErrorMessage } from "@/lib/utils-format"
import { terminalStatuses } from "@/lib/types"

export function TaskDetailPage() {
  const { taskId = "" } = useParams()

  const taskQuery = useQuery({
    queryKey: ["task", taskId],
    queryFn: () => getTask(taskId),
    enabled: Boolean(taskId),
    refetchInterval: (query) => getTaskDetailPollingInterval(query.state.data?.status),
  })

  const artifactsQuery = useQuery({
    queryKey: ["task-artifacts", taskId],
    queryFn: () => listArtifacts(taskId),
    enabled: Boolean(taskId),
  })

  const logsQuery = useQuery({
    queryKey: ["task-logs", taskId],
    queryFn: () => listLogs(taskId),
    enabled: Boolean(taskId),
  })

  const retryMutation = useMutation({
    mutationFn: () => retryTask(taskId),
    onSuccess: async (response) => {
      toast.success(response.message)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["task", taskId] }),
        queryClient.invalidateQueries({ queryKey: ["tasks"] }),
      ])
    },
    onError: (error) => {
      toast.error("Retry failed", { description: getErrorMessage(error) })
    },
  })

  const cancelMutation = useMutation({
    mutationFn: () => cancelTask(taskId),
    onSuccess: async (response) => {
      toast.success(response.message)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["task", taskId] }),
        queryClient.invalidateQueries({ queryKey: ["tasks"] }),
      ])
    },
    onError: (error) => {
      toast.error("Cancel failed", { description: getErrorMessage(error) })
    },
  })

  const task = taskQuery.data
  const canRetry = task ? task.status === "FAILED" || task.status === "CANCELED" : false
  const canCancel = task ? !terminalStatuses.includes(task.status) : false

  const groupedArtifacts = useMemo(() => {
    const artifacts = artifactsQuery.data?.items ?? []
    return artifacts.reduce<Record<string, typeof artifacts>>((accumulator, artifact) => {
      const key = artifact.artifact_type
      accumulator[key] ??= []
      accumulator[key].push(artifact)
      return accumulator
    }, {})
  }, [artifactsQuery.data?.items])

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button asChild variant="outline">
          <Link to="/">
            <ArrowLeftIcon data-icon="inline-start" />
            Back to tasks
          </Link>
        </Button>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={!canRetry || retryMutation.isPending}
            onClick={() => retryMutation.mutate()}
          >
            {retryMutation.isPending ? (
              <Loader2Icon className="animate-spin" data-icon="inline-start" />
            ) : (
              <RefreshCwIcon data-icon="inline-start" />
            )}
            Retry
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={!canCancel || cancelMutation.isPending}
            onClick={() => cancelMutation.mutate()}
          >
            {cancelMutation.isPending ? (
              <Loader2Icon className="animate-spin" data-icon="inline-start" />
            ) : (
              <SquareIcon data-icon="inline-start" />
            )}
            Cancel
          </Button>
        </div>
      </div>

      {taskQuery.isLoading || !task ? (
        <div className="grid gap-6">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-72 w-full" />
        </div>
      ) : (
        <>
          <TaskProgressCard task={task} />

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
            <div className="flex flex-col gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Task metadata</CardTitle>
                  <CardDescription>
                    Primary record returned by `GET /api/tasks/{'{task_id}'}`.
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 md:grid-cols-2">
                  <MetadataItem label="Task ID" value={task.id} />
                  <MetadataItem label="Created by" value={task.created_by} />
                  <MetadataItem label="Source type" value={task.source_type} />
                  <MetadataItem label="arXiv ID" value={task.arxiv_id ?? "—"} />
                  <MetadataItem label="Model" value={task.model_name} />
                  <MetadataItem label="Workspace" value={task.workspace_dir ?? "—"} />
                  <MetadataItem label="Output dir" value={task.output_dir ?? "—"} />
                  <MetadataItem label="Updated" value={formatDateTime(task.updated_at)} />
                  <MetadataItem label="Created" value={formatDateTime(task.created_at)} />
                  <MetadataItem label="Started" value={formatDateTime(task.started_at)} />
                  <MetadataItem label="Finished" value={formatDateTime(task.finished_at)} />
                  <div className="flex flex-col gap-2">
                    <p className="text-sm font-medium">Current status</p>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={task.status} />
                      <Badge variant="outline">{task.current_stage}</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Task history</CardTitle>
                  <CardDescription>
                    Event timeline and backend-emitted details.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ProgressTimeline events={task.events} />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Artifacts and logs</CardTitle>
                  <CardDescription>
                    Download links come from the backend pre-signed URLs.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Tabs defaultValue="artifacts">
                    <TabsList>
                      <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
                      <TabsTrigger value="logs">Logs</TabsTrigger>
                      <TabsTrigger value="config">Config snapshot</TabsTrigger>
                    </TabsList>
                    <TabsContent value="artifacts" className="pt-4">
                      {artifactsQuery.isLoading ? (
                        <Skeleton className="h-48 w-full" />
                      ) : (
                        <div className="flex flex-col gap-5">
                          {Object.entries(groupedArtifacts).map(([type, items]) => (
                            <div key={type} className="flex flex-col gap-2">
                              <div className="flex items-center gap-2">
                                <Badge variant="outline">{type}</Badge>
                                <span className="text-sm text-muted-foreground">
                                  {items.length} file(s)
                                </span>
                              </div>
                              <ArtifactTable
                                items={items}
                              />
                            </div>
                          ))}
                        </div>
                      )}
                    </TabsContent>
                    <TabsContent value="logs" className="pt-4">
                      {logsQuery.isLoading ? (
                        <Skeleton className="h-32 w-full" />
                      ) : (
                        <ArtifactTable items={logsQuery.data?.items ?? []} />
                      )}
                    </TabsContent>
                    <TabsContent value="config" className="pt-4">
                      <div className="flex flex-col gap-4">
                        {task.configs.length > 0 ? (
                          task.configs.map((config) => (
                            <div key={config.id} className="rounded-xl border bg-muted/30 p-4">
                              <div className="mb-2 flex items-center justify-between gap-3">
                                <p className="font-medium">{config.env_profile}</p>
                                <span className="text-xs text-muted-foreground">
                                  {formatDateTime(config.created_at)}
                                </span>
                              </div>
                              <pre className="overflow-x-auto text-xs text-muted-foreground">
                                {JSON.stringify(config.config_snapshot_json, null, 2)}
                              </pre>
                            </div>
                          ))
                        ) : (
                          <p className="text-sm text-muted-foreground">
                            No config snapshots were returned for this task.
                          </p>
                        )}
                      </div>
                    </TabsContent>
                  </Tabs>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Operator notes</CardTitle>
                <CardDescription>
                  Helpful context while reviewing a long-running or failed task.
                </CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-4 text-sm text-muted-foreground">
                <p>Detail page polling slows to 3 seconds and automatically stops once the task reaches a terminal status.</p>
                <p>Retry is only enabled for `FAILED` and `CANCELED` tasks, matching the backend contract.</p>
                <p>Cancel is disabled for terminal tasks. If the backend returns a `409`, the toast will surface that detail directly.</p>
                <p>Error summary:</p>
                <p className="rounded-lg bg-destructive/8 p-3 text-destructive">
                  {task.error_message ?? "No error summary provided."}
                </p>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}

function MetadataItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <p className="text-sm font-medium">{label}</p>
      <p className="text-sm text-muted-foreground">{value}</p>
    </div>
  )
}

function ArtifactTable({
  items,
}: {
  items: Array<{
    id: number
    file_name: string
    content_type: string
    file_size: number
    version: number
    created_at: string
    download_url: string
  }>
}) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">No files available.</p>
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>File</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Size</TableHead>
          <TableHead>Version</TableHead>
          <TableHead>Created</TableHead>
          <TableHead className="text-right">Download</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item) => (
          <TableRow key={item.id}>
            <TableCell>{item.file_name}</TableCell>
            <TableCell className="text-muted-foreground">{item.content_type}</TableCell>
            <TableCell>{formatFileSize(item.file_size)}</TableCell>
            <TableCell>{item.version}</TableCell>
            <TableCell>{formatDateTime(item.created_at)}</TableCell>
            <TableCell className="text-right">
              <a
                href={item.download_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
              >
                <DownloadIcon className="size-4" />
                Download
              </a>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
