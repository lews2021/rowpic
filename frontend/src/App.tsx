import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import { pushHistory } from "./api/history";
import type { CategoryLabel, PhotoDetail, PhotoMeta } from "./api/types";
import { useLang, useT } from "./i18n";
import TopBar from "./components/TopBar";
import Sidebar from "./components/Sidebar";
import Stage from "./components/Stage";
import RightPanel from "./components/RightPanel";
import StatusBar from "./components/StatusBar";

export default function App() {
  const t = useT();
  const lang = useLang();
  const [root, setRoot] = useState<string>("");
  const [photos, setPhotos] = useState<PhotoMeta[]>([]);
  const [selected, setSelected] = useState<PhotoMeta | null>(null);
  const [detail, setDetail] = useState<PhotoDetail | null>(null);
  const [scanning, setScanning] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string>("");
  const [filter, setFilter] = useState<CategoryLabel | "all">("all");

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const handleScan = useCallback(async (path: string) => {
    setScanning(true);
    setError("");
    setRoot(path);
    setSelected(null);
    setDetail(null);
    try {
      const res = await api.scan(path, true);
      setPhotos(res.photos);
      // Record into history (most recent first, capped)
      pushHistory(path);
    } catch (e: any) {
      setError(t("error.scanFailed", { msg: e.message ?? e }));
      setPhotos([]);
    } finally {
      setScanning(false);
    }
  }, [t]);

  useEffect(() => {
    if (!selected) { setDetail(null); return; }
    setLoadingDetail(true);
    api.detail(selected.path)
      .then((d) => setDetail(d))
      .catch((e) => setError(t("error.detailFailed", { msg: e.message ?? e })))
      .finally(() => setLoadingDetail(false));
  }, [selected?.path, t]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (!photos.length) return;
      const idx = selected ? photos.findIndex((p) => p.id === selected.id) : -1;
      if (e.key === "ArrowDown" || e.key === "j") {
        e.preventDefault();
        const next = Math.min(photos.length - 1, idx + 1);
        setSelected(photos[Math.max(0, next)]);
      } else if (e.key === "ArrowUp" || e.key === "k") {
        e.preventDefault();
        const next = Math.max(0, idx - 1);
        setSelected(photos[next]);
      } else if (e.key === "Home") {
        e.preventDefault();
        setSelected(photos[0]);
      } else if (e.key === "End") {
        e.preventDefault();
        setSelected(photos[photos.length - 1]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [photos, selected]);

  const updatePhotos = (next: PhotoMeta[]) => setPhotos(next);

  const filteredPhotos = filter === "all"
    ? photos
    : photos.filter((p) => p.category === filter);

  return (
    <div className="app">
      <TopBar
        root={root}
        scanning={scanning}
        photos={photos}
        onScan={handleScan}
        onClassified={updatePhotos}
        onError={setError}
      />
      <div className="main">
        <Sidebar
          photos={filteredPhotos}
          total={photos.length}
          selected={selected}
          onSelect={setSelected}
          filter={filter}
          onFilter={setFilter}
        />
        <Stage
          selected={selected}
          detail={detail}
          loading={loadingDetail}
        />
        <RightPanel
          detail={detail}
          loading={loadingDetail}
        />
      </div>
      <StatusBar
        total={photos.length}
        filtered={filteredPhotos.length}
        root={root}
        busy={scanning || loadingDetail}
        error={error}
      />
      {error && <div className="toast" onClick={() => setError("")}>{error}</div>}
    </div>
  );
}