import { useState } from "react";
import { clearHistory, loadHistory, removeFromHistory, type HistoryEntry } from "../api/history";
import { useT } from "../i18n";

interface Props {
  onPick: (path: string) => void;
  onClose: () => void;
}

function fmtAgo(ms: number, t: (k: string, p?: any) => string): string {
  if (!ms) return t("history.never");
  const diff = Date.now() - ms;
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return t("history.justNow");
  const min = Math.floor(sec / 60);
  if (min < 60) return t("history.minutesAgo", { n: min });
  const hr = Math.floor(min / 60);
  if (hr < 24) return t("history.hoursAgo", { n: hr });
  const day = Math.floor(hr / 24);
  if (day < 30) return t("history.daysAgo", { n: day });
  return new Date(ms).toLocaleDateString();
}

export default function HistoryList({ onPick, onClose }: Props) {
  const t = useT();
  const [items, setItems] = useState<HistoryEntry[]>(() => loadHistory());
  const [confirmClear, setConfirmClear] = useState(false);

  const remove = (p: string) => setItems(removeFromHistory(p));
  const clear = () => { clearHistory(); setItems([]); setConfirmClear(false); };

  return (
    <div className="history-panel" onClick={(e) => e.stopPropagation()}>
      <div className="hp-toolbar">
        <span style={{ color: "var(--fg-1)", fontSize: 12 }}>{t("history.title")}</span>
        <span style={{ flex: 1 }} />
        {items.length > 0 && (
          confirmClear ? (
            <>
              <span style={{ fontSize: 10, color: "var(--warn)" }}>{t("history.confirmClear")}</span>
              <button className="ghost small" onClick={() => setConfirmClear(false)}>{t("common.cancel")}</button>
              <button className="danger small" onClick={clear}>{t("common.confirm")}</button>
            </>
          ) : (
            <button className="ghost small" onClick={() => setConfirmClear(true)}>{t("history.clear")}</button>
          )
        )}
        <button className="ghost small" onClick={onClose}>×</button>
      </div>
      {items.length === 0 ? (
        <div className="empty">{t("history.empty")}</div>
      ) : (
        <div className="hp-list">
          {items.map((it) => (
            <div key={it.path} className="hp-row" onClick={() => onPick(it.path)}>
              <div className="hp-icon">📂</div>
              <div className="hp-meta">
                <div className="hp-path" title={it.path}>{it.path}</div>
                <div className="hp-sub">
                  {fmtAgo(it.lastUsed, t)} · {t("history.usedTimes", { n: it.scanCount })}
                </div>
              </div>
              <button
                className="hp-remove"
                onClick={(e) => { e.stopPropagation(); remove(it.path); }}
                title={t("history.remove")}
              >×</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}