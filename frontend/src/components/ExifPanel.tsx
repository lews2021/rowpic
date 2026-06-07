import type { PhotoDetail } from "../api/types";
import { useT } from "../i18n";

interface Props { detail: PhotoDetail; }

function fmtDate(s: string | null | undefined, dash: string) {
  if (!s) return dash;
  try { return new Date(s).toLocaleString(); } catch { return s; }
}

export default function ExifPanel({ detail }: Props) {
  const t = useT();
  const x = detail.exif;
  const dash = t("common.dash");

  return (
    <>
      <div className="section">
        <h3>{t("exif.file")}</h3>
        <div className="kv">
          <div className="k">{t("exif.format")}</div><div className="v">{detail.format.toUpperCase()}</div>
          <div className="k">{t("exif.size")}</div><div className="v">{(detail.size / 1024 / 1024).toFixed(2)} MB</div>
          <div className="k">{t("exif.dimensions")}</div><div className="v">{detail.width} × {detail.height}</div>
          <div className="k">{t("exif.taken")}</div><div className="v">{fmtDate(x.taken_at, dash)}</div>
        </div>
      </div>
      <div className="section">
        <h3>{t("exif.cameraLens")}</h3>
        <div className="kv">
          <div className="k">{t("exif.make")}</div><div className="v">{x.make ?? dash}</div>
          <div className="k">{t("exif.model")}</div><div className="v">{x.model ?? dash}</div>
          <div className="k">{t("exif.lens")}</div><div className="v">{x.lens ?? x.lens_model ?? dash}</div>
          <div className="k">{t("exif.focal")}</div><div className="v">
            {x.focal_length != null ? t("exif.focalMm", { n: x.focal_length }) : dash}
            {x.focal_length_35mm ? ` ${t("exif.focalEquiv", { n: x.focal_length_35mm })}` : ""}
          </div>
          <div className="k">{t("exif.software")}</div><div className="v">{x.software ?? dash}</div>
        </div>
      </div>
      <div className="section">
        <h3>{t("exif.exposure")}</h3>
        <div className="kv">
          <div className="k">{t("exif.aperture")}</div><div className="v">{x.aperture != null ? t("exif.apertureVal", { n: x.aperture }) : dash}</div>
          <div className="k">{t("exif.shutter")}</div><div className="v">{x.shutter ?? dash}</div>
          <div className="k">{t("exif.iso")}</div><div className="v">{x.iso ?? dash}</div>
          <div className="k">{t("exif.program")}</div><div className="v">{x.exposure_program ?? dash}</div>
          <div className="k">{t("exif.wb")}</div><div className="v">{x.white_balance ?? dash}</div>
          <div className="k">{t("exif.flash")}</div><div className="v">{x.flash == null ? dash : (x.flash ? t("common.yes") : t("common.no"))}</div>
        </div>
      </div>
      {Object.keys(x.raw_extras ?? {}).length > 0 && (
        <div className="section">
          <h3>{t("exif.rawExtras")}</h3>
          <div className="kv">
            {Object.entries(x.raw_extras).map(([k, v]) => (
              <div key={k} style={{ display: "contents" }}>
                <div className="k">{k}</div>
                <div className="v">{String(v).slice(0, 60)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}