import { useT } from "../i18n";

interface Props {
  total: number;
  filtered: number;
  root: string;
  busy: boolean;
  error: string;
}

export default function StatusBar({ total, filtered, root, busy, error }: Props) {
  const t = useT();
  return (
    <div className="statusbar">
      <span className={`dot ${error ? "err" : busy ? "warn" : ""}`} />
      <span>{busy ? t("common.working") : t("common.ready")}</span>
      <span>· {t("status.shown", { filtered, total })}</span>
      <span style={{ flex: 1 }} />
      <span style={{ fontFamily: "ui-monospace, monospace" }}>{root}</span>
    </div>
  );
}