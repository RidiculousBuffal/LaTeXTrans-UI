import { createBrowserRouter, RouterProvider } from "react-router-dom"

import { AppShell } from "@/components/layout/app-shell"
import { ArchivesPage } from "@/pages/archives-page"
import { NewTaskPage } from "@/pages/new-task-page"
import { TaskDetailPage } from "@/pages/task-detail-page"
import { TasksPage } from "@/pages/tasks-page"

const router = createBrowserRouter([
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
    ],
  },
])

function App() {
  return <RouterProvider router={router} />
}

export default App
