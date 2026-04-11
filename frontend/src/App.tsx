import { Navigate } from "react-router-dom";
import { useAuthStore } from "./stores/auth";

export default function HomeRedirect() {
  const token = useAuthStore((s) => s.accessToken);
  if (token) {
    return <Navigate to="/files" replace />;
  }
  return <Navigate to="/login" replace />;
}
