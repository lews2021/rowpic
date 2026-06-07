import type { PhotoDetail } from "../api/types";
import { useT } from "../i18n";

interface Props { detail: PhotoDetail; }

export default function FocusPanel({ detail }: Props) {
  const t = useT();
  const f = detail.focus;
  if (!f) return <div className="empty">{t("focus.noData")}</div>;
  return (
    <>
      <div className="section">
        <h3>{t("focus.overall")}</h3>
        <div className="focus-card">
          <div className="box">
            <div className="k">{t("focus.laplacian")}</div>
            <div className="v">{f.overall_sharpness.toFixed(1)}</div>
          </div>
          <div className="box">
            <div className="k">{t("focus.quality")}</div>
            <div className={`v quality-${f.overall_quality}`}>{f.overall_quality}</div>
          </div>
          <div className="box">
            <div className="k">{t("focus.exposure")}</div>
            <div className="v">{(f.exposure ?? 0).toFixed(2)}</div>
          </div>
          <div className="box">
            <div className="k">{t("focus.backlit")}</div>
            <div className="v">{f.is_backlit ? t("common.yes") : t("common.no")}</div>
          </div>
        </div>
      </div>
      {f.faces.length > 0 && (
        <div className="section face-list">
          <h3>{t("focus.faces", { n: f.faces.length })}</h3>
          {f.faces.map((face, i) => (
            <div key={i} className="face-row">
              <span>#{i + 1} ({face.w}×{face.h})</span>
              <span style={{ fontFamily: "ui-monospace, monospace" }}>{face.sharpness.toFixed(1)}</span>
              <span className={`quality-${face.quality}`}>{face.quality}</span>
            </div>
          ))}
        </div>
      )}
      {f.blur_map_thumb && (
        <div className="section">
          <h3>{t("focus.heatmap")}</h3>
          <img className="heatmap-img" src={`data:image/png;base64,${f.blur_map_thumb}`} alt="focus heatmap" />
        </div>
      )}
    </>
  );
}