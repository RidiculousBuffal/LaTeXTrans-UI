import { format } from "date-fns"
import type { DateRange } from "react-day-picker"
import { CalendarIcon, SearchIcon, XIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Calendar } from "@/components/ui/calendar"
import {
  Field,
  FieldContent,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
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

function toDateRange(
  createdFrom?: string,
  createdTo?: string
): DateRange | undefined {
  if (!createdFrom && !createdTo) {
    return undefined
  }

  return {
    from: createdFrom ? new Date(createdFrom) : undefined,
    to: createdTo ? new Date(createdTo) : undefined,
  }
}

function setDateTime(date: Date, hours: number, minutes: number, seconds: number, milliseconds: number) {
  const next = new Date(date)
  next.setHours(hours, minutes, seconds, milliseconds)
  return next
}

export function TaskFilters({ filters, onChange, onReset }: TaskFiltersProps) {
  const selectedRange = toDateRange(filters.created_from, filters.created_to)
  const activeCount = [
    filters.task_name,
    filters.arxiv_id,
    filters.status,
    filters.created_from,
    filters.created_to,
  ].filter((value) => Boolean(value)).length

  const dateRangeLabel =
    selectedRange?.from == null
      ? "Pick a date range"
      : selectedRange.to == null
        ? format(selectedRange.from, "PPP")
        : `${format(selectedRange.from, "PPP")} - ${format(selectedRange.to, "PPP")}`

  function handleDateRangeChange(range: DateRange | undefined) {
    onChange({
      ...filters,
      page: 1,
      created_from: range?.from
        ? setDateTime(range.from, 0, 0, 0, 0).toISOString()
        : "",
      created_to: range?.to
        ? setDateTime(range.to, 23, 59, 59, 999).toISOString()
        : range?.from
          ? setDateTime(range.from, 23, 59, 59, 999).toISOString()
          : "",
    })
  }

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
        <Field className="md:col-span-2 xl:col-span-3">
          <FieldLabel>Created date range</FieldLabel>
          <FieldContent>
            <Popover>
              <PopoverTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  className={cn(
                    "w-full justify-start text-left font-normal",
                    !selectedRange?.from && "text-muted-foreground"
                  )}
                >
                  <CalendarIcon data-icon="inline-start" />
                  {dateRangeLabel}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="start">
                <Calendar
                  mode="range"
                  captionLayout={'dropdown'}
                  numberOfMonths={2}
                  selected={selectedRange}
                  onSelect={handleDateRangeChange}
                />
              </PopoverContent>
            </Popover>
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
