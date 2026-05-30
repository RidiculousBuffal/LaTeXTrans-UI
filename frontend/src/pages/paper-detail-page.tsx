import { useState } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { Link, useParams } from "react-router-dom"
import { toast } from "sonner"
import {
  ArrowLeftIcon,
  BookmarkPlusIcon,
  ExternalLinkIcon,
  FileTextIcon,
  GlobeIcon,
  Loader2Icon,
  SparklesIcon,
} from "lucide-react"

import {
  addPaperToCollection,
  createTaskFromDiscoveryPaper,
  getDiscoveryPaper,
  listDiscoveryCollections,
} from "@/lib/api"
import { queryClient } from "@/lib/query-client"
import type { TranslateDecision } from "@/lib/types"
import {
  formatDateTime,
  formatRelativeTime,
  formatTranslateDecision,
  getErrorMessage,
} from "@/lib/utils-format"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Field, FieldContent, FieldLabel } from "@/components/ui/field"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { StatusBadge } from "@/components/tasks/status-badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

export function PaperDetailPage() {
  const { paperId = "" } = useParams()
  const numericPaperId = Number(paperId)
  const [isAddOpen, setIsAddOpen] = useState(false)
  const [collectionId, setCollectionId] = useState("")
  const [translateDecision, setTranslateDecision] = useState<TranslateDecision>("pending")

  const paperQuery = useQuery({
    queryKey: ["discovery-paper", numericPaperId],
    queryFn: () => getDiscoveryPaper(numericPaperId),
    enabled: Number.isFinite(numericPaperId),
  })

  const collectionsQuery = useQuery({
    queryKey: ["discovery-collections"],
    queryFn: () => listDiscoveryCollections(),
  })

  const addMutation = useMutation({
    mutationFn: () => {
      if (!collectionId || !paperQuery.data) {
        throw new Error("Please choose a collection first.")
      }

      return addPaperToCollection(Number(collectionId), {
        paper_id: paperQuery.data.id,
        translate_decision: translateDecision,
      })
    },
    onSuccess: async () => {
      toast.success("Paper added to collection")
      setCollectionId("")
      setTranslateDecision("pending")
      setIsAddOpen(false)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["discovery-paper", numericPaperId] }),
        queryClient.invalidateQueries({ queryKey: ["discovery-papers"] }),
        queryClient.invalidateQueries({ queryKey: ["discovery-collections"] }),
      ])
    },
    onError: (error) => {
      toast.error("Failed to add paper", { description: getErrorMessage(error) })
    },
  })

  const createTaskMutation = useMutation({
    mutationFn: () =>
      createTaskFromDiscoveryPaper(
        numericPaperId,
        collectionId ? { collection_id: Number(collectionId) } : {}
      ),
    onSuccess: async (response) => {
      toast.success("Translation task created", {
        description: `Task ${response.task.task_name} is ready to open.`,
      })
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["discovery-paper", numericPaperId] }),
        queryClient.invalidateQueries({ queryKey: ["discovery-papers"] }),
        queryClient.invalidateQueries({ queryKey: ["tasks"] }),
        queryClient.invalidateQueries({ queryKey: ["archives"] }),
      ])
    },
    onError: (error) => {
      toast.error("Failed to create translation task", {
        description: getErrorMessage(error),
      })
    },
  })

  const paper = paperQuery.data
  const availableCollections =
    collectionsQuery.data?.items.filter(
      (collection) => !paper?.collections.some((item) => item.collection_id === collection.id)
    ) ?? []

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button asChild variant="outline">
          <Link to="/discover">
            <ArrowLeftIcon data-icon="inline-start" />
            Back to discover
          </Link>
        </Button>
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={() => setIsAddOpen(true)}
            disabled={!paper || availableCollections.length === 0}
          >
            <BookmarkPlusIcon data-icon="inline-start" />
            Add to collection
          </Button>
          <Button
            variant="outline"
            onClick={() => createTaskMutation.mutate()}
            disabled={!paper || createTaskMutation.isPending}
          >
            {createTaskMutation.isPending ? (
              <Loader2Icon className="animate-spin" data-icon="inline-start" />
            ) : (
              <SparklesIcon data-icon="inline-start" />
            )}
            Translate now
          </Button>
        </div>
      </div>

      {paperQuery.isLoading || !paper ? (
        <div className="grid gap-6">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-72 w-full" />
          <Skeleton className="h-72 w-full" />
        </div>
      ) : (
        <>
          <Card className="overflow-hidden border-none bg-[linear-gradient(145deg,color-mix(in_oklab,var(--color-primary)_14%,white),color-mix(in_oklab,var(--color-accent)_38%,white))]">
            <CardContent className="flex flex-col gap-6 p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    {paper.worth_read !== null ? (
                      <Badge className={paper.worth_read ? "bg-emerald-600 text-white" : ""}>
                        {paper.worth_read ? "Worth reading" : "Review completed"}
                      </Badge>
                    ) : (
                      <Badge variant="outline">Review pending</Badge>
                    )}
                    {paper.primary_category ? <Badge variant="outline">{paper.primary_category}</Badge> : null}
                    {paper.has_translation ? (
                      <Badge variant="secondary">
                        {paper.translation_task_count} translation
                        {paper.translation_task_count === 1 ? "" : "s"}
                      </Badge>
                    ) : null}
                  </div>
                  <div className="space-y-2">
                    <h1 className="font-heading text-3xl font-semibold tracking-tight text-slate-900">
                      {paper.title_en }
                    </h1>
                    {paper.title_zh ? (
                      <p className="max-w-4xl text-base text-slate-700">{paper.title_zh}</p>
                    ) : null}
                  </div>
                </div>
                <div className="space-y-2 rounded-2xl bg-white/70 p-4 text-sm">
                  <p className="font-medium text-slate-900">{paper.arxiv_id}</p>
                  <p className="text-slate-700">
                    Synced {paper.source_run_date ?? "unknown"} · {formatRelativeTime(paper.updated_at)}
                  </p>
                  <div className="flex flex-wrap gap-2 pt-2">
                    {paper.abs_url ? (
                      <Button asChild size="sm" variant="outline">
                        <a href={paper.abs_url} target="_blank" rel="noreferrer">
                          <GlobeIcon data-icon="inline-start" />
                          Abstract
                        </a>
                      </Button>
                    ) : null}
                    {paper.pdf_url ? (
                      <Button asChild size="sm" variant="outline">
                        <a href={paper.pdf_url} target="_blank" rel="noreferrer">
                          <FileTextIcon data-icon="inline-start" />
                          PDF
                        </a>
                      </Button>
                    ) : null}
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-2 text-sm text-slate-700">
                {paper.authors_json.map((author) => (
                  <span key={author} className="rounded-full bg-white/75 px-3 py-1">
                    {author}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="flex flex-col gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Abstract</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="rounded-xl border bg-muted/20 p-4 text-sm leading-7">
                    {paper.abstract_zh ?? "No Chinese summary available yet."}
                  </div>
                  <div className="rounded-xl border bg-background p-4 text-sm leading-7 text-muted-foreground">
                    {paper.abstract_en}
                  </div>
                  {paper.comment ? (
                    <Alert>
                      <SparklesIcon className="size-4" />
                      <AlertTitle>AI comment</AlertTitle>
                      <AlertDescription>{paper.comment}</AlertDescription>
                    </Alert>
                  ) : null}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Review history</CardTitle>
                  <CardDescription>
                    Reviews are scoped to collections — worth_read and comment come from here.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {paper.reviews.length ? (
                    paper.reviews.map((review) => (
                      <div key={review.id} className="rounded-xl border p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="font-medium">{review.collection_name}</p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {review.model_name} · {formatDateTime(review.updated_at)}
                            </p>
                          </div>
                          <Badge variant={review.worth_read ? "default" : "outline"}>
                            {review.worth_read ? "Worth reading" : "Not worth reading"}
                          </Badge>
                        </div>
                        {review.comment ? (
                          <p className="mt-3 rounded-lg bg-muted/30 p-3 text-sm">{review.comment}</p>
                        ) : null}
                      </div>
                    ))
                  ) : (
                    <Empty className="min-h-0 border">
                      <EmptyHeader>
                        <EmptyMedia variant="icon">
                          <SparklesIcon />
                        </EmptyMedia>
                        <EmptyTitle>No reviews yet</EmptyTitle>
                        <EmptyDescription>
                          This paper has been ingested, but no collection-scoped review is visible yet.
                        </EmptyDescription>
                      </EmptyHeader>
                    </Empty>
                  )}
                </CardContent>
              </Card>
            </div>

            <div className="flex flex-col gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Collections</CardTitle>
                  <CardDescription>Where this paper already sits in your workflow.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {paper.collections.length ? (
                    paper.collections.map((collection) => (
                      <div key={collection.item_id} className="rounded-xl border bg-muted/20 p-4">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <p className="font-medium">{collection.collection_name}</p>
                          <Badge variant="outline">
                            {formatTranslateDecision(collection.translate_decision)}
                          </Badge>
                        </div>
                        {collection.note ? (
                          <p className="mt-2 text-sm text-muted-foreground">{collection.note}</p>
                        ) : null}
                      </div>
                    ))
                  ) : (
                    <Empty className="min-h-0 border">
                      <EmptyHeader>
                        <EmptyMedia variant="icon">
                          <BookmarkPlusIcon />
                        </EmptyMedia>
                        <EmptyTitle>Not in a collection yet</EmptyTitle>
                        <EmptyDescription>
                          Add it to a collection first if you want discovery to remain the upstream control point.
                        </EmptyDescription>
                      </EmptyHeader>
                    </Empty>
                  )}
                </CardContent>
              </Card>

              <Card id="history">
                <CardHeader>
                  <CardTitle>Translation history</CardTitle>
                  <CardDescription>
                    Existing tasks are surfaced here so you can reuse prior work instead of translating twice.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {paper.latest_task ? (
                    <div className="rounded-xl border bg-accent/25 p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-medium">Latest task</p>
                          <p className="mt-1 text-sm text-muted-foreground">
                            {paper.latest_task.task_name}
                          </p>
                        </div>
                        <StatusBadge status={paper.latest_task.status} />
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <Button asChild size="sm">
                          <Link to={`/tasks/${paper.latest_task.id}`}>
                            <SparklesIcon data-icon="inline-start" />
                            Open latest task
                          </Link>
                        </Button>
                      </div>
                    </div>
                  ) : null}
                  {paper.tasks.length ? (
                    paper.tasks.map((task) => (
                      <div key={task.id} className="rounded-xl border p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="font-medium">{task.task_name}</p>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {task.id} · updated {formatRelativeTime(task.updated_at)}
                            </p>
                          </div>
                          <StatusBadge status={task.status} />
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <Badge variant="outline">{task.engine}</Badge>
                          <Badge variant="outline">{task.source_type}</Badge>
                          <Button asChild size="sm" variant="outline">
                            <Link to={`/tasks/${task.id}`}>
                              <ExternalLinkIcon data-icon="inline-start" />
                              Open task
                            </Link>
                          </Button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <Empty className="min-h-0 border">
                      <EmptyHeader>
                        <EmptyMedia variant="icon">
                          <FileTextIcon />
                        </EmptyMedia>
                        <EmptyTitle>No translation tasks yet</EmptyTitle>
                        <EmptyDescription>
                          This paper has not been turned into a translation task in your visible scope.
                        </EmptyDescription>
                      </EmptyHeader>
                    </Empty>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Pipeline snapshot</CardTitle>
                  <CardDescription>Current product flow for one paper.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {[
                    { step: "crawl", detail: `Paper scraped at ${formatDateTime(paper.scraped_at)}` },
                    {
                      step: "enrich",
                      detail: paper.enrichment
                        ? `Global enrichment ready · ${paper.enrichment.model_name}`
                        : "No global enrichment yet",
                    },
                    {
                      step: "judge",
                      detail: paper.reviews.length
                        ? `${paper.reviews.length} collection-scoped review(s) visible`
                        : "No visible review yet",
                    },
                    {
                      step: "collect",
                      detail: paper.collections.length
                        ? `Saved in ${paper.collections.length} collection(s)`
                        : "Not collected yet",
                    },
                    {
                      step: "translate",
                      detail: paper.tasks.length
                        ? `${paper.tasks.length} linked task(s) available`
                        : "No translation task created yet",
                    },
                  ].map((item, index) => (
                    <div key={item.step} className="flex gap-4 rounded-xl border p-4">
                      <div className="flex size-8 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
                        {index + 1}
                      </div>
                      <div className="space-y-1">
                        <p className="font-medium uppercase tracking-[0.12em] text-muted-foreground">
                          {item.step}
                        </p>
                        <p className="text-sm">{item.detail}</p>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </div>
        </>
      )}

      <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add paper to collection</DialogTitle>
            <DialogDescription>
              Choose where this paper belongs before you move it deeper into translation work.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Field>
              <FieldLabel htmlFor="paper-detail-collection">Collection</FieldLabel>
              <FieldContent>
                <Select value={collectionId} onValueChange={setCollectionId}>
                  <SelectTrigger id="paper-detail-collection" className="w-full">
                    <SelectValue placeholder="Choose a collection" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableCollections.map((collection) => (
                      <SelectItem key={collection.id} value={String(collection.id)}>
                        {collection.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FieldContent>
            </Field>
            <Field>
              <FieldLabel htmlFor="paper-detail-decision">Decision</FieldLabel>
              <FieldContent>
                <Select
                  value={translateDecision}
                  onValueChange={(value) => setTranslateDecision(value as TranslateDecision)}
                >
                  <SelectTrigger id="paper-detail-decision" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="manual_requested">Manual requested</SelectItem>
                    <SelectItem value="auto_queued">Auto queued</SelectItem>
                    <SelectItem value="translated">Translated</SelectItem>
                  </SelectContent>
                </Select>
              </FieldContent>
            </Field>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => addMutation.mutate()}
              disabled={!collectionId || addMutation.isPending || availableCollections.length === 0}
            >
              {addMutation.isPending ? (
                <Loader2Icon className="animate-spin" data-icon="inline-start" />
              ) : (
                <BookmarkPlusIcon data-icon="inline-start" />
              )}
              Add paper
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
