import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Navigate } from "react-router-dom"
import { PlusIcon, KeyRoundIcon, CoinsIcon } from "lucide-react"

import { adminListUsers, adminAdjustQuota, adminCreateUser, adminChangePassword } from "@/lib/api"
import type { AdminUserItem } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
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
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { useAuth } from "@/lib/auth-context"
import { getErrorMessage } from "@/lib/utils-format"

// ─── Create User Dialog ───────────────────────────────────────────────────────

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
      adminCreateUser({ username, password, role, initial_quota: parseInt(initialQuota) || 0 }),
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
      toast.error("Failed to create user", { description: getErrorMessage(error) })
    },
  })

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create User</DialogTitle>
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
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="user">user</SelectItem>
                <SelectItem value="admin">admin</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label htmlFor="initial-quota">Initial Quota</Label>
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

// ─── Change Password Dialog ───────────────────────────────────────────────────

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
      toast.error("Failed to change password", { description: getErrorMessage(error) })
    },
  })

  const mismatch = confirm.length > 0 && newPassword !== confirm

  return (
    <Dialog open={!!target} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Change Password — {target?.username}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1">
            <Label htmlFor="cp-new">New Password</Label>
            <Input
              id="cp-new"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="cp-confirm">Confirm Password</Label>
            <Input
              id="cp-confirm"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className={mismatch ? "border-destructive" : ""}
            />
            {mismatch && <p className="text-xs text-destructive">Passwords do not match.</p>}
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

// ─── Adjust Quota Dialog ──────────────────────────────────────────────────────

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
    mutationFn: () =>
      adminAdjustQuota(target!.id, parseInt(delta), reason),
    onSuccess: () => {
      toast.success("Quota adjusted")
      onSuccess()
      onClose()
    },
    onError: (error) => {
      toast.error("Failed to adjust quota", { description: getErrorMessage(error) })
    },
  })

  return (
    <Dialog open={!!target} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Adjust Quota — {target?.username}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="space-y-1">
            <Label>Current Balance</Label>
            <p className="text-lg font-bold">{target?.quota_balance}</p>
          </div>
          <div className="space-y-1">
            <Label htmlFor="delta">Delta (positive to add, negative to deduct)</Label>
            <Input
              id="delta"
              type="number"
              value={delta}
              onChange={(e) => setDelta(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="reason">Reason</Label>
            <Input
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
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

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [page] = useState(1)
  const [showCreate, setShowCreate] = useState(false)
  const [pwTarget, setPwTarget] = useState<AdminUserItem | null>(null)
  const [quotaTarget, setQuotaTarget] = useState<AdminUserItem | null>(null)

  if (user?.role !== "admin") {
    return <Navigate to="/" replace />
  }

  const { data, isLoading } = useQuery({
    queryKey: ["admin-users", page],
    queryFn: () => adminListUsers(page, 50),
  })

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ["admin-users"] })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Admin Dashboard</h1>
          <p className="text-muted-foreground">Manage users and quotas</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <PlusIcon className="mr-1 size-4" />
          Add User
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Users ({data?.total ?? 0})</CardTitle>
          <CardDescription>Click the action buttons to manage each user.</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
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
                {data?.items.map((u) => (
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
                          <KeyRoundIcon className="size-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setQuotaTarget(u)}
                          title="Adjust quota"
                        >
                          <CoinsIcon className="size-4" />
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

      <CreateUserDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onSuccess={invalidate}
      />
      <ChangePasswordDialog
        target={pwTarget}
        onClose={() => setPwTarget(null)}
      />
      <AdjustQuotaDialog
        target={quotaTarget}
        onClose={() => setQuotaTarget(null)}
        onSuccess={invalidate}
      />
    </div>
  )
}
