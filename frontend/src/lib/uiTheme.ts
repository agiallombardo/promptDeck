export const UI_THEME_STORAGE_KEY = "promptdeck-ui-theme";

export type UiTheme = "dark" | "light";

export function getStoredUiTheme(): UiTheme {
  try {
    const v = localStorage.getItem(UI_THEME_STORAGE_KEY);
    if (v === "light") return "light";
  } catch {
    /* ignore */
  }
  return "dark";
}

export function applyUiTheme(theme: UiTheme): void {
  const root = document.documentElement;
  if (theme === "light") {
    root.classList.add("light");
  } else {
    root.classList.remove("light");
  }
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) {
    meta.setAttribute("content", theme === "light" ? "#f2f4f8" : "#050507");
  }
}

export function setUiTheme(theme: UiTheme): void {
  try {
    localStorage.setItem(UI_THEME_STORAGE_KEY, theme);
  } catch {
    /* ignore */
  }
  applyUiTheme(theme);
}
