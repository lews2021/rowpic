import { useState } from "react";
import { api } from "../api/client";
import type { ClassifyRequest, PhotoMeta } from "../api/types";
import { LANG_LABELS, SUPPORTED_LANGS, setLanguage, useLang, useT } from "../i18n";
import type { Lang } from "../i18n";

interface Props {
  root: string;
  scanning: boolean;
  photos: PhotoMeta[];
  onScan: (path: string) => void;
  onClassified: (next: PhotoMeta[]) => void;
  onError: (msg: string) => void;
}

const QUICK_PATHS = [
  "C:\\Users\\Public\\Pictures",
  "C:\\Users\\liws\\Pictures",
];

export default function TopBar({ root, scanning, photos, onScan, onClassified, onError }: Props) {
  const t = useT();
  const lang = useLang();
  const [pathInput, setPathInput] = useState("");
  const [classifying, setClassifying] = useState(false);

  const handleScan = () => {
    if (!pathInput.trim() && !root) {
      onError(t("error.enterPath"));
      return;
    }
    onScan(pathInput.trim() || root);
  };

  const handleClassify = async () => {
    if (!photos.length) {
      onError(t("error.noPhotos"));
      return;
    }
    setClassifying(true);
    try {
      const req: ClassifyRequest = {
        rules: ["blurry_face", "blurry", "exposure"],
        move: false,
        dest_template: "{category}/{name}",
      };
      const result = await api.classify(photos, req);
      const next = photos.map((p) => {
        const newPath = result.moves.find((m) => m.src === p.path)?.dest ?? p.path;
        const newCat = (result.per_photo[p.path] ?? result.per_photo[newPath] ?? p.category) as PhotoMeta["category"];
        return { ...p, path: newPath, category: newCat };
      });
      onClassified(next);
      const summary = Object.entries(result.categories)
        .map(([k, v]) => `${k}=${v}`).join(", ");
      onError(t("summary.classified", { total: result.total, breakdown: summary }));
    } catch (e: any) {
      onError(t("error.classifyFailed", { msg: e.message ?? e }));
    } finally {
      setClassifying(false);
    }
  };

  const switchLang = (newLang: Lang) => {
    if (newLang === lang) return;
    setLanguage(newLang);
  };

  return (
    <div className="topbar">
      <div className="brand">rowpic</div>
      <input
        style={{ width: 360 }}
        placeholder={t("topbar.placeholder")}
        value={pathInput}
        onChange={(e) => setPathInput(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleScan()}
        list="quick-paths"
      />
      <datalist id="quick-paths">
        {QUICK_PATHS.map((p) => <option key={p} value={p} />)}
      </datalist>
      <button className="primary" onClick={handleScan} disabled={scanning}>
        {scanning ? <><span className="spinner" /> {t("topbar.scanning")}</> : t("topbar.scan")}
      </button>
      <button onClick={handleClassify} disabled={classifying || !photos.length}>
        {classifying ? <><span className="spinner" /> {t("topbar.classifying")}</> : t("topbar.classify")}
      </button>
      <div className="path">{root || t("topbar.noFolder")}</div>
      <div style={{ flex: 1 }} />
      <div className="lang-switch" title={t("topbar.lang.label")}>
        {SUPPORTED_LANGS.map((l) => (
          <button
            key={l}
            className={`lang-btn ${lang === l ? "active" : ""}`}
            onClick={() => switchLang(l)}
          >
            {LANG_LABELS[l]}
          </button>
        ))}
      </div>
    </div>
  );
}