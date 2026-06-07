import { useEffect, useRef } from "react";
import { api } from "../api/client";
import type { CategoryLabel, PhotoMeta } from "../api/types";
import { useT } from "../i18n";

interface Props {
  photos: PhotoMeta[];
  total: number;
  selected: PhotoMeta | null;
  onSelect: (p: PhotoMeta) => void;
  filter: CategoryLabel | "all";
  onFilter: (f: CategoryLabel | "all") => void;
}

const CATEGORIES: { key: CategoryLabel | "all" }[] = [
  { key: "all" },
  { key: "blurry_face" },
  { key: "blurry" },
  { key: "underexposed" },
  { key: "overexposed" },
  { key: "keep" },
];

const CATEGORY_BADGE: Record<string, { cls: string; labelKey: string }> = {
  keep:           { cls: "sharp",  labelKey: "category.keep" },
  blurry:         { cls: "blurry", labelKey: "category.blurry" },
  blurry_face:    { cls: "face-blur", labelKey: "category.blurry_face" },
  underexposed:   { cls: "underexposed", labelKey: "category.underexposed" },
  overexposed:    { cls: "overexposed",  labelKey: "category.overexposed" },
  duplicate:      { cls: "blurry", labelKey: "category.duplicate" },
  unclassified:   { cls: "",       labelKey: "category.unclassified" },
};

function fmtSize(n: number, t: (k: string) => string) {
  if (n < 1024) return `${n}${t("generic.byte")}`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)}${t("generic.kb")}`;
  return `${(n / 1024 / 1024).toFixed(1)}${t("generic.mb")}`;
}

export default function Sidebar({ photos, total, selected, onSelect, filter, onFilter }: Props) {
  const t = useT();
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!selected) return;
    const el = listRef.current?.querySelector(`[data-pid="${CSS.escape(selected.id)}"]`);
    if (el && "scrollIntoView" in el) (el as HTMLElement).scrollIntoView({ block: "nearest" });
  }, [selected?.id]);

  return (
    <div className="sidebar">
      <div className="toolbar">
        <span style={{ flex: 1, color: "var(--fg-2)", fontSize: 11 }}>
          {t("sidebar.count", { filtered: photos.length, total })}
        </span>
        <span style={{ color: "var(--fg-2)", fontSize: 10 }}>
          <span className="badge raw">RAW</span> = {t("sidebar.rawHint").replace(/^RAW = /, "")}
        </span>
      </div>
      <div className="filter">
        {CATEGORIES.map((c) => (
          <div
            key={c.key}
            className={`chip ${filter === c.key ? "active" : ""}`}
            onClick={() => onFilter(c.key)}
          >
            {t(`sidebar.category.${c.key === "all" ? "all" : c.key}`)}
          </div>
        ))}
      </div>
      <div className="photo-list" ref={listRef}>
        {photos.length === 0 ? (
          <div className="empty">{t("sidebar.empty")}</div>
        ) : (
          photos.map((p) => {
            const cat = CATEGORY_BADGE[p.category ?? "unclassified"] || CATEGORY_BADGE.unclassified;
            const catLabel = t(cat.labelKey);
            return (
              <div
                key={p.id}
                data-pid={p.id}
                className={`photo-item ${selected?.id === p.id ? "active" : ""}`}
                onClick={() => onSelect(p)}
              >
                <div className="thumb">
                  <img src={api.thumbUrl(p.path)} alt="" loading="lazy" />
                </div>
                <div className="meta">
                  <div className="name">
                    {p.format === "raw" && <span className="badge raw">RAW</span>}
                    {catLabel && <span className={`badge ${cat.cls}`}>{catLabel}</span>}
                    <span className="fname" title={p.path}>{p.name}</span>
                  </div>
                  <div className="sub">
                    {p.width && p.height ? `${p.width}×${p.height} · ` : ""}
                    {fmtSize(p.size, t)}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}