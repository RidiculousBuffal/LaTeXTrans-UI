import { Button } from "@/components/ui/button"
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
} from "@/components/ui/pagination"

type ListPaginationProps = {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
}

function buildPageItems(page: number, totalPages: number) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1)
  }

  const pages = new Set<number>([1, totalPages, page - 1, page, page + 1])
  const visiblePages = Array.from(pages)
    .filter((item) => item >= 1 && item <= totalPages)
    .sort((a, b) => a - b)

  const items: Array<number | "ellipsis"> = []

  for (const visiblePage of visiblePages) {
    const previous = items[items.length - 1]

    if (typeof previous === "number" && visiblePage - previous > 1) {
      items.push("ellipsis")
    }

    items.push(visiblePage)
  }

  return items
}

export function ListPagination({
  page,
  pageSize,
  total,
  onPageChange,
}: ListPaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const canGoPrevious = page > 1
  const canGoNext = page < totalPages
  const pageItems = buildPageItems(page, totalPages)

  if (total <= pageSize) {
    return null
  }

  return (
    <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-sm text-muted-foreground">
        Showing page {page} of {totalPages} with {total} total items.
      </p>
      <Pagination className="mx-0 w-auto justify-start sm:justify-end">
        <PaginationContent>
          <PaginationItem>
            <Button
              type="button"
              variant="ghost"
              size="default"
              disabled={!canGoPrevious}
              onClick={() => onPageChange(page - 1)}
            >
              Previous
            </Button>
          </PaginationItem>
          {pageItems.map((item, index) => (
            <PaginationItem key={`${item}-${index}`}>
              {item === "ellipsis" ? (
                <PaginationEllipsis />
              ) : (
                <Button
                  type="button"
                  variant={item === page ? "outline" : "ghost"}
                  size="icon"
                  aria-current={item === page ? "page" : undefined}
                  onClick={() => onPageChange(item)}
                >
                  {item}
                </Button>
              )}
            </PaginationItem>
          ))}
          <PaginationItem>
            <Button
              type="button"
              variant="ghost"
              size="default"
              disabled={!canGoNext}
              onClick={() => onPageChange(page + 1)}
            >
              Next
            </Button>
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    </div>
  )
}
