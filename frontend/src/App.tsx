import { useEffect } from 'react'
import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router'
import { AppShell } from '@/components/AppShell'
import { useAuthStore } from '@/features/auth/store'
import AuthPage from '@/pages/AuthPage'
import CreatePage from '@/pages/CreatePage'
import ProjectDetailPage from '@/pages/ProjectDetailPage'
import ProjectsPage from '@/pages/ProjectsPage'
import ModelSettingsPage from '@/pages/ModelSettingsPage'
import { RequireAuth } from '@/routes/RequireAuth'
import { RuntimeNotice } from '@/components/RuntimeNotice'

export default function App() {
  const restore = useAuthStore((state) => state.restore)

  useEffect(() => {
    void restore()
  }, [restore])

  return (
    <BrowserRouter>
      <div className="flex h-dvh flex-col">
      <RuntimeNotice />
      <div className="min-h-0 flex-1 overflow-auto">
      <Routes>
        <Route path="/login" element={<AuthPage />} />

        <Route
          element={
            <RequireAuth>
              <AppShell>
                <Outlet />
              </AppShell>
            </RequireAuth>
          }
        >
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/create" element={<CreatePage />} />
          <Route path="/settings/model" element={<ModelSettingsPage />} />
        </Route>

        {/* 大纲与编辑工作台自带全屏 chrome，不进工作区外壳 */}
        <Route
          element={
            <RequireAuth>
              <Outlet />
            </RequireAuth>
          }
        >
          <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/projects" replace />} />
      </Routes>
      </div>
      </div>
    </BrowserRouter>
  )
}
