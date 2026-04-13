import { queryClient } from "./queryClient";
import { useAuthStore } from "../stores/auth";

function shouldSkipUnauthorizedSessionClear(requestPath: string): boolean {
  return (
    requestPath.includes("/auth/login") ||
    requestPath.includes("/auth/config") ||
    requestPath.includes("/share-links/exchange")
  );
}

/**
 * When the API rejects the session (401), clear client auth and cached queries so
 * RequireAuth / RequireDeckAccess send the user to the login page.
 */
export function handleApiUnauthorized(requestPath: string): void {
  if (shouldSkipUnauthorizedSessionClear(requestPath)) return;
  useAuthStore.getState().clear();
  queryClient.clear();
}
