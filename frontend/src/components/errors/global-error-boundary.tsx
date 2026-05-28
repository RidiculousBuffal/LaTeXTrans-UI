import { AlertTriangleIcon, HomeIcon, RefreshCcwIcon } from "lucide-react"
import type { ErrorInfo, ReactNode } from "react"
import { Component } from "react"
import {
  isRouteErrorResponse,
  Link,
  useLocation,
  useRouteError,
} from "react-router-dom"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

type ErrorDetails = {
  title: string
  description: string
  statusLabel: string
  debugMessage?: string
}

function getErrorDetails(error: unknown, pathname?: string): ErrorDetails {
  if (isRouteErrorResponse(error)) {
    const isNotFound = error.status === 404

    return {
      title: isNotFound ? "Page not found" : "Route request failed",
      description: isNotFound
        ? `No page is available for ${pathname ?? "this address"}.`
        : "The current page could not be loaded because the router reported an error.",
      statusLabel: `${error.status} ${error.statusText || "Error"}`.trim(),
      debugMessage:
        typeof error.data === "string"
          ? error.data
          : error.statusText || undefined,
    }
  }

  if (error instanceof Error) {
    return {
      title: "Something went wrong",
      description:
        "An unexpected frontend error interrupted this screen. You can retry or head back to the task list.",
      statusLabel: "Unexpected error",
      debugMessage: error.message,
    }
  }

  return {
    title: "Something went wrong",
    description:
      "An unexpected frontend error interrupted this screen. You can retry or head back to the task list.",
    statusLabel: "Unexpected error",
  }
}

type ErrorFallbackViewProps = {
  error?: unknown
  pathname?: string
  onRetry?: () => void
}

function ErrorFallbackView({
  error,
  pathname,
  onRetry,
}: ErrorFallbackViewProps) {
  const details = getErrorDetails(error, pathname)

  return (
    <div className="min-h-svh bg-[radial-gradient(circle_at_top_left,_var(--color-primary)/0.08,_transparent_28%),linear-gradient(180deg,var(--background),color-mix(in_oklab,var(--background)_92%,var(--color-muted)))] p-5">
      <div className="mx-auto flex min-h-svh max-w-3xl items-center justify-center px-4 py-10 sm:px-6 lg:px-8">
        <Card className="w-full border bg-background/92 shadow-sm backdrop-blur">
          <CardHeader className="gap-3 border-b">
            <div className="flex items-center gap-3">
              <div className="flex size-11 items-center justify-center rounded-2xl bg-destructive/12 text-destructive">
                <AlertTriangleIcon className="size-5" />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium uppercase tracking-[0.24em] text-muted-foreground">
                  Global Error Boundary
                </p>
                <CardTitle className="text-2xl">{details.title}</CardTitle>
              </div>
            </div>
            <CardDescription className="max-w-2xl text-sm/relaxed">
              {details.description}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-6">
            <div className="rounded-2xl border border-dashed bg-muted/40 px-4 py-3">
              <p className="text-xs font-medium uppercase tracking-[0.24em] text-muted-foreground">
                Status
              </p>
              <p className="mt-2 font-medium">{details.statusLabel}</p>
              {pathname ? (
                <p className="mt-1 break-all text-sm text-muted-foreground">
                  Requested path: {pathname}
                </p>
              ) : null}
            </div>
            {details.debugMessage ? (
              <div className="rounded-2xl border bg-card px-4 py-3">
                <p className="text-xs font-medium uppercase tracking-[0.24em] text-muted-foreground">
                  Details
                </p>
                <p className="mt-2 break-words font-mono text-xs text-muted-foreground">
                  {details.debugMessage}
                </p>
              </div>
            ) : null}
          </CardContent>
          <CardFooter className="flex flex-wrap justify-between gap-3">
            <Button asChild variant="outline">
              <Link to="/">
                <HomeIcon />
                Back to tasks
              </Link>
            </Button>
            <Button
              type="button"
              onClick={() => {
                if (onRetry) {
                  onRetry()
                  return
                }
                window.location.reload()
              }}
            >
              <RefreshCcwIcon />
              Try again
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}

export function RouteErrorBoundary() {
  const error = useRouteError()
  const location = useLocation()

  return <ErrorFallbackView error={error} pathname={location.pathname} />
}

type GlobalErrorBoundaryProps = {
  children: ReactNode
}

type GlobalErrorBoundaryState = {
  error: Error | null
}

export class GlobalErrorBoundary extends Component<
  GlobalErrorBoundaryProps,
  GlobalErrorBoundaryState
> {
  state: GlobalErrorBoundaryState = {
    error: null,
  }

  static getDerivedStateFromError(error: Error): GlobalErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("GlobalErrorBoundary caught an error", error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ error: null })
    window.location.reload()
  }

  render() {
    if (this.state.error) {
      return (
        <ErrorFallbackView error={this.state.error} onRetry={this.handleRetry} />
      )
    }

    return this.props.children
  }
}
