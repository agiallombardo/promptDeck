import { Navigate, Route, Routes } from "react-router-dom";
import AdminPage from "./pages/AdminPage";
import FileManagerPage from "./pages/FileManagerPage";
import LoginPage from "./pages/LoginPage";
import PresentationPage from "./pages/PresentationPage";
import App from "./App";

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<App />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/files" element={<FileManagerPage />} />
      <Route path="/p/:id" element={<PresentationPage />} />
      <Route path="/admin" element={<AdminPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
