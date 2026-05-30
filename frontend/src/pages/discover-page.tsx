import {useState} from "react"
import {useMutation, useQuery} from "@tanstack/react-query"
import {Link} from "react-router-dom"
import {toast} from "sonner"
import {
    ArrowRightIcon,
    BookmarkPlusIcon,
    ExternalLinkIcon,
    FileTextIcon,
    Loader2Icon,
    OrbitIcon,
    SearchIcon,
    SparklesIcon,
} from "lucide-react"

import {
    addPaperToCollection,
    createTaskFromDiscoveryPaper,
    getDiscoveryDailyDigest,
    listDiscoveryCollections,
    listDiscoveryPapers,
} from "@/lib/api"
import {queryClient} from "@/lib/query-client"
import type {
    DiscoveryCollection,
    DiscoveryPaperListFilters,
    DiscoveryPaperSummary,
    TranslateDecision,
} from "@/lib/types"
import {
    formatCollectionTranslationMode,
    formatRelativeTime,
    formatTranslateDecision,
    getErrorMessage,
} from "@/lib/utils-format"
import {Badge} from "@/components/ui/badge"
import {Button} from "@/components/ui/button"
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from "@/components/ui/card"
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
    EmptyContent,
    EmptyDescription,
    EmptyHeader,
    EmptyMedia,
    EmptyTitle,
} from "@/components/ui/empty"
import {Field, FieldContent, FieldDescription, FieldGroup, FieldLabel} from "@/components/ui/field"
import {Input} from "@/components/ui/input"
import {ListPagination} from "@/components/ui/list-pagination"
import {Select, SelectContent, SelectItem, SelectTrigger, SelectValue} from "@/components/ui/select"
import {Skeleton} from "@/components/ui/skeleton"
import {Textarea} from "@/components/ui/textarea"
import {Alert, AlertDescription, AlertTitle} from "@/components/ui/alert"

const defaultFilters: DiscoveryPaperListFilters = {
    page: 1,
    page_size: 10,
    category: "",
    keyword: "",
    worth_read: "",
    translated: "",
    collection_id: "",
    source_run_date: "",
}

type AddToCollectionDialogProps = {
    open: boolean
    onOpenChange: (open: boolean) => void
    paper: DiscoveryPaperSummary | null
    collections: DiscoveryCollection[]
}

function WorthReadBadge({value}: { value: boolean | null }) {
    if (value === null) {
        return <Badge variant="outline">Review pending</Badge>
    }

    return value ? (
        <Badge className="bg-emerald-600 text-white hover:bg-emerald-600">Worth reading</Badge>
    ) : (
        <Badge variant="outline" className="border-zinc-300 text-zinc-600">
            Skim only
        </Badge>
    )
}

function TranslationBadge({hasTranslation, count}: { hasTranslation: boolean; count: number }) {
    if (!hasTranslation) {
        return (
            <Badge variant="outline" className="border-dashed">
                No translation yet
            </Badge>
        )
    }

    return (
        <Badge variant="secondary" className="gap-1">
            <SparklesIcon className="size-3"/>
            {count} translation{count === 1 ? "" : "s"}
        </Badge>
    )
}

