import { createBrowserRouter, RouterProvider } from "react-router-dom"

import {
  RouteErrorBoundary,
  GlobalErrorBoundary,
} from "@/components/errors/global-error-boundary"
import { AuthProvider } from "@/lib/auth-context"

import { AppShell } from "@/components/layout/app-shell"
import { ArchivesPage } from "@/pages/archives-page"
import { CollectionsPage } from "@/pages/collections-page"
import { DiscoverPage } from "@/pages/discover-page"
import { NewTaskPage } from "@/pages/new-task-page"
import { PaperDetailPage } from "@/pages/paper-detail-page"
import { TaskDetailPage } from "@/pages/task-detail-page"
import { TasksPage } from "@/pages/tasks-page"
import LoginPage from "@/pages/login-page"
import RegisterPage from "@/pages/register-page"
import AdminPage from "@/pages/admin-page"
import LandingPage from "@/pages/landing-page"

const router = createBrowserRouter([
  {
    path: "/landing",
    element: <LandingPage />,
    errorElement: <RouteErrorBoundary />,
  },
  {
    path: "/login",
    element: <LoginPage />,
    errorElement: <RouteErrorBoundary />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
    errorElement: <RouteErrorBoundary />,
  },
  {
    path: "/",
    element: <AppShell />,
    errorElement: <RouteErrorBoundary />,
    children: [
      {
        index: true,
        element: <DiscoverPage />,
      },
      {
        path: "discover",
        element: <DiscoverPage />,
      },
      {
        path: "collections",
        element: <CollectionsPage />,
      },
      {
        path: "papers/:paperId",
        element: <PaperDetailPage />,
      },
      {
        path: "tasks",
        element: <TasksPage />,
      },
      {
        path: "tasks/new",
        element: <NewTaskPage />,
      },
      {
        path: "tasks/:taskId",
        element: <TaskDetailPage />,
      },
      {
        path: "archives",
        element: <ArchivesPage />,
      },
      {
        path: "admin",
        element: <AdminPage />,
      },
    ],
  },
])

function App() {
  return (
    <AuthProvider>
      <GlobalErrorBoundary>
        <RouterProvider router={router} />
      </GlobalErrorBoundary>
    </AuthProvider>
  )
}

export default App
