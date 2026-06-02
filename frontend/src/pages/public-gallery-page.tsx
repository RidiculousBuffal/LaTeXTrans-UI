import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { BookOpenIcon, SearchIcon, SparklesIcon } from "lucide-react"

import { listPublicDiscoveryPapers } from "@/lib/api"
import type { DiscoveryPaperListFilters, DiscoveryPaperSummary } from "@/lib/types"
import { formatRelativeTime } from "@/lib/utils-format"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { Input } from "@/components/ui/input"
import { ListPagination } from "@/components/ui/list-pagination"
import { Skeleton } from "@/components/ui/skeleton"

const defaultFilters: DiscoveryPaperListFilters = { page: 1, page_size: 12 }

function PaperTile({ paper }: { paper: DiscoveryPaperSummary }) {
  return (
    <Card className="h-full overflow-hidden">
      <CardHeader className="space-y-2">
        <div className="flex flex-wrap gap-2">
          {paper.primary_category ? <Badge variant="outline">{paper.primary_category}</Badge> : null}
          {paper.has_translation ? (
            <Badge variant="secondary" className="gap-1">
              <SparklesIcon className="size-3" />
              {paper.translation_task_count} translation{paper.translation_task_count === 1 ? "" : "s"}
            </Badge>
          ) : (
            <Badge variant="outline">No translation yet</Badge>
          )}
        </div>
        <CardTitle className="line-clamp-2 text-xl leading-tight">{paper.title_en}</CardTitle>
        <p className="line-clamp-4 text-sm text-muted-foreground">{paper.title_zh ?? paper.abstract_en}</p>
      </CardHeader>
      <CardContent className="mt-auto space-y-4">
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
          <span>{paper.arxiv_id}</span>
          <span>{formatRelativeTime(paper.scraped_at)}</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild size="sm">
            <Link to={`/gallery/papers/${paper.id}`}>Open detail</Link>
          </Button>
          {paper.abs_url ? (
            <Button asChild size="sm" variant="outline">
              <a href={paper.abs_url} target="_blank" rel="noreferrer">arXiv</a>
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}

export function PublicGalleryPage() {
  const [keyword, setKeyword] = useState("")
  const [filters, setFilters] = useState<DiscoveryPaperListFilters>(defaultFilters)

  const query = useQuery({
    queryKey: ["public-discovery-papers", filters],
    queryFn: () => listPublicDiscoveryPapers(filters),
  })

  function handleSearch() {
    setFilters((prev) => ({ ...prev, keyword: keyword.trim(), page: 1 }))
  }

  function handlePageChange(page: number) {
    setFilters((prev) => ({ ...prev, page }))
  }

  return (
    <div className="flex h-svh flex-col gap-4 overflow-hidden p-4">
      <Card className="shrink-0 border-none bg-[radial-gradient(circle_at_top_left,color-mix(in_oklab,var(--color-primary)_18%,white),transparent_42%),linear-gradient(135deg,color-mix(in_oklab,var(--color-primary)_16%,white),color-mix(in_oklab,var(--color-accent)_44%,white))] shadow-[0_18px_45px_-28px_color-mix(in_oklab,var(--color-primary)_28%,transparent)] dark:bg-[radial-gradient(circle_at_12%_18%,color-mix(in_oklab,var(--color-primary)_42%,transparent),transparent_38%),radial-gradient(circle_at_88%_14%,color-mix(in_oklab,var(--color-accent)_26%,transparent),transparent_34%),linear-gradient(135deg,oklch(0.24_0.03_248),oklch(0.18_0.035_238))] dark:shadow-[0_22px_60px_-34px_color-mix(in_oklab,var(--color-primary)_50%,transparent)]">
        <CardHeader>
          <Badge className="w-fit bg-primary/90 text-primary-foreground dark:bg-white/12 dark:text-white dark:ring-1 dark:ring-white/10">
            Public Gallery
          </Badge>
          <CardTitle className="text-3xl text-slate-950 dark:text-white">arXiv papers and enrichments</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-3">
          <Input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="Search papers..."
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
            <Link to="/public/tasks">Public tasks</Link>
          </Button>
        </CardContent>
      </Card>

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 p-1">
        {query.isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <Skeleton className="h-56 w-full" />
            <Skeleton className="h-56 w-full" />
            <Skeleton className="h-56 w-full" />
          </div>
        ) : query.data?.items.length ? (
          <div className="grid auto-rows-fr gap-4 md:grid-cols-2 xl:grid-cols-3 ">
            {query.data.items.map((paper) => <PaperTile key={paper.id} paper={paper} />)}
          </div>
        ) : (
          <div className="flex min-h-full items-center justify-center">
            <Empty>
              <EmptyHeader>
                <EmptyMedia variant="icon"><BookOpenIcon /></EmptyMedia>
                <EmptyTitle>No public papers yet</EmptyTitle>
                <EmptyDescription>Try a different keyword or come back after the next sync.</EmptyDescription>
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
              Showing {query.data.total} paper{query.data.total === 1 ? "" : "s"}.
            </div>
          )
        ) : (
          <div className="min-h-16 border-t" />
        )}
      </div>
    </div>
  )
}
