import { MoonIcon, SunIcon, LogOutIcon, ShieldIcon } from "lucide-react"
import {
  NavLink,
  Outlet,
  useNavigate,
  Navigate,
  useLocation,
  matchPath,
} from "react-router-dom"
import { useTheme } from "next-themes"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { useAuth } from "@/lib/auth-context"

const navigation = [
  { to: "/discover", label: "Discover" },
  { to: "/collections", label: "Collections" },
  { to: "/tasks", label: "Tasks" },
  { to: "/tasks/new", label: "New Task" },
  { to: "/archives", label: "Archives" },
]

export function AppShell() {
  const { resolvedTheme, setTheme } = useTheme()
  const { user, logout, isLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex min-h-svh items-center justify-center text-muted-foreground text-sm">
        Loading...
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/landing" replace />
  }
  async function handleLogout() {
    await logout()
    navigate("/login")
  }

  const navItems = [
    ...navigation,
    ...(user?.role === "admin" ? [{ to: "/admin", label: "Admin" }] : []),
  ]

  function isNavItemActive(to: string) {
    const { pathname } = location

    if (to === "/tasks") {
      return (
        pathname === "/tasks" ||
        (pathname !== "/tasks/new" && matchPath("/tasks/:taskId", pathname) !== null)
      )
    }

    if (to === "/tasks/new") {
      return pathname === "/tasks/new"
    }

    return false
  }

  return (
    <div className="min-h-svh bg-[radial-gradient(circle_at_top_left,var(--color-primary)/0.08,transparent_28%),linear-gradient(180deg,var(--background),color-mix(in_oklab,var(--background)_92%,var(--color-muted)))] p-5">
      <div className="mx-auto flex min-h-svh max-w-7xl flex-col px-4 pb-4 sm:px-6 lg:px-8">
        <header className="sticky top-0 z-10 -mx-4 mb-6 bg-[radial-gradient(circle_at_top_left,var(--color-primary)/0.08,transparent_28%),linear-gradient(180deg,var(--background),color-mix(in_oklab,var(--background)_92%,var(--color-muted)))] px-4  sm:-mx-6 sm:px-6 lg:-mx-8 lg:px-8">
          <div className="rounded-2xl border bg-background/90 px-4 py-3 shadow-sm backdrop-blur">
           <div className="flex items-center gap-2 justify-between">
                <nav className="flex flex-wrap gap-2">
                  {navItems.map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.to === "/"}
                      className={({ isActive }) =>
                        cn(
                          "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                          (item.to.startsWith("/tasks")
                            ? isNavItemActive(item.to)
                            : isActive)
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-muted hover:text-foreground"
                        )
                      }
                    >
                      {item.label}
                    </NavLink>
                  ))}
                </nav>
                <div className={'flex gap-3 items-center'}>
                  {user && (
                  <div className="flex items-center gap-2 text-sm">
                    {user.role === "admin" && (
                      <ShieldIcon className="h-4 w-4 text-orange-500" />
                    )}
                    <span className="text-muted-foreground">{user.username}</span>
                    <Badge variant="outline" title="Translation quota balance">
                      {user.quota_balance} quota
                    </Badge>
                  </div>
                )}
                <Button
                  type="button"
                  variant="outline"
                  size="icon-sm"
                  onClick={() =>
                    setTheme(resolvedTheme === "dark" ? "light" : "dark")
                  }
                >
                  {resolvedTheme === "dark" ? <SunIcon /> : <MoonIcon />}
                  <span className="sr-only">Toggle theme</span>
                </Button>
                {user && (
                  <Button
                    type="button"
                    variant="outline"
                    size="icon-sm"
                    onClick={() => {
                      void handleLogout()
                    }}
                    title="Sign out"
                  >
                    <LogOutIcon />
                    <span className="sr-only">Sign out</span>
                  </Button>
                )}
                </div>
              </div>
          </div>
        </header>
        <main className="flex-1 pb-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
