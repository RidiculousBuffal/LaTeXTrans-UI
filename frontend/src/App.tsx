import { createBrowserRouter, RouterProvider } from "react-router-dom"

import { AuthProvider } from "@/lib/auth-context"

import { AppShell } from "@/components/layout/app-shell"
import { ArchivesPage } from "@/pages/archives-page"
import { NewTaskPage } from "@/pages/new-task-page"
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
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
  },
  {
    path: "/",
    element: <AppShell />,
    children: [
      {
        index: true,
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
      <RouterProvider router={router} />
    </AuthProvider>
  )
}

export default App
