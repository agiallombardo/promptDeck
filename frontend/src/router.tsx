import { Navigate, Route, Routes } from "react-router-dom";
import { RequireAdmin } from "./components/RequireAdmin";
import { RequireAuth } from "./components/RequireAuth";
import { AppShell } from "./components/layout/AppShell";
import HomeRedirect from "./App";
import AdminPage from "./pages/AdminPage";
import FileManagerPage from "./pages/FileManagerPage";
import LoginPage from "./pages/LoginPage";
import PresentationPage from "./pages/PresentationPage";
import ShareEntryPage from "./pages/ShareEntryPage";

function AuthenticatedLayout() {
  return (
    <RequireAuth>
      <AppShell />
    </RequireAuth>
  );
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AuthenticatedLayout />}>
        <Route path="files" element={<FileManagerPage />} />
        <Route
          path="admin"
          element={
            <RequireAdmin>
              <AdminPage />
            </RequireAdmin>
          }
        />
      </Route>
      <Route path="/share/:token" element={<ShareEntryPage />} />
      <Route path="/p/:id" element={<PresentationPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
