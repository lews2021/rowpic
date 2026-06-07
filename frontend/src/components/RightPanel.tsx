import { useState } from "react";
import type { PhotoDetail } from "../api/types";
import { useT } from "../i18n";
import ExifPanel from "./ExifPanel";
import HistogramPanel from "./HistogramPanel";
import FocusPanel from "./FocusPanel";
import ColorPanel from "./ColorPanel";

interface Props {
  detail: PhotoDetail | null;
  loading: boolean;
}

type Tab = "info" | "hist" | "focus" | "color";

export default function RightPanel({ detail, loading }: Props) {
  const t = useT();
  const [tab, setTab] = useState<Tab>("info");

  return (
    <div className="panel">
      <div className="tabs">
        {(["info", "hist", "focus", "color"] as Tab[]).map((tk) => (
          <div
            key={tk}
            className={`tab ${tab === tk ? "active" : ""}`}
            onClick={() => setTab(tk)}
          >
            {tk === "info" ? t("tab.exif")
              : tk === "hist" ? t("tab.hist")
              : tk === "focus" ? t("tab.focus")
              : t("tab.color")}
          </div>
        ))}
      </div>
      <div className="content">
        {!detail ? (
          <div className="empty">{t("right.noPhoto")}</div>
        ) : loading ? (
          <div className="empty"><span className="spinner" /> {t("right.loading")}</div>
        ) : tab === "info" ? (
          <ExifPanel detail={detail} />
        ) : tab === "hist" ? (
          <HistogramPanel detail={detail} />
        ) : tab === "focus" ? (
          <FocusPanel detail={detail} />
        ) : (
          <ColorPanel detail={detail} />
        )}
      </div>
    </div>
  );
}