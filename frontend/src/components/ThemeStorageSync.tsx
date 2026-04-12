import { useEffect } from "react";
import { applyUiTheme, getStoredUiTheme, UI_THEME_STORAGE_KEY } from "../lib/uiTheme";

/** Re-applies theme after hydration and keeps other tabs in sync via storage events. */
export function ThemeStorageSync() {
  useEffect(() => {
    applyUiTheme(getStoredUiTheme());
    function onStorage(e: StorageEvent) {
      if (e.key !== UI_THEME_STORAGE_KEY) return;
      applyUiTheme(e.newValue === "light" ? "light" : "dark");
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);
  return null;
}
