import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ColorAdjustRequest, PhotoDetail } from "../api/types";
import { useT } from "../i18n";

interface Props { detail: PhotoDetail; }

interface SliderProps {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  format?: (v: number) => string;
  onChange: (v: number) => void;
}

function Slider({ label, min, max, step, value, format, onChange }: SliderProps) {
  return (
    <div className="slider-row">
      <div className="lbl">{label}</div>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
      <div className="val">{format ? format(value) : value.toFixed(2)}</div>
    </div>
  );
}

const ZERO: Required<Pick<ColorAdjustRequest,
  "exposure" | "contrast" | "saturation" | "vibrance" | "temperature" | "tint" |
  "highlights" | "shadows" | "whites" | "blacks">> = {
  exposure: 0, contrast: 1, saturation: 1, vibrance: 0,
  temperature: 0, tint: 0, highlights: 0, shadows: 0, whites: 0, blacks: 0,
};

export default function ColorPanel({ detail }: Props) {
  const t = useT();
  const [params, setParams] = useState<typeof ZERO>({ ...ZERO });
  const [auto, setAuto] = useState(false);
  const [aiMode, setAiMode] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [applied, setApplied] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    setParams({ ...ZERO });
    setAuto(false);
    setAiMode(false);
    setPreview(null);
    setApplied(null);
    setError("");
  }, [detail.path]);

  const set = <K extends keyof typeof ZERO>(k: K, v: number) => setParams((p) => ({ ...p, [k]: v }));

  const runAdjust = async (extra: Partial<ColorAdjustRequest> = {}) => {
    setBusy(true); setError("");
    try {
      const req: ColorAdjustRequest = {
        exposure: params.exposure,
        contrast: params.contrast,
        saturation: params.saturation,
        vibrance: params.vibrance,
        temperature: params.temperature,
        tint: params.tint,
        highlights: params.highlights,
        shadows: params.shadows,
        whites: params.whites,
        blacks: params.blacks,
        auto,
        ai: aiMode,
        ...extra,
      };
      const res = await api.colorAdjust(detail.path, req);
      setPreview(`data:image/png;base64,${res.image_b64}`);
      setApplied(res.applied);
    } catch (e: any) {
      setError(e.message ?? String(e));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    const tm = setTimeout(() => {
      if (preview) runAdjust();
    }, 250);
    return () => clearTimeout(tm);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params, auto, aiMode, detail.path]);

  const evFormat = (v: number) => t("color.evFmt", { sign: v >= 0 ? "+" : "", n: Math.abs(v).toFixed(2) });

  return (
    <>
      <div className="section">
        <h3>{t("color.light")}</h3>
        <Slider label={t("color.exposure")} min={-3} max={3} step={0.05} value={params.exposure}
          format={evFormat}
          onChange={(v) => set("exposure", v)} />
        <Slider label={t("color.contrast")} min={0.5} max={2} step={0.01} value={params.contrast}
          onChange={(v) => set("contrast", v)} />
        <Slider label={t("color.highlights")} min={-1} max={1} step={0.01} value={params.highlights}
          onChange={(v) => set("highlights", v)} />
        <Slider label={t("color.shadows")} min={-1} max={1} step={0.01} value={params.shadows}
          onChange={(v) => set("shadows", v)} />
        <Slider label={t("color.whites")} min={-1} max={1} step={0.01} value={params.whites}
          onChange={(v) => set("whites", v)} />
        <Slider label={t("color.blacks")} min={-1} max={1} step={0.01} value={params.blacks}
          onChange={(v) => set("blacks", v)} />
      </div>

      <div className="section">
        <h3>{t("color.colorSection")}</h3>
        <Slider label={t("color.saturation")} min={0} max={2} step={0.01} value={params.saturation}
          onChange={(v) => set("saturation", v)} />
        <Slider label={t("color.vibrance")} min={-1} max={1} step={0.01} value={params.vibrance}
          onChange={(v) => set("vibrance", v)} />
        <Slider label={t("color.temperature")} min={-100} max={100} step={1} value={params.temperature}
          onChange={(v) => set("temperature", v)} />
        <Slider label={t("color.tint")} min={-100} max={100} step={1} value={params.tint}
          onChange={(v) => set("tint", v)} />
      </div>

      <div className="section">
        <h3>{t("color.oneClick")}</h3>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <button
            className={auto ? "primary" : ""}
            onClick={() => { setAuto(!auto); if (aiMode) setAiMode(false); }}
          >{t("color.auto")}</button>
          <button
            className={aiMode ? "primary" : ""}
            onClick={() => { setAiMode(!aiMode); if (auto) setAuto(false); }}
            title={t("color.aiTitle")}
          >✨ {t("color.ai")}</button>
          <button className="ghost" onClick={() => { setParams({ ...ZERO }); setAuto(false); setAiMode(false); setPreview(null); setApplied(null); }}>{t("color.reset")}</button>
        </div>
      </div>

      <div className="section">
        <h3>{t("color.preview")} {busy && <span className="spinner" style={{ marginLeft: 6 }} />}</h3>
        <div className="color-preview">
          {preview ? (
            <img src={preview} alt="color preview" />
          ) : (
            <div style={{ padding: 30, textAlign: "center", color: "var(--fg-2)", fontSize: 11 }}>
              {t("color.previewHint")}
            </div>
          )}
        </div>
        {applied && (
          <div style={{ fontSize: 10, color: "var(--fg-2)", marginTop: 6 }}>
            {t("color.applied", { list: Object.entries(applied).map(([k, v]) => `${k}=${v}`).join(", ") })}
          </div>
        )}
        {error && <div style={{ fontSize: 11, color: "var(--danger)", marginTop: 6 }}>{error}</div>}
      </div>

      <div className="section" style={{ fontSize: 10, color: "var(--fg-2)" }}>
        {t("color.aiHelp")}
      </div>
    </>
  );
}