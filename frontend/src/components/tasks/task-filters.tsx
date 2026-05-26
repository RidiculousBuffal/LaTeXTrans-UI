import { SearchIcon, XIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
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
import { taskStatuses, type TaskListFilters } from "@/lib/types"

type TaskFiltersProps = {
  filters: TaskListFilters
  onChange: (next: TaskListFilters) => void
  onReset: () => void
}

export function TaskFilters({ filters, onChange, onReset }: TaskFiltersProps) {
  return (
    <FieldGroup className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
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
      <Field className="justify-end">
        <FieldLabel className="sr-only">Actions</FieldLabel>
        <FieldContent className="flex flex-row gap-2">
          <Button type="button">
            <SearchIcon data-icon="inline-start" />
            Filters active
          </Button>
          <Button type="button" variant="outline" onClick={onReset}>
            <XIcon data-icon="inline-start" />
            Reset
          </Button>
        </FieldContent>
      </Field>
    </FieldGroup>
  )
}
