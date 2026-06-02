import { useQuery } from "@tanstack/react-query"
import { Link, useParams } from "react-router-dom"
import { ArrowLeftIcon, ExternalLinkIcon, FileTextIcon, SparklesIcon } from "lucide-react"

import { getPublicDiscoveryPaper } from "@/lib/api"
import { formatDateTime, formatRelativeTime } from "@/lib/utils-format"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

export function PublicPaperDetailPage() {
  const { paperId = "" } = useParams()
  const numericPaperId = Number(paperId)
  const paperQuery = useQuery({
    queryKey: ["public-discovery-paper", numericPaperId],
    queryFn: () => getPublicDiscoveryPaper(numericPaperId),
    enabled: Number.isFinite(numericPaperId),
  })

  const paper = paperQuery.data

  return (
    <div className="flex flex-col gap-6 p-4">
      <Button asChild variant="outline" className="w-fit">
        <Link to="/gallery"><ArrowLeftIcon className="mr-2 size-4" />Back to gallery</Link>
      </Button>

      {paperQuery.isLoading || !paper ? (
        <Skeleton className="h-96 w-full" />
      ) : (
        <>
          <Card>
            <CardHeader>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">{paper.arxiv_id}</Badge>
                {paper.primary_category ? <Badge variant="secondary">{paper.primary_category}</Badge> : null}
                {paper.has_translation ? <Badge className="gap-1"><SparklesIcon className="size-3" />{paper.translation_task_count} translation(s)</Badge> : null}
              </div>
              <CardTitle className="text-3xl">{paper.title_en}</CardTitle>
              <p className="text-muted-foreground">{paper.title_zh ?? paper.abstract_en}</p>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
                <span>Scraped {formatRelativeTime(paper.scraped_at)}</span>
                <span>Updated {formatDateTime(paper.updated_at)}</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {paper.abs_url ? <Button asChild variant="outline"><a href={paper.abs_url} target="_blank" rel="noreferrer"><ExternalLinkIcon className="mr-2 size-4" />arXiv</a></Button> : null}
                {paper.pdf_url ? <Button asChild variant="outline"><a href={paper.pdf_url} target="_blank" rel="noreferrer"><FileTextIcon className="mr-2 size-4" />PDF</a></Button> : null}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Abstract</CardTitle></CardHeader>
            <CardContent className="grid gap-4">
              <div className="rounded-lg border bg-muted/20 p-4 text-sm leading-7">{paper.abstract_zh ?? "No Chinese enrichment yet."}</div>
              <div className="rounded-lg border p-4 text-sm leading-7 text-muted-foreground">{paper.abstract_en}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Public translation tasks</CardTitle></CardHeader>
            <CardContent>
              <div className="space-y-3">
                {paper.tasks.length ? (
                  paper.tasks.map((task) => (
                    <div key={task.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3">
                      <div>
                        <p className="font-medium">{task.task_name}</p>
                        <p className="text-sm text-muted-foreground">{task.status} · {formatDateTime(task.updated_at)}</p>
                      </div>
                      <Button asChild size="sm" variant="outline">
                        <Link to={`/public/tasks/${task.id}`}>Open</Link>
                      </Button>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">No public task history exposed yet.</p>
                )}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