function AddToCollectionDialog({
                                   open,
                                   onOpenChange,
                                   paper,
                                   collections,
                               }: AddToCollectionDialogProps) {
    const [collectionId, setCollectionId] = useState("")
    const [translateDecision, setTranslateDecision] = useState<TranslateDecision>("pending")
    const [note, setNote] = useState("")

    const addMutation = useMutation({
        mutationFn: () => {
            if (!paper || !collectionId) {
                throw new Error("Please select a collection first.")
            }

            return addPaperToCollection(Number(collectionId), {
                paper_id: paper.id,
                note: note.trim() || undefined,
                translate_decision: translateDecision,
            })
        },
        onSuccess: async () => {
            toast.success("Paper added to collection")
            setCollectionId("")
            setTranslateDecision("pending")
            setNote("")
            onOpenChange(false)
            await Promise.all([
                queryClient.invalidateQueries({queryKey: ["discovery-papers"]}),
                queryClient.invalidateQueries({queryKey: ["discovery-paper", paper?.id]}),
                queryClient.invalidateQueries({queryKey: ["discovery-collections"]}),
                queryClient.invalidateQueries({queryKey: ["discovery-daily-digest"]}),
            ])
        },
        onError: (error) => {
            toast.error("Failed to add paper", {description: getErrorMessage(error)})
        },
    })

    const availableCollections = collections.filter(
        (collection) => !paper?.collections.some((item) => item.collection_id === collection.id)
    )

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <DialogTitle>Add to collection</DialogTitle>
                    <DialogDescription>
                        Save this paper into one of your collections first, then decide whether you want
                        manual or automatic follow-up later.
                    </DialogDescription>
                </DialogHeader>
                {paper ? (
                    <div className="flex flex-col gap-4">
                        <div className="rounded-xl border bg-muted/30 p-4">
                            <p className="font-medium">{paper.title_en}</p>
                            {paper.title_zh ? (
                                <p className="mt-1 text-sm text-muted-foreground">{paper.title_zh}</p>
                            ) : null}
                            <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-foreground">
                                <span>{paper.arxiv_id}</span>
                                {paper.primary_category ? <span>{paper.primary_category}</span> : null}
                            </div>
                        </div>
                        {availableCollections.length === 0 ? (
                            <Alert>
                                <BookmarkPlusIcon className="size-4"/>
                                <AlertTitle>Already added everywhere</AlertTitle>
                                <AlertDescription>
                                    This paper is already present in all of your collections.
                                </AlertDescription>
                            </Alert>
                        ) : (
                            <FieldGroup>
                                <Field>
                                    <FieldLabel htmlFor="add-paper-collection">Collection</FieldLabel>
                                    <FieldContent>
                                        <Select value={collectionId} onValueChange={setCollectionId}>
                                            <SelectTrigger id="add-paper-collection" className="w-full">
                                                <SelectValue placeholder="Choose a collection"/>
                                            </SelectTrigger>
                                            <SelectContent>
                                                {availableCollections.map((collection) => (
                                                    <SelectItem key={collection.id} value={String(collection.id)}>
                                                        {collection.name}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <FieldDescription>
                                            Existing collection policies stay on the collection itself.
                                        </FieldDescription>
                                    </FieldContent>
                                </Field>
                                <Field>
                                    <FieldLabel htmlFor="add-paper-decision">Translate decision</FieldLabel>
                                    <FieldContent>
                                        <Select value={translateDecision}
                                                onValueChange={(value) => setTranslateDecision(value as TranslateDecision)}>
                                            <SelectTrigger id="add-paper-decision" className="w-full">
                                                <SelectValue/>
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
                                <Field>
                                    <FieldLabel htmlFor="add-paper-note">Note</FieldLabel>
                                    <FieldContent>
                                        <Textarea
                                            id="add-paper-note"
                                            value={note}
                                            onChange={(event) => setNote(event.target.value)}
                                            placeholder="Optional context for why this paper matters"
                                        />
                                    </FieldContent>
                                </Field>
                            </FieldGroup>
                        )}
                    </div>
                ) : null}
                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        Cancel
                    </Button>
                    <Button
                        onClick={() => addMutation.mutate()}
                        disabled={!paper || !collectionId || addMutation.isPending || availableCollections.length === 0}
                    >
                        {addMutation.isPending ? (
                            <Loader2Icon className="animate-spin" data-icon="inline-start"/>
                        ) : (
                            <BookmarkPlusIcon data-icon="inline-start"/>
                        )}
                        Add paper
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}

function PaperCard({
                       paper,
                       collections,
                       onAdd,
                   }: {
    paper: DiscoveryPaperSummary
    collections: DiscoveryCollection[]
    onAdd: (paper: DiscoveryPaperSummary) => void
}) {
    const createTaskMutation = useMutation({
        mutationFn: () => createTaskFromDiscoveryPaper(paper.id, {}),
        onSuccess: async (response) => {
            toast.success("Translation task created", {
                description: `Task ${response.task.task_name} is now in the queue.`,
            })
            await Promise.all([
                queryClient.invalidateQueries({queryKey: ["discovery-papers"]}),
                queryClient.invalidateQueries({queryKey: ["discovery-paper", paper.id]}),
                queryClient.invalidateQueries({queryKey: ["tasks"]}),
                queryClient.invalidateQueries({queryKey: ["archives"]}),
            ])
        },
        onError: (error) => {
            toast.error("Failed to create translation task", {
                description: getErrorMessage(error),
            })
        },
    })

    const hasAvailableCollection = collections.some(
        (collection) => !paper.collections.some((item) => item.collection_id === collection.id)
    )

    return (
        <Card className="border-border/80 bg-card/90 h-max w-full">
                <div className="px-5 flex flex-col items-start justify-between gap-3">
                    <div className={'w-full'}>
                        <div className="flex justify-between ">
                            <div className={"flex gap-2"}>
                                <WorthReadBadge value={paper.worth_read}/>
                                <TranslationBadge
                                    hasTranslation={paper.has_translation}
                                    count={paper.translation_task_count}
                                />
                                {paper.primary_category ?
                                    <Badge variant="outline">{paper.primary_category}</Badge> : null}
                            </div>
                            <div className={'flex gap-2'}>
                                <Badge variant={'secondary'}>{paper.arxiv_id}</Badge>
                                <Badge variant={'secondary'}>{paper.source_run_date || 'unknown'}</Badge>
                <div className="flex flex-wrap gap-2">
                    {paper.collections.length > 0 ? (
                        paper.collections.map((item) => (
                            <Badge key={item.item_id} variant="secondary" className="gap-1">
                                {item.collection_name}
                                <span className="text-[11px] opacity-70">
                  {formatTranslateDecision(item.translate_decision)}
                </span>
                            </Badge>
                        ))
                    ) : (
                        <Badge variant="outline" className="border-dashed">
                            Not saved to a collection yet
                        </Badge>
                    )}
                </div>

                            </div>

                        </div>
                        <div className="pt-2">
                            <CardTitle className="text-xl leading-tight">
                                {paper.title_en}
                            </CardTitle>
                            {paper.title_zh ? (
                                <CardDescription className="text-sm">{paper.title_zh}</CardDescription>
                            ) : null}

                        </div>
                    </div>

                </div>

           <div className={"px-5 flex flex-col gap-3"}>

               <div className="flex flex-wrap gap-2 text-sm text-muted-foreground ">
                    {paper.authors_json.slice(0, 5).map((author) => (
                        <span key={author} className="rounded-full bg-muted px-2 py-1">
              {author}
            </span>
                    ))}
                    {paper.authors_json.length > 5 ? (
                        <span className="rounded-full bg-muted px-2 py-1">
              +{paper.authors_json.length - 5} more
            </span>
                    ) : null}
                </div>
                <p className="text-sm leading-6 text-muted-foreground">
                    {paper.abstract_zh ?? paper.abstract_en}
                </p>
                {paper.comment ? (
                    <div className="rounded-xl border bg-accent/30 p-3 text-sm text-accent-foreground">
                        {paper.comment}
                    </div>
                ) : null}
                <div className="flex flex-wrap gap-2 pt-2">
                    <Button onClick={() => onAdd(paper)} disabled={!hasAvailableCollection}>
                        <BookmarkPlusIcon data-icon="inline-start"/>
                        Add to collection
                    </Button>
                    <Button asChild variant="outline">
                        <Link to={`/papers/${paper.id}`}>
                            <FileTextIcon data-icon="inline-start"/>
                            View detail
                        </Link>
                    </Button>
                    {paper.has_translation ? (
                        <Button asChild variant="outline">
                            <Link to={`/papers/${paper.id}#history`}>
                                <SparklesIcon data-icon="inline-start"/>
                                View history
                            </Link>
                        </Button>
                    ) : null}
                    <Button
                        variant="outline"
                        onClick={() => createTaskMutation.mutate()}
                        disabled={createTaskMutation.isPending}
                    >
                        {createTaskMutation.isPending ? (
                            <Loader2Icon className="animate-spin" data-icon="inline-start"/>
                        ) : (
                            <ArrowRightIcon data-icon="inline-start"/>
                        )}
                        Translate now
                    </Button>
                    {paper.abs_url ? (
                        <Button asChild variant="ghost">
                            <a href={paper.abs_url} target="_blank" rel="noreferrer">
                                <ExternalLinkIcon data-icon="inline-start"/>
                                arXiv
                            </a>
                        </Button>
                    ) : null}
                </div>
           </div>
        </Card>
    )
}

export function DiscoverPage() {
    const [filters, setFilters] = useState<DiscoveryPaperListFilters>(defaultFilters)
    const [selectedPaper, setSelectedPaper] = useState<DiscoveryPaperSummary | null>(null)
    const [dialogOpen, setDialogOpen] = useState(false)

    const papersQuery = useQuery({
        queryKey: ["discovery-papers", filters],
        queryFn: () => listDiscoveryPapers(filters),
    })

    const digestQuery = useQuery({
        queryKey: ["discovery-daily-digest"],
        queryFn: () => getDiscoveryDailyDigest(),
    })

    const collectionsQuery = useQuery({
        queryKey: ["discovery-collections"],
        queryFn: () => listDiscoveryCollections(),
    })

    const categoryOptions = Array.from(
        new Set(
            [
                ...(digestQuery.data?.groups.map((group) => group.category) ?? []),
                ...(papersQuery.data?.items.map((paper) => paper.primary_category).filter(Boolean) ?? []),
                ...(collectionsQuery.data?.items.flatMap((collection) => collection.categories_json) ?? []),
            ].filter((value): value is string => Boolean(value))
        )
    ).sort()

    const quickStats = {
        total: digestQuery.data?.groups.reduce((sum, group) => sum + group.papers.length, 0) ?? 0,
        worthRead:
            digestQuery.data?.groups.reduce(
                (sum, group) => sum + group.papers.filter((paper) => paper.worth_read).length,
                0
            ) ?? 0,
        translated:
            digestQuery.data?.groups.reduce(
                (sum, group) => sum + group.papers.filter((paper) => paper.has_translation).length,
                0
            ) ?? 0,
    }

    function handleOpenAddDialog(paper: DiscoveryPaperSummary) {
        setSelectedPaper(paper)
        setDialogOpen(true)
    }

    function handlePageChange(page: number) {
        setFilters((current) => ({...current, page}))
    }

    return (
        <div className="flex flex-col gap-6">
            <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
                <Card
                    className=" border-none bg-[linear-gradient(135deg,color-mix(in_oklab,var(--color-primary)_16%,white),color-mix(in_oklab,var(--color-accent)_48%,white))] shadow-sm">
                    <CardContent className="flex h-full flex-col justify-between gap-6 p-6">
                        <div className="space-y-3">
                            <Badge variant="secondary" className="w-fit bg-white/65 text-slate-700">
                                Discovery Hub
                            </Badge>
                            <div className="space-y-2">
                                <h2 className="font-heading text-3xl font-semibold tracking-tight text-slate-900">
                                    Find today&apos;s papers before they turn into task URLs.
                                </h2>
                                <p className="max-w-2xl text-sm leading-6 text-slate-700">
                                    Browse the latest synced arXiv papers, triage with AI review hints, and push
                                    the good ones into collections before you spend translation quota.
                                </p>
                            </div>
                        </div>
                        <div className="grid gap-3 sm:grid-cols-3">
                            <div className="rounded-2xl bg-white/70 p-4">
                                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Latest run</p>
                                <p className="mt-2 text-lg font-semibold text-slate-900">
                                    {digestQuery.data?.run?.source_run_date ?? "No sync yet"}
                                </p>
                                <p className="mt-1 text-xs text-slate-600">
                                    {digestQuery.data?.run
                                        ? formatRelativeTime(digestQuery.data.run.updated_at)
                                        : "Ask an admin to trigger sync"}
                                </p>
                            </div>
                            <div className="rounded-2xl bg-white/70 p-4">
                                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Papers</p>
                                <p className="mt-2 text-3xl font-semibold text-slate-900">{quickStats.total}</p>
                                <p className="mt-1 text-xs text-slate-600">Across today&apos;s visible digest</p>
                            </div>
                            <div className="rounded-2xl bg-white/70 p-4">
                                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                                    Worth reading
                                </p>
                                <p className="mt-2 text-3xl font-semibold text-slate-900">
                                    {quickStats.worthRead}
                                </p>
                                <p className="mt-1 text-xs text-slate-600">
                                    {quickStats.translated} already have translations
                                </p>
                            </div>
                        </div>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader>
                        <CardTitle>Quick collections entry</CardTitle>
                        <CardDescription>
                            Keep discovery upstream. Collections are still the primary decision point.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-4 ">
                        {collectionsQuery.isLoading ? (
                            <>
                                <Skeleton className="h-16 w-full"/>
                                <Skeleton className="h-16 w-full"/>
                            </>
                        ) : collectionsQuery.data?.items.length ? (
                            collectionsQuery.data.items.slice(0, 4).map((collection) => (
                                <div
                                    key={collection.id}
                                    className="rounded-xl border bg-muted/20 p-4 transition-colors hover:bg-muted/30"
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <p className="font-medium">{collection.name}</p>
                                            <p className="mt-1 text-sm text-muted-foreground">
                                                {collection.description || "No description yet"}
                                            </p>
                                        </div>
                                        <Badge variant="outline">{collection.item_count} papers</Badge>
                                    </div>
                                    <div className="mt-3 flex flex-wrap gap-2">
                                        <Badge variant="secondary">
                                            {formatCollectionTranslationMode(collection.translation_mode)}
                                        </Badge>
                                        {collection.categories_json.slice(0, 3).map((category) => (
                                            <Badge key={category} variant="outline">
                                                {category}
                                            </Badge>
                                        ))}
                                    </div>
                                </div>
                            ))
                        ) : (
                            <Empty className="min-h-0 border">
                                <EmptyHeader>
                                    <EmptyMedia variant="icon">
                                        <BookmarkPlusIcon/>
                                    </EmptyMedia>
                                    <EmptyTitle>No collections yet</EmptyTitle>
                                    <EmptyDescription>
                                        Create a collection first so discovery can feed a reading workflow.
                                    </EmptyDescription>
                                </EmptyHeader>
                                <EmptyContent>
                                    <Button asChild variant="outline">
                                        <Link to="/collections">Open collections</Link>
                                    </Button>
                                </EmptyContent>
                            </Empty>
                        )}
                    </CardContent>
                </Card>
            </section>

            <Card>
                <CardHeader>
                    <CardTitle>Filter papers</CardTitle>
                    <CardDescription>
                        Explore by category, AI signal, collection coverage, or whether a reusable
                        translation already exists.
                    </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                    <Field>
                        <FieldLabel htmlFor="discovery-category">Category</FieldLabel>
                        <FieldContent>
                            <Select
                                value={filters.category || "all"}
                                onValueChange={(value) =>
                                    setFilters((current) => ({
                                        ...current,
                                        category: value === "all" ? "" : value,
                                        page: 1,
                                    }))
                                }
                            >
                                <SelectTrigger id="discovery-category" className="w-full">
                                    <SelectValue/>
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All categories</SelectItem>
                                    {categoryOptions.map((category) => (
                                        <SelectItem key={category} value={category}>
                                            {category}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </FieldContent>
                    </Field>
                    <Field>
                        <FieldLabel htmlFor="discovery-keyword">Keyword</FieldLabel>
                        <FieldContent>
                            <div className="relative">
                                <SearchIcon
                                    className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"/>
                                <Input
                                    id="discovery-keyword"
                                    className="pl-9"
                                    placeholder="title, abstract, comment"
                                    value={filters.keyword || ""}
                                    onChange={(event) =>
                                        setFilters((current) => ({
                                            ...current,
                                            keyword: event.target.value,
                                            page: 1,
                                        }))
                                    }
                                />
                            </div>
                        </FieldContent>
                    </Field>
                    <Field>
                        <FieldLabel htmlFor="discovery-worth-read">Worth read</FieldLabel>
                        <FieldContent>
                            <Select
                                value={filters.worth_read === "" ? "all" : filters.worth_read ? "yes" : "no"}
                                onValueChange={(value) =>
                                    setFilters((current) => ({
                                        ...current,
                                        worth_read: value === "all" ? "" : value === "yes",
                                        page: 1,
                                    }))
                                }
                            >
                                <SelectTrigger id="discovery-worth-read" className="w-full">
                                    <SelectValue/>
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All reviews</SelectItem>
                                    <SelectItem value="yes">Worth reading</SelectItem>
                                    <SelectItem value="no">Not worth reading</SelectItem>
                                </SelectContent>
                            </Select>
                        </FieldContent>
                    </Field>
                    <Field>
                        <FieldLabel htmlFor="discovery-translated">Translated</FieldLabel>
                        <FieldContent>
                            <Select
                                value={filters.translated === "" ? "all" : filters.translated ? "yes" : "no"}
                                onValueChange={(value) =>
                                    setFilters((current) => ({
                                        ...current,
                                        translated: value === "all" ? "" : value === "yes",
                                        page: 1,
                                    }))
                                }
                            >
                                <SelectTrigger id="discovery-translated" className="w-full">
                                    <SelectValue/>
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All papers</SelectItem>
                                    <SelectItem value="yes">Has translation</SelectItem>
                                    <SelectItem value="no">Needs translation</SelectItem>
                                </SelectContent>
                            </Select>
                        </FieldContent>
                    </Field>
                    <Field>
                        <FieldLabel htmlFor="discovery-collection">Collection</FieldLabel>
                        <FieldContent>
                            <Select
                                value={
                                    filters.collection_id === "" || filters.collection_id === undefined
                                        ? "all"
                                        : String(filters.collection_id)
                                }
                                onValueChange={(value) =>
                                    setFilters((current) => ({
                                        ...current,
                                        collection_id: value === "all" ? "" : Number(value),
                                        page: 1,
                                    }))
                                }
                            >
                                <SelectTrigger id="discovery-collection" className="w-full">
                                    <SelectValue/>
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="all">All collections</SelectItem>
                                    {(collectionsQuery.data?.items ?? []).map((collection) => (
                                        <SelectItem key={collection.id} value={String(collection.id)}>
                                            {collection.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </FieldContent>
                    </Field>
                </CardContent>
            </Card>

            <section className="flex w-full">
                <Card className={'w-full'}>
                    <CardHeader>
                        <CardTitle>All papers</CardTitle>
                        <CardDescription>
                            {papersQuery.data
                                ? `${papersQuery.data.total} papers matched the current filters.`
                                : "Loading papers from the latest visible discovery data."}
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col p-2  overflow-y-auto">
                        {papersQuery.isLoading ? (
                            <>
                                <Skeleton className="h-56 w-full"/>
                                <Skeleton className="h-56 w-full"/>
                            </>
                        ) : papersQuery.data?.items.length ? (
                            <div className={'flex flex-col gap-3'}>
                                {papersQuery.data.items.map((paper) => (
                                    <PaperCard
                                        key={paper.id}
                                        paper={paper}
                                        collections={collectionsQuery.data?.items ?? []}
                                        onAdd={handleOpenAddDialog}
                                    />
                                ))}
                                <div className={'px-2'}>
                                    <ListPagination
                                        page={papersQuery.data.page}
                                        pageSize={papersQuery.data.page_size}
                                        total={papersQuery.data.total}
                                        onPageChange={handlePageChange}
                                    />
                                </div>
                            </div>
                        ) : (
                            <Empty className="border">
                                <EmptyHeader>
                                    <EmptyMedia variant="icon">
                                        <OrbitIcon/>
                                    </EmptyMedia>
                                    <EmptyTitle>No discovery papers matched</EmptyTitle>
                                    <EmptyDescription>
                                        Try resetting the filters or wait for the next discovery sync.
                                    </EmptyDescription>
                                </EmptyHeader>
                            </Empty>
                        )}
                    </CardContent>
                </Card>
            </section>

            <AddToCollectionDialog
                open={dialogOpen}
                onOpenChange={setDialogOpen}
                paper={selectedPaper}
                collections={collectionsQuery.data?.items ?? []}
            />
        </div>
    )
}
