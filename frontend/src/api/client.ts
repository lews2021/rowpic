import type {
  PhotoDetail, PhotoMeta, ScanResult,
  ColorAdjustRequest, ColorAdjustResult,
  ClassifyRequest, ClassifyResult,
} from "./types";

const BASE = ""; // proxied through Vite to backend

async function json<T>(resp: Response): Promise<T> {
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

export const api = {
  info: () => fetch(`${BASE}/api/info`).then((r) => json<any>(r)),

  scan: (root: string, recursive = true) =>
    fetch(`${BASE}/api/photos/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ root, recursive, include_hidden: false }),
    }).then((r) => json<ScanResult>(r)),

  detail: (path: string) => {
    const q = new URLSearchParams({ path });
    return fetch(`${BASE}/api/photos/detail?${q.toString()}`).then((r) => json<PhotoDetail>(r));
  },

  thumbUrl: (path: string) => {
    const q = new URLSearchParams({ path });
    return `${BASE}/api/photos/thumb?${q.toString()}`;
  },

  previewUrl: (path: string, maxDim = 0) => {
    const q = new URLSearchParams({ path });
    if (maxDim) q.set("max_dim", String(maxDim));
    return `${BASE}/api/photos/preview?${q.toString()}`;
  },

  rawUrl: (path: string, maxDim = 0) => {
    const q = new URLSearchParams({ path });
    if (maxDim) q.set("max_dim", String(maxDim));
    return `${BASE}/api/photos/raw?${q.toString()}`;
  },

  colorAdjust: (imagePath: string, params: ColorAdjustRequest) =>
    fetch(`${BASE}/api/color/adjust_path`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image_path: imagePath, ...params }),
    }).then((r) => json<ColorAdjustResult>(r)),

  classify: (photos: PhotoMeta[], req: ClassifyRequest) =>
    fetch(`${BASE}/api/classify/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...req, photos }),
    }).then((r) => json<ClassifyResult>(r)),
};
