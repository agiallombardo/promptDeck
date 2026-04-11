import { Navigate } from "react-router-dom";
import { useAuthStore } from "../stores/auth";

export function RequireAdmin({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (user?.role !== "admin") {
    return <Navigate to="/files" replace />;
  }
  return children;
}
