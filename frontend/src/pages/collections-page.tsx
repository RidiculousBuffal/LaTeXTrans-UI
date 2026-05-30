import { useMemo, useState } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { toast } from "sonner"
import {
  BookmarkIcon,
  FileTextIcon,
  FolderPlusIcon,
  Loader2Icon,
  PencilIcon,
  Trash2Icon,
} from "lucide-react"

import {
  createDiscoveryCollection,
  deleteDiscoveryCollection,
  listDiscoveryCollections,
  removePaperFromCollection,
  updateDiscoveryCollection,
} from "@/lib/api"
import { queryClient } from "@/lib/query-client"
import type {
  CollectionTranslationMode,
  DiscoveryCollection,
  DiscoveryCollectionCreatePayload,
  DiscoveryCollectionUpdatePayload,
} from "@/lib/types"
import {
  formatCollectionTranslationMode,
  formatDateTime,
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
import { Field, FieldContent, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"

function normalizeCategories(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
}

function CollectionFormDialog({
  open,
  onOpenChange,
  mode,
  collection,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  mode: "create" | "edit"
  collection?: DiscoveryCollection | null
}) {
  const [name, setName] = useState(collection?.name ?? "")
  const [description, setDescription] = useState(collection?.description ?? "")
  const [categories, setCategories] = useState(collection?.categories_json.join(", ") ?? "")
  const [preferKeywords, setPreferKeywords] = useState(collection?.prefer_keywords ?? "")
  const [avoidKeywords, setAvoidKeywords] = useState(collection?.avoid_keywords ?? "")
  const [translationMode, setTranslationMode] = useState<CollectionTranslationMode>(
    collection?.translation_mode ?? "manual"
  )
  const [autoTranslateEnabled, setAutoTranslateEnabled] = useState(
    collection?.auto_translate_enabled ?? false
  )

  const mutation = useMutation({
    mutationFn: async () => {
      const payload: DiscoveryCollectionCreatePayload | DiscoveryCollectionUpdatePayload = {
        name: name.trim(),
        description: description.trim() || undefined,
        categories_json: normalizeCategories(categories),
        prefer_keywords: preferKeywords.trim() || undefined,
        avoid_keywords: avoidKeywords.trim() || undefined,
        translation_mode: translationMode,
        auto_translate_enabled: autoTranslateEnabled,
      }

      if (mode === "create") {
        return createDiscoveryCollection(payload as DiscoveryCollectionCreatePayload)
      }

      if (!collection) {
        throw new Error("Missing collection to edit.")
      }

      return updateDiscoveryCollection(collection.id, payload)
    },
    onSuccess: async () => {
      toast.success(mode === "create" ? "Collection created" : "Collection updated")
      onOpenChange(false)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["discovery-collections"] }),
        queryClient.invalidateQueries({ queryKey: ["discovery-papers"] }),
      ])
    },
    onError: (error) => {
      toast.error(mode === "create" ? "Failed to create collection" : "Failed to update collection", {
        description: getErrorMessage(error),
      })
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "Create collection" : "Edit collection"}</DialogTitle>
          <DialogDescription>
            Configure the discovery preferences and the default translation posture for this
            reading list.
          </DialogDescription>
        </DialogHeader>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="collection-name">Name</FieldLabel>
            <FieldContent>
              <Input
                id="collection-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Vision backlog"
              />
            </FieldContent>
          </Field>
          <Field>
            <FieldLabel htmlFor="collection-description">Description</FieldLabel>
            <FieldContent>
              <Textarea
                id="collection-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="What belongs in this collection?"
              />
            </FieldContent>
          </Field>
          <Field>
            <FieldLabel htmlFor="collection-categories">Categories</FieldLabel>
            <FieldContent>
              <Input
                id="collection-categories"
                value={categories}
                onChange={(event) => setCategories(event.target.value)}
                placeholder="cs.AI, cs.CV"
              />
            </FieldContent>
          </Field>
          <div className="grid gap-4 md:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="collection-prefer">Prefer keywords</FieldLabel>
              <FieldContent>
                <Input
                  id="collection-prefer"
                  value={preferKeywords}
                  onChange={(event) => setPreferKeywords(event.target.value)}
                  placeholder="agents, evaluation"
                />
              </FieldContent>
            </Field>
            <Field>
              <FieldLabel htmlFor="collection-avoid">Avoid keywords</FieldLabel>
              <FieldContent>
                <Input
                  id="collection-avoid"
                  value={avoidKeywords}
                  onChange={(event) => setAvoidKeywords(event.target.value)}
                  placeholder="survey, hardware"
                />
              </FieldContent>
            </Field>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="collection-mode">Translation mode</FieldLabel>
              <FieldContent>
                <Select
                  value={translationMode}
                  onValueChange={(value) => setTranslationMode(value as CollectionTranslationMode)}
                >
                  <SelectTrigger id="collection-mode" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manual">Manual</SelectItem>
                    <SelectItem value="auto">Auto</SelectItem>
                  </SelectContent>
                </Select>
              </FieldContent>
            </Field>
            <Field>
              <FieldLabel htmlFor="collection-auto-translate">Auto translate flag</FieldLabel>
              <FieldContent>
                <Select
                  value={autoTranslateEnabled ? "enabled" : "disabled"}
                  onValueChange={(value) => setAutoTranslateEnabled(value === "enabled")}
                >
                  <SelectTrigger id="collection-auto-translate" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="disabled">Disabled</SelectItem>
                    <SelectItem value="enabled">Enabled</SelectItem>
                  </SelectContent>
                </Select>
              </FieldContent>
            </Field>
          </div>
        </FieldGroup>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={() => mutation.mutate()}
            disabled={!name.trim() || mutation.isPending}
          >
            {mutation.isPending ? (
              <Loader2Icon className="animate-spin" data-icon="inline-start" />
            ) : mode === "create" ? (
              <FolderPlusIcon data-icon="inline-start" />
            ) : (
              <PencilIcon data-icon="inline-start" />
            )}
            {mode === "create" ? "Create collection" : "Save changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function CollectionCard({ collection }: { collection: DiscoveryCollection }) {
  const [isEditing, setIsEditing] = useState(false)
  const [isDeleteConfirmOpen, setIsDeleteConfirmOpen] = useState(false)

  const removeMutation = useMutation({
    mutationFn: ({ paperId }: { paperId: number }) => removePaperFromCollection(collection.id, paperId),
    onSuccess: async () => {
      toast.success("Paper removed from collection")
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["discovery-collections"] }),
        queryClient.invalidateQueries({ queryKey: ["discovery-papers"] }),
      ])
    },
    onError: (error) => {
      toast.error("Failed to remove paper", { description: getErrorMessage(error) })
    },
  })

  const deleteCollectionMutation = useMutation({
    mutationFn: () => deleteDiscoveryCollection(collection.id),
    onSuccess: async () => {
      toast.success("Collection deleted")
      setIsDeleteConfirmOpen(false)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["discovery-collections"] }),
        queryClient.invalidateQueries({ queryKey: ["discovery-papers"] }),
      ])
    },
    onError: (error) => {
      toast.error("Failed to delete collection", { description: getErrorMessage(error) })
    },
  })

  return (
    <>
      <Card className="overflow-hidden">
        <CardHeader className="gap-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>{collection.name}</CardTitle>
              <CardDescription className="mt-1">
                {collection.description || "No description yet"}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Badge variant="outline">{collection.item_count} papers</Badge>
              <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
                <PencilIcon className="size-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsDeleteConfirmOpen(true)}
                disabled={deleteCollectionMutation.isPending}
              >
                {deleteCollectionMutation.isPending ? (
                  <Loader2Icon className="size-4 animate-spin" />
                ) : (
                  <Trash2Icon className="size-4" />
                )}
              </Button>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">
              {formatCollectionTranslationMode(collection.translation_mode)}
            </Badge>
            <Badge variant={collection.auto_translate_enabled ? "default" : "outline"}>
              {collection.auto_translate_enabled ? "Auto flag on" : "Auto flag off"}
            </Badge>
            {collection.categories_json.map((category) => (
              <Badge key={category} variant="outline">
                {category}
              </Badge>
            ))}
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border bg-muted/20 p-4 text-sm">
              <p className="font-medium">Prefer keywords</p>
              <p className="mt-1 text-muted-foreground">
                {collection.prefer_keywords || "None configured"}
              </p>
            </div>
            <div className="rounded-xl border bg-muted/20 p-4 text-sm">
              <p className="font-medium">Avoid keywords</p>
              <p className="mt-1 text-muted-foreground">
                {collection.avoid_keywords || "None configured"}
              </p>
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-medium">Saved papers</h3>
              <p className="text-xs text-muted-foreground">
                Updated {formatDateTime(collection.updated_at)}
              </p>
            </div>
            {collection.items.length ? (
              collection.items.map((item) => (
                <div
                  key={item.id}
                  className="flex flex-col gap-3 rounded-xl border bg-background p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{item.paper.title_en}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {item.paper.arxiv_id} {item.paper.primary_category ? `· ${item.paper.primary_category}` : ""}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge variant="outline">
                        {formatTranslateDecision(item.translate_decision)}
                      </Badge>
                      {item.paper.has_translation ? (
                        <Badge variant="secondary">
                          {item.paper.translation_task_count} translations
                        </Badge>
                      ) : null}
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {item.note || item.paper.comment || item.paper.abstract_zh || item.paper.abstract_en}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <Button asChild variant="outline" size="sm">
                      <Link to={`/papers/${item.paper.id}`}>
                        <FileTextIcon data-icon="inline-start" />
                        Open paper
                      </Link>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeMutation.mutate({ paperId: item.paper.id })}
                      disabled={removeMutation.isPending}
                    >
                      {removeMutation.isPending ? (
                        <Loader2Icon className="animate-spin" data-icon="inline-start" />
                      ) : (
                        <Trash2Icon data-icon="inline-start" />
                      )}
                      Remove
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <Empty className="min-h-0 border">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <BookmarkIcon />
                  </EmptyMedia>
                  <EmptyTitle>No papers saved yet</EmptyTitle>
                  <EmptyDescription>
                    Start from the discovery page and add papers into this collection.
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </div>
        </CardContent>
      </Card>
      <CollectionFormDialog
        open={isEditing}
        onOpenChange={setIsEditing}
        mode="edit"
        collection={collection}
      />
      <Dialog open={isDeleteConfirmOpen} onOpenChange={setIsDeleteConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete collection</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{collection.name}&rdquo;? This will permanently
              remove the collection and all its saved papers. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsDeleteConfirmOpen(false)}
              disabled={deleteCollectionMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteCollectionMutation.mutate()}
              disabled={deleteCollectionMutation.isPending}
            >
              {deleteCollectionMutation.isPending ? (
                <Loader2Icon className="size-4 animate-spin" data-icon="inline-start" />
              ) : (
                <Trash2Icon data-icon="inline-start" />
              )}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

export function CollectionsPage() {
  const [createOpen, setCreateOpen] = useState(false)

  const collectionsQuery = useQuery({
    queryKey: ["discovery-collections"],
    queryFn: () => listDiscoveryCollections(),
  })

  const summary = useMemo(() => {
    const items = collectionsQuery.data?.items ?? []
    return {
      totalCollections: items.length,
      totalPapers: items.reduce((sum, collection) => sum + collection.item_count, 0),
      autoEnabled: items.filter((collection) => collection.auto_translate_enabled).length,
    }
  }, [collectionsQuery.data?.items])

  return (
    <div className="flex flex-col gap-6">
      <Card className="overflow-hidden border-none bg-[linear-gradient(145deg,color-mix(in_oklab,var(--color-accent)_35%,white),color-mix(in_oklab,var(--color-primary)_12%,white))]">
        <CardContent className="grid gap-4 p-6 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
          <div className="space-y-3">
            <Badge variant="secondary" className="w-fit bg-white/70 text-slate-700">
              Collections
            </Badge>
            <div className="space-y-2">
              <h2 className="font-heading text-3xl font-semibold tracking-tight text-slate-900">
                Organize discovery around actual reading intent.
              </h2>
              <p className="max-w-2xl text-sm leading-6 text-slate-700">
                Collections shape how papers are triaged upstream. Use them to encode themes,
                categories, and what should eventually move into translation.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-2xl bg-white/70 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Collections</p>
              <p className="mt-2 text-3xl font-semibold text-slate-900">
                {summary.totalCollections}
              </p>
            </div>
            <div className="rounded-2xl bg-white/70 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Saved papers</p>
              <p className="mt-2 text-3xl font-semibold text-slate-900">{summary.totalPapers}</p>
            </div>
            <div className="rounded-2xl bg-white/70 p-4">
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Auto enabled</p>
              <p className="mt-2 text-3xl font-semibold text-slate-900">{summary.autoEnabled}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="font-heading text-2xl font-semibold tracking-tight">Your collections</h1>
          <p className="text-sm text-muted-foreground">
            Edit discovery preferences and review the papers already captured.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <FolderPlusIcon data-icon="inline-start" />
          Create collection
        </Button>
      </div>

      {collectionsQuery.isLoading ? (
        <div className="grid gap-4">
          <Skeleton className="h-72 w-full" />
          <Skeleton className="h-72 w-full" />
        </div>
      ) : collectionsQuery.data?.items.length ? (
        <div className="grid gap-6">
          {collectionsQuery.data.items.map((collection) => (
            <CollectionCard key={collection.id} collection={collection} />
          ))}
        </div>
      ) : (
        <Empty className="rounded-2xl border bg-card p-8">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <FolderPlusIcon />
            </EmptyMedia>
            <EmptyTitle>No collections created yet</EmptyTitle>
            <EmptyDescription>
              Start with one collection for a theme or workflow, then feed it from the discovery page.
            </EmptyDescription>
          </EmptyHeader>
          <Button onClick={() => setCreateOpen(true)}>Create your first collection</Button>
        </Empty>
      )}

      <CollectionFormDialog open={createOpen} onOpenChange={setCreateOpen} mode="create" />
    </div>
  )
}
