import { SearchIcon, XIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Field,
  FieldContent,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { taskStatuses, type TaskListFilters } from "@/lib/types"

type TaskFiltersProps = {
  filters: TaskListFilters
  onChange: (next: TaskListFilters) => void
  onReset: () => void
}

export function TaskFilters({ filters, onChange, onReset }: TaskFiltersProps) {
  const activeCount = [
    filters.task_name,
    filters.arxiv_id,
    filters.status,
    filters.created_by,
    filters.created_from,
    filters.created_to,
  ].filter((value) => Boolean(value)).length

  return (
    <FieldGroup className="flex flex-col gap-4">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
      <Field>
        <FieldLabel htmlFor="task-name">Task name</FieldLabel>
        <FieldContent>
          <Input
            id="task-name"
            value={filters.task_name ?? ""}
            onChange={(event) =>
              onChange({ ...filters, page: 1, task_name: event.target.value })
            }
            placeholder="Search by task name"
          />
        </FieldContent>
      </Field>
      <Field>
        <FieldLabel htmlFor="arxiv-id">arXiv ID</FieldLabel>
        <FieldContent>
          <Input
            id="arxiv-id"
            value={filters.arxiv_id ?? ""}
            onChange={(event) =>
              onChange({ ...filters, page: 1, arxiv_id: event.target.value })
            }
            placeholder="2501.00001"
          />
        </FieldContent>
      </Field>
      <Field>
        <FieldLabel>Status</FieldLabel>
        <FieldContent>
          <Select
            value={filters.status ?? ""}
            onValueChange={(value) =>
              onChange({
                ...filters,
                page: 1,
                status: value === "ALL" ? "" : (value as TaskListFilters["status"]),
              })
            }
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="ALL">All statuses</SelectItem>
                {taskStatuses.map((status) => (
                  <SelectItem key={status} value={status}>
                    {status}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </FieldContent>
      </Field>
      <Field>
        <FieldLabel htmlFor="created-by">Created by</FieldLabel>
        <FieldContent>
          <Input
            id="created-by"
            value={filters.created_by ?? ""}
            onChange={(event) =>
              onChange({ ...filters, page: 1, created_by: event.target.value })
            }
            placeholder="frontend-user"
          />
        </FieldContent>
      </Field>
      <Field>
        <FieldLabel htmlFor="created-from">Created from</FieldLabel>
        <FieldContent>
          <Input
            id="created-from"
            type="datetime-local"
            value={filters.created_from ?? ""}
            onChange={(event) =>
              onChange({ ...filters, page: 1, created_from: event.target.value })
            }
          />
        </FieldContent>
      </Field>
      <Field>
        <FieldLabel htmlFor="created-to">Created to</FieldLabel>
        <FieldContent>
          <Input
            id="created-to"
            type="datetime-local"
            value={filters.created_to ?? ""}
            onChange={(event) =>
              onChange({ ...filters, page: 1, created_to: event.target.value })
            }
          />
        </FieldContent>
      </Field>
      </div>
      <div className="flex flex-col gap-3 rounded-xl border border-dashed bg-muted/20 p-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <SearchIcon />
          <span>Current filters</span>
          <Badge
            variant="outline"
            className={cn(
              activeCount > 0 && "border-primary/20 bg-primary/8 text-foreground"
            )}
          >
            {activeCount} active
          </Badge>
        </div>
        <div className="flex flex-wrap gap-2 sm:justify-end">
          <Button type="button" variant="outline" onClick={onReset}>
            <XIcon data-icon="inline-start" />
            Reset filters
          </Button>
        </div>
      </div>
    </FieldGroup>
  )
}
