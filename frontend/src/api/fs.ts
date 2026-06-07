/**
 * Filesystem browser API.  Used by the PathPicker to build the tree.
 */
export interface DirEntry {
  name: string;
  path: string;
  has_children: boolean;
}

export interface DirListing {
  path: string;
  parent: string | null;
  dirs: DirEntry[];
  file_count: number;
  total: number;
}

async function jsonOrThrow<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let msg = `${resp.status} ${resp.statusText}`;
    try {
      const j = await resp.json();
      msg = j.detail ?? msg;
    } catch { /* ignore */ }
    throw new Error(msg);
  }
  return resp.json() as Promise<T>;
}

export const fs = {
  roots: () => fetch(`/api/fs/roots`).then((r) => jsonOrThrow<string[]>(r)),

  list: (path: string) => {
    const q = new URLSearchParams({ path });
    return fetch(`/api/fs/list?${q.toString()}`).then((r) => jsonOrThrow<DirListing>(r));
  },
};