import { useEffect, useRef } from "react";
import type { PhotoDetail } from "../api/types";
import { useT } from "../i18n";

interface Props { detail: PhotoDetail; }

export default function HistogramPanel({ detail }: Props) {
  const t = useT();
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (w === 0) return;
    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr; canvas.height = h * dpr;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const hist = detail.histogram;
    if (!hist) return;
    const bins = hist.luminance.length;
    const max = Math.max(1,
      ...hist.luminance,
      ...hist.red,
      ...hist.green,
      ...hist.blue);

    const drawChannel = (data: number[], color: string) => {
      ctx.beginPath();
      ctx.fillStyle = color;
      for (let i = 0; i < bins; i++) {
        const x = (i / (bins - 1)) * w;
        const y = h - (data[i] / max) * h;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.lineTo(w, h);
      ctx.lineTo(0, h);
      ctx.closePath();
      ctx.fill();
    };

    drawChannel(hist.red, "rgba(255,80,80,0.45)");
    drawChannel(hist.green, "rgba(80,200,120,0.45)");
    drawChannel(hist.blue, "rgba(80,140,255,0.45)");
    drawChannel(hist.luminance, "rgba(255,255,255,0.55)");

    if (hist.clip_high > 0.005) {
      ctx.fillStyle = "rgba(255,107,107,0.5)";
      ctx.fillRect(w - 4, 0, 4, h);
    }
    if (hist.clip_low > 0.005) {
      ctx.fillStyle = "rgba(116,143,252,0.5)";
      ctx.fillRect(0, 0, 4, h);
    }
  }, [detail]);

  return (
    <>
      <div className="section">
        <h3>{t("hist.title")}</h3>
        <canvas ref={ref} className="histogram-canvas" style={{ width: "100%", height: 110 }} />
        <div style={{ display: "flex", gap: 8, marginTop: 6, fontSize: 10, color: "var(--fg-2)" }}>
          <span style={{ color: "rgba(255,80,80,0.9)" }}>● R</span>
          <span style={{ color: "rgba(80,200,120,0.9)" }}>● G</span>
          <span style={{ color: "rgba(80,140,255,0.9)" }}>● B</span>
          <span style={{ color: "rgba(255,255,255,0.9)" }}>● Lum</span>
        </div>
      </div>
      {detail.histogram && (
        <div className="section">
          <h3>{t("hist.clipping")}</h3>
          <div className="kv">
            <div className="k">{t("hist.highlights")}</div>
            <div className="v" style={{ color: detail.histogram.clip_high > 0.01 ? "var(--danger)" : undefined }}>
              {(detail.histogram.clip_high * 100).toFixed(2)}%
            </div>
            <div className="k">{t("hist.shadows")}</div>
            <div className="v" style={{ color: detail.histogram.clip_low > 0.01 ? "var(--warn)" : undefined }}>
              {(detail.histogram.clip_low * 100).toFixed(2)}%
            </div>
          </div>
        </div>
      )}
    </>
  );
}