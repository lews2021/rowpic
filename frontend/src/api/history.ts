/**
 * Path history persisted in localStorage.  Most-recent first, capped at 20.
 */
export interface HistoryEntry {
  path: string;
  lastUsed: number; // epoch ms
  scanCount: number; // how many times the user re-scanned it
}

const KEY = "rowpic.pathHistory";
const CAP = 20;

export function loadHistory(): HistoryEntry[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    if (!Array.isArray(arr)) return [];
    return arr
      .filter((e: any) => e && typeof e.path === "string")
      .slice(0, CAP)
      .map((e: any) => ({
        path: e.path,
        lastUsed: Number(e.lastUsed) || 0,
        scanCount: Number(e.scanCount) || 0,
      }));
  } catch {
    return [];
  }
}

export function saveHistory(entries: HistoryEntry[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(entries.slice(0, CAP)));
  } catch { /* ignore */ }
}

export function pushHistory(path: string): HistoryEntry[] {
  const now = Date.now();
  const cur = loadHistory();
  const existing = cur.find((e) => e.path === path);
  let next: HistoryEntry[];
  if (existing) {
    next = [
      { path, lastUsed: now, scanCount: existing.scanCount + 1 },
      ...cur.filter((e) => e.path !== path),
    ];
  } else {
    next = [{ path, lastUsed: now, scanCount: 1 }, ...cur];
  }
  next = next.slice(0, CAP);
  saveHistory(next);
  return next;
}

export function removeFromHistory(path: string): HistoryEntry[] {
  const next = loadHistory().filter((e) => e.path !== path);
  saveHistory(next);
  return next;
}

export function clearHistory(): void {
  saveHistory([]);
}