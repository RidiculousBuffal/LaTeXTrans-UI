import {useState} from "react"
import {useMutation, useQuery, useQueryClient} from "@tanstack/react-query"
import {format} from "date-fns"
import {toast} from "sonner"
import {Navigate} from "react-router-dom"
import {
    CalendarIcon,
    CoinsIcon,
    KeyRoundIcon,
    Loader2Icon,
    OrbitIcon,
    PlusIcon,
    RefreshCwIcon,
} from "lucide-react"

import {
    adminAdjustQuota,
    adminChangePassword,
    adminCreateUser,
    adminListDiscoveryRuns,
    adminListUsers,
    adminTriggerDiscoverySync,
} from "@/lib/api"
import type {AdminUserItem, DiscoveryRun} from "@/lib/types"
import {Button} from "@/components/ui/button"
import {Calendar} from "@/components/ui/calendar"
import {Input} from "@/components/ui/input"
import {Badge} from "@/components/ui/badge"
import {Card, CardContent, CardHeader, CardTitle, CardDescription} from "@/components/ui/card"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import {
    Dialog,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import {Label} from "@/components/ui/label"
import {Popover, PopoverContent, PopoverTrigger} from "@/components/ui/popover"
import {useAuth} from "@/lib/auth-context"
import {
    formatDateTime,
    formatDiscoveryRunStatus,
    formatRelativeTime,
    getErrorMessage,
} from "@/lib/utils-format"
import {Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle} from "@/components/ui/empty"
import {Alert, AlertDescription, AlertTitle} from "@/components/ui/alert"
import {cn} from "@/lib/utils"

function CreateUserDialog({
                              open,
                              onClose,
                              onSuccess,
                          }: {
    open: boolean
    onClose: () => void
    onSuccess: () => void
}) {
    const [username, setUsername] = useState("")
    const [password, setPassword] = useState("")
    const [role, setRole] = useState<"user" | "admin">("user")
    const [initialQuota, setInitialQuota] = useState("10")

    const mutation = useMutation({
        mutationFn: () =>
            adminCreateUser({
                username,
                password,
                role,
                initial_quota: parseInt(initialQuota, 10) || 0,
            }),
        onSuccess: () => {
            toast.success(`User "${username}" created`)
            setUsername("")
            setPassword("")
            setRole("user")
            setInitialQuota("10")
            onSuccess()
            onClose()
        },
        onError: (error) => {
            toast.error("Failed to create user", {description: getErrorMessage(error)})
        },
    })

    return (
        <Dialog open={open} onOpenChange={onClose}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Create user</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-2">
                    <div className="space-y-1">
                        <Label htmlFor="new-username">Username</Label>
                        <Input
                            id="new-username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="e.g. alice"
                            autoComplete="off"
                        />
                    </div>
                    <div className="space-y-1">
                        <Label htmlFor="new-password">Password</Label>
                        <Input
                            id="new-password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            autoComplete="new-password"
                        />
                    </div>
                    <div className="space-y-1">
                        <Label>Role</Label>
                        <Select value={role} onValueChange={(v) => setRole(v as "user" | "admin")}>
                            <SelectTrigger>
                                <SelectValue/>
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="user">user</SelectItem>
                                <SelectItem value="admin">admin</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-1">
                        <Label htmlFor="initial-quota">Initial quota</Label>
                        <Input
                            id="initial-quota"
                            type="number"
                            value={initialQuota}
                            onChange={(e) => setInitialQuota(e.target.value)}
                            min={0}
                        />
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button
                        onClick={() => mutation.mutate()}
                        disabled={!username.trim() || !password.trim() || mutation.isPending}
                    >
                        {mutation.isPending ? "Creating..." : "Create"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}

function ChangePasswordDialog({
                                  target,
                                  onClose,
                              }: {
    target: AdminUserItem | null
    onClose: () => void
}) {
    const [newPassword, setNewPassword] = useState("")
    const [confirm, setConfirm] = useState("")

    const mutation = useMutation({
        mutationFn: () => adminChangePassword(target!.id, newPassword),
        onSuccess: () => {
            toast.success(`Password changed for "${target?.username}"`)
            setNewPassword("")
            setConfirm("")
            onClose()
        },
        onError: (error) => {
            toast.error("Failed to change password", {description: getErrorMessage(error)})
        },
    })

    const mismatch = confirm.length > 0 && newPassword !== confirm

    return (
        <Dialog open={!!target} onOpenChange={onClose}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Change password - {target?.username}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-2">
                    <div className="space-y-1">
                        <Label htmlFor="cp-new">New password</Label>
                        <Input
                            id="cp-new"
                            type="password"
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            autoComplete="new-password"
                        />
                    </div>
                    <div className="space-y-1">
                        <Label htmlFor="cp-confirm">Confirm password</Label>
                        <Input
                            id="cp-confirm"
                            type="password"
                            value={confirm}
                            onChange={(e) => setConfirm(e.target.value)}
                            className={mismatch ? "border-destructive" : ""}
                        />
                        {mismatch ? <p className="text-xs text-destructive">Passwords do not match.</p> : null}
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button
                        onClick={() => mutation.mutate()}
                        disabled={!newPassword || mismatch || mutation.isPending}
                    >
                        {mutation.isPending ? "Saving..." : "Save"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}

function AdjustQuotaDialog({
                               target,
                               onClose,
                               onSuccess,
                           }: {
    target: AdminUserItem | null
    onClose: () => void
    onSuccess: () => void
}) {
    const [delta, setDelta] = useState("10")
    const [reason, setReason] = useState("manual grant")

    const mutation = useMutation({
        mutationFn: () => adminAdjustQuota(target!.id, parseInt(delta, 10), reason),
        onSuccess: () => {
            toast.success("Quota adjusted")
            onSuccess()
            onClose()
        },
        onError: (error) => {
            toast.error("Failed to adjust quota", {description: getErrorMessage(error)})
        },
    })

    return (
        <Dialog open={!!target} onOpenChange={onClose}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Adjust quota - {target?.username}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-2">
                    <div className="space-y-1">
                        <Label>Current balance</Label>
                        <p className="text-lg font-bold">{target?.quota_balance}</p>
                    </div>
                    <div className="space-y-1">
                        <Label htmlFor="delta">Delta</Label>
                        <Input
                            id="delta"
                            type="number"
                            value={delta}
                            onChange={(e) => setDelta(e.target.value)}
                        />
                    </div>
                    <div className="space-y-1">
                        <Label htmlFor="reason">Reason</Label>
                        <Input id="reason" value={reason} onChange={(e) => setReason(e.target.value)}/>
                    </div>
                </div>
                <DialogFooter>
                    <Button variant="outline" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
                        {mutation.isPending ? "Saving..." : "Apply"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    )
}

function DiscoverySyncCard({
                               latestRun,
                               onRefresh,
                           }: {
    latestRun: DiscoveryRun | null
    onRefresh: () => void
}) {
    const queryClient = useQueryClient()
    const [sourceRunDate, setSourceRunDate] = useState<Date | undefined>(undefined)
    const [forceRefresh, setForceRefresh] = useState("false")
    const [runInline, setRunInline] = useState("false")

    const mutation = useMutation({
        mutationFn: () =>
            adminTriggerDiscoverySync({
                source_run_date: sourceRunDate ? format(sourceRunDate, "yyyy-MM-dd") : undefined,
                force_refresh: forceRefresh === "true",
                run_inline: runInline === "true",
            }),
        onSuccess: async (run) => {
            toast.success("Discovery sync scheduled", {
                description: `Run ${run.id} is now ${formatDiscoveryRunStatus(run.status).toLowerCase()}.`,
            })
            onRefresh()
            await queryClient.invalidateQueries({queryKey: ["discovery-daily-digest"]})
        },
        onError: (error) => {
            toast.error("Failed to trigger discovery sync", {description: getErrorMessage(error)})
        },
    })

    return (
        <Card>
            <CardHeader>
                <CardTitle>Discovery sync</CardTitle>
                <CardDescription>
                    Trigger a new arXiv discovery run and inspect the latest sync health without leaving the admin
                    workspace.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
                <div className="grid gap-4 md:grid-cols-3">
                    <div className="space-y-1">
                        <Label htmlFor="sync-date">Source run date</Label>
                        <Popover>
                            <PopoverTrigger asChild>
                                <Button
                                    id="sync-date"
                                    type="button"
                                    variant="outline"
                                    className={cn(
                                        "w-full justify-start text-left font-normal",
                                        !sourceRunDate && "text-muted-foreground"
                                    )}
                                >
                                    <CalendarIcon data-icon="inline-start"/>
                                    {sourceRunDate ? format(sourceRunDate, "PPP") : "Pick a source run date"}
                                </Button>
                            </PopoverTrigger>
                            <PopoverContent className="w-auto p-0" align="start">
                                <Calendar
                                    mode="single"
                                    captionLayout="dropdown"
                                    selected={sourceRunDate}
                                    onSelect={setSourceRunDate}
                                />
                            </PopoverContent>
                        </Popover>
                    </div>
                    <div className="space-y-1">
                        <Label htmlFor="sync-force">Force refresh</Label>
                        <Select value={forceRefresh} onValueChange={setForceRefresh}>
                            <SelectTrigger id="sync-force" className="w-full">
                                <SelectValue/>
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="false">No</SelectItem>
                                <SelectItem value="true">Yes</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                    <div className="space-y-1">
                        <Label htmlFor="sync-inline">Run inline</Label>
                        <Select value={runInline} onValueChange={setRunInline}>
                            <SelectTrigger id="sync-inline" className="w-full">
                                <SelectValue/>
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="false">Queue only</SelectItem>
                                <SelectItem value="true">Execute inline</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                    <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
                        {mutation.isPending ? (
                            <Loader2Icon className="animate-spin" data-icon="inline-start"/>
                        ) : (
                            <OrbitIcon data-icon="inline-start"/>
                        )}
                        Trigger discovery sync
                    </Button>
                    {latestRun ? (
                        <p className="text-sm text-muted-foreground">
                            Latest run {formatRelativeTime(latestRun.updated_at)} for {latestRun.source_run_date}
                        </p>
                    ) : (
                        <p className="text-sm text-muted-foreground">No discovery run recorded yet.</p>
                    )}
                </div>
                {latestRun?.error_message ? (
                    <Alert variant="destructive">
                        <AlertTitle>Latest run reported an error</AlertTitle>
                        <AlertDescription>{latestRun.error_message}</AlertDescription>
                    </Alert>
                ) : null}
            </CardContent>
        </Card>
    )
}

export default function AdminPage() {
    const {user} = useAuth()
    const queryClient = useQueryClient()
    const [page] = useState(1)
    const [showCreate, setShowCreate] = useState(false)
    const [pwTarget, setPwTarget] = useState<AdminUserItem | null>(null)
    const [quotaTarget, setQuotaTarget] = useState<AdminUserItem | null>(null)

    if (user?.role !== "admin") {
        return <Navigate to="/" replace/>
    }

    const usersQuery = useQuery({
        queryKey: ["admin-users", page],
        queryFn: () => adminListUsers(page, 50),
    })

    const discoveryRunsQuery = useQuery({
        queryKey: ["admin-discovery-runs", 1, 10],
        queryFn: () => adminListDiscoveryRuns(1, 10),
        refetchInterval: 10_000,
    })

    function invalidateUsers() {
        queryClient.invalidateQueries({queryKey: ["admin-users"]})
    }

    async function refreshDiscovery() {
        await Promise.all([
            queryClient.invalidateQueries({queryKey: ["admin-discovery-runs"]}),
            queryClient.invalidateQueries({queryKey: ["discovery-papers"]}),
            queryClient.invalidateQueries({queryKey: ["discovery-paper"]}),
            queryClient.invalidateQueries({queryKey: ["discovery-collections"]}),
        ])
    }

    const latestRun = discoveryRunsQuery.data?.items[0] ?? null

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h1 className="text-2xl font-bold">Admin dashboard</h1>
                    <p className="text-muted-foreground">Manage users, quota, and discovery operations</p>
                </div>
            </div>

            <DiscoverySyncCard latestRun={latestRun} onRefresh={() => void refreshDiscovery()}/>

            <Card>
                <CardHeader className="flex flex-row items-start justify-between gap-4">
                    <div>
                        <CardTitle>Discovery runs</CardTitle>
                        <CardDescription>
                            Recent pipeline executions, useful for checking freshness and failure modes.
                        </CardDescription>
                    </div>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={() => void refreshDiscovery()}
                        disabled={discoveryRunsQuery.isFetching}
                    >
                        {discoveryRunsQuery.isFetching ? (
                            <Loader2Icon className="animate-spin" data-icon="inline-start"/>
                        ) : (
                            <RefreshCwIcon data-icon="inline-start"/>
                        )}
                        Refresh
                    </Button>
                </CardHeader>
                <CardContent>
                    {discoveryRunsQuery.isLoading ? (
                        <p className="text-muted-foreground">Loading discovery runs...</p>
                    ) : discoveryRunsQuery.data?.items.length ? (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Date</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Trigger</TableHead>
                                    <TableHead>Papers</TableHead>
                                    <TableHead>Worth read</TableHead>
                                    <TableHead>Updated</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {discoveryRunsQuery.data.items.map((run) => (
                                    <TableRow key={run.id}>
                                        <TableCell className="font-medium">{run.source_run_date}</TableCell>
                                        <TableCell>
                                            <Badge
                                                variant={
                                                    run.status === "FAILED"
                                                        ? "destructive"
                                                        : run.status === "SUCCEEDED"
                                                            ? "secondary"
                                                            : "outline"
                                                }
                                            >
                                                {formatDiscoveryRunStatus(run.status)}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>{run.trigger_source}</TableCell>
                                        <TableCell>{run.total_papers}</TableCell>
                                        <TableCell>{run.total_worth_read}</TableCell>
                                        <TableCell className="text-muted-foreground">
                                            {formatRelativeTime(run.updated_at)}
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    ) : (
                        <Empty className="border">
                            <EmptyHeader>
                                <EmptyMedia variant="icon">
                                    <OrbitIcon/>
                                </EmptyMedia>
                                <EmptyTitle>No discovery runs yet</EmptyTitle>
                                <EmptyDescription>
                                    Trigger the first run from the card above to populate discovery data.
                                </EmptyDescription>
                            </EmptyHeader>
                        </Empty>
                    )}
                </CardContent>
            </Card>

            <Card>
                <CardHeader className={"flex justify-between items-center"}>
                    <div>
                        <CardTitle>Users ({usersQuery.data?.total ?? 0})</CardTitle>
                        <CardDescription>Click the action buttons to manage each user.</CardDescription>
                    </div>
                    <div>
                        <Button onClick={() => setShowCreate(true)}>
                            <PlusIcon className="mr-1 size-4"/>
                            Add user
                        </Button>
                    </div>

                </CardHeader>
                <CardContent>
                    {usersQuery.isLoading ? (
                        <p className="text-muted-foreground">Loading...</p>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Username</TableHead>
                                    <TableHead>Role</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead>Quota</TableHead>
                                    <TableHead>Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {usersQuery.data?.items.map((u) => (
                                    <TableRow key={u.id}>
                                        <TableCell className="font-medium">{u.username}</TableCell>
                                        <TableCell>
                                            <Badge variant={u.role === "admin" ? "default" : "secondary"}>
                                                {u.role}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant={u.is_active ? "outline" : "destructive"}>
                                                {u.is_active ? "active" : "disabled"}
                                            </Badge>
                                        </TableCell>
                                        <TableCell>{u.quota_balance}</TableCell>
                                        <TableCell>
                                            <div className="flex gap-2">
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={() => setPwTarget(u)}
                                                    title="Change password"
                                                >
                                                    <KeyRoundIcon className="size-4"/>
                                                </Button>
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={() => setQuotaTarget(u)}
                                                    title="Adjust quota"
                                                >
                                                    <CoinsIcon className="size-4"/>
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            {latestRun ? (
                <Card>
                    <CardHeader>
                        <CardTitle>Latest run details</CardTitle>
                        <CardDescription>
                            Useful when you need exact timestamps or a quick explanation for what just happened.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="grid gap-4 md:grid-cols-2">
                        <div className="space-y-1">
                            <p className="text-sm font-medium">Started</p>
                            <p className="text-sm text-muted-foreground">{formatDateTime(latestRun.started_at)}</p>
                        </div>
                        <div className="space-y-1">
                            <p className="text-sm font-medium">Finished</p>
                            <p className="text-sm text-muted-foreground">{formatDateTime(latestRun.finished_at)}</p>
                        </div>
                        <div className="space-y-1">
                            <p className="text-sm font-medium">Categories</p>
                            <p className="text-sm text-muted-foreground">
                                {latestRun.categories_json.join(", ") || "—"}
                            </p>
                        </div>
                        <div className="space-y-1">
                            <p className="text-sm font-medium">Created at</p>
                            <p className="text-sm text-muted-foreground">{formatDateTime(latestRun.created_at)}</p>
                        </div>
                    </CardContent>
                </Card>
            ) : null}

            <CreateUserDialog
                open={showCreate}
                onClose={() => setShowCreate(false)}
                onSuccess={invalidateUsers}
            />
            <ChangePasswordDialog target={pwTarget} onClose={() => setPwTarget(null)}/>
            <AdjustQuotaDialog
                target={quotaTarget}
                onClose={() => setQuotaTarget(null)}
                onSuccess={invalidateUsers}
            />
        </div>
    )
}
