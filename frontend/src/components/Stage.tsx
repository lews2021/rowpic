import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { PhotoDetail, PhotoMeta } from "../api/types";
import { useT } from "../i18n";
import CompositionOverlayCanvas from "./CompositionOverlay";

interface Props {
  selected: PhotoMeta | null;
  detail: PhotoDetail | null;
  loading: boolean;
}

export default function Stage({ selected, detail, loading }: Props) {
  const t = useT();
  const wrapRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [natural, setNatural] = useState({ w: 0, h: 0 });

  useLayoutEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const rect = el.getBoundingClientRect();
      setSize({ w: rect.width, h: rect.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    const img = imgRef.current;
    if (!img) return;
    if (img.complete && img.naturalWidth > 0) {
      setNatural({ w: img.naturalWidth, h: img.naturalHeight });
    }
  }, [selected?.path]);

  const showSpinner = loading && selected;

  return (
    <div className="stage">
      <div className="stage-toolbar">
        {selected ? (
          <>
            <span style={{ color: "var(--fg-1)" }}>{selected.name}</span>
            <span style={{ color: "var(--fg-2)", fontSize: 11 }}>
              {detail ? `${detail.width}×${detail.height}` : ""}
            </span>
            <span style={{ flex: 1 }} />
            <span style={{ color: "var(--fg-2)", fontSize: 11 }}>
              {t("stage.hint")}
            </span>
          </>
        ) : (
          <span style={{ color: "var(--fg-2)" }}>{t("stage.empty")}</span>
        )}
      </div>
      <div className="stage-canvas-wrap" ref={wrapRef}>
        {!selected ? (
          <div className="empty">
            <div className="icon">🖼</div>
            <div>{t("stage.empty")}</div>
          </div>
        ) : (
          <>
            {detail && (
              <img
                ref={imgRef}
                className="preview"
                src={api.previewUrl(selected.path, 0)}
                alt={selected.name}
                onLoad={(e) => {
                  const img = e.currentTarget;
                  setNatural({ w: img.naturalWidth, h: img.naturalHeight });
                }}
              />
            )}
            {!detail && showSpinner && <div className="empty"><span className="spinner" /> {t("right.loading")}</div>}
            {detail && (
              <CompositionOverlayCanvas
                width={size.w}
                height={size.h}
                imageNaturalWidth={natural.w}
                imageNaturalHeight={natural.h}
                faces={detail.focus?.faces ?? []}
              />
            )}
          </>
        )}
      </div>
      <div className="stage-info">
        <span>{selected ? `${selected.width || natural.w} × ${selected.height || natural.h}` : ""}</span>
        <span style={{ flex: 1 }} />
        <span>{detail?.focus ? `${detail.focus.overall_sharpness.toFixed(1)} · ${detail.focus.overall_quality}` : ""}</span>
      </div>
    </div>
  );
}