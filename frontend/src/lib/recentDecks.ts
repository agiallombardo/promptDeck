const STORAGE_KEY = "promptdeck_recent_decks_v1";
const MAX_RECENT = 4;

export type RecentDeckEntry = {
  id: string;
  title: string;
  at: number;
};

export const RECENT_DECKS_CHANGED = "promptdeck-recent-decks";

export function readRecentDecks(): RecentDeckEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    const out: RecentDeckEntry[] = [];
    for (const x of parsed) {
      if (
        x !== null &&
        typeof x === "object" &&
        typeof (x as RecentDeckEntry).id === "string" &&
        typeof (x as RecentDeckEntry).title === "string"
      ) {
        const at = (x as RecentDeckEntry).at;
        out.push({
          id: (x as RecentDeckEntry).id,
          title: (x as RecentDeckEntry).title,
          at: typeof at === "number" ? at : 0,
        });
      }
    }
    return out.slice(0, MAX_RECENT);
  } catch {
    return [];
  }
}

/** Remember a deck as recently opened (most recent first, max 4). */
export function recordRecentDeck(id: string, title: string): void {
  const trimmed = title.trim() || "Untitled deck";
  const prev = readRecentDecks().filter((e) => e.id !== id);
  const next: RecentDeckEntry[] = [{ id, title: trimmed, at: Date.now() }, ...prev].slice(
    0,
    MAX_RECENT,
  );
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  window.dispatchEvent(new CustomEvent(RECENT_DECKS_CHANGED));
}

export function removeRecentDeck(id: string): void {
  const prev = readRecentDecks();
  const next = prev.filter((e) => e.id !== id);
  if (next.length === prev.length) return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  window.dispatchEvent(new CustomEvent(RECENT_DECKS_CHANGED));
}
