import { useEffect, useRef, useState } from "react";
import { useT } from "../i18n";
import FolderTree from "./FolderTree";
import HistoryList from "./HistoryList";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onScan: () => void;
  onPick: (path: string) => void;
  onError: (msg: string) => void;
}

/**
 * Top-bar path picker: input + browse button + history button.
 * Clicking "browse" opens a tree-style folder picker; clicking "history"
 * opens a list of recent paths.  The active panel can be closed by clicking
 * the backdrop or pressing Escape.
 */
export default function PathPicker({ value, onChange, onScan, onPick, onError }: Props) {
  const t = useT();
  const [panel, setPanel] = useState<"tree" | "history" | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!panel) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPanel(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [panel]);

  // Close on outside click
  useEffect(() => {
    if (!panel) return;
    const onDown = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (target.closest(".path-picker-panel")) return;
      setPanel(null);
    };
    window.addEventListener("mousedown", onDown);
    return () => window.removeEventListener("mousedown", onDown);
  }, [panel]);

  const handleTreeSelect = (p: string) => {
    setPanel(null);
    onChange(p);
    onPick(p);
  };

  return (
    <div className="path-picker">
      <input
        ref={inputRef}
        className="path-input"
        placeholder={t("topbar.placeholder")}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") { setPanel(null); onScan(); }
        }}
        onFocus={() => setPanel(null)}
      />
      <button
        className={`pp-btn ${panel === "tree" ? "active" : ""}`}
        onClick={() => setPanel(panel === "tree" ? null : "tree")}
        title={t("picker.browse")}
      >📁 {t("picker.browse")}</button>
      <button
        className={`pp-btn ${panel === "history" ? "active" : ""}`}
        onClick={() => setPanel(panel === "history" ? null : "history")}
        title={t("history.title")}
      >🕐 {t("history.title")}</button>
      {panel === "tree" && (
        <div className="path-picker-panel tree-panel">
          <FolderTree
            initialPath={value}
            onSelect={handleTreeSelect}
            onCancel={() => setPanel(null)}
          />
        </div>
      )}
      {panel === "history" && (
        <div className="path-picker-panel history-panel-wrap">
          <HistoryList
            onPick={(p) => { setPanel(null); onChange(p); onPick(p); }}
            onClose={() => setPanel(null)}
          />
        </div>
      )}
    </div>
  );
}