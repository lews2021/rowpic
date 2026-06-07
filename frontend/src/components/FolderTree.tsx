import { useCallback, useEffect, useRef, useState } from "react";
import { fs } from "../api/fs";
import type { DirEntry, DirListing } from "../api/fs";
import { useT } from "../i18n";

interface Props {
  initialPath?: string;
  onSelect: (path: string) => void;
  onCancel: () => void;
}

interface NodeState {
  listing?: DirListing;
  loading: boolean;
  loaded: boolean;
  error?: string;
  expanded: boolean;
}

function emptyNode(): NodeState {
  return { loading: false, loaded: false, expanded: false };
}

export default function FolderTree({ initialPath, onSelect, onCancel }: Props) {
  const t = useT();
  const [roots, setRoots] = useState<string[]>([]);
  const [path, setPath] = useState<string>(initialPath || "");
  const [nodes, setNodes] = useState<Record<string, NodeState>>({});
  const [rootsError, setRootsError] = useState<string>("");
  const inflight = useRef<Record<string, Promise<void>>>({});

  // Initial load: roots
  useEffect(() => {
    fs.roots()
      .then((rs) => {
        setRoots(rs);
        if (!path && rs[0]) setPath(rs[0]);
      })
      .catch((e) => setRootsError(String(e.message ?? e)));
  }, []);

  const ensureLoaded = useCallback((p: string): Promise<void> => {
    const existing = inflight.current[p];
    if (existing) return existing;
    setNodes((n) => ({ ...n, [p]: { ...(n[p] || emptyNode()), loading: true, error: undefined } }));
    const pr = fs.list(p)
      .then((listing) => {
        setNodes((n) => ({ ...n, [p]: { ...(n[p] || emptyNode()), listing, loading: false, loaded: true, error: undefined } }));
      })
      .catch((e) => {
        setNodes((n) => ({ ...n, [p]: { ...(n[p] || emptyNode()), loading: false, loaded: true, error: String(e.message ?? e) } }));
      });
    inflight.current[p] = pr;
    pr.finally(() => { delete inflight.current[p]; });
    return pr;
  }, []);

  // Whenever the current path changes, ensure it's loaded and expanded
  useEffect(() => {
    if (!path) return;
    ensureLoaded(path)
      .then(() => {
        setNodes((n) => ({ ...n, [path]: { ...(n[path] || emptyNode()), expanded: true } }));
      })
      .catch(() => {});
  }, [path, ensureLoaded]);

  const lookupNode = useCallback((p: string) => nodes[p], [nodes]);

  const toggle = (p: string) => {
    const cur = nodes[p] || emptyNode();
    const willExpand = !cur.expanded;
    setNodes((n) => ({ ...n, [p]: { ...cur, expanded: willExpand } }));
    if (willExpand && !cur.loaded) ensureLoaded(p);
  };

  const segments = path ? splitPath(path) : [];

  const navigateTo = (idx: number) => {
    if (!path) return;
    const sep = path.includes("\\") ? "\\" : "/";
    const parts = splitPath(path);
    if (idx < 0) {
      // up to parent
      const pp = parentPath(path);
      if (pp) setPath(pp);
      return;
    }
    const newPath = parts.slice(0, idx + 1).join(sep);
    setPath(newPath);
  };

  return (
    <div className="folder-tree" onClick={(e) => e.stopPropagation()}>
      <div className="ft-toolbar">
        <div className="ft-breadcrumb">
          {segments.length === 0 ? (
            <span style={{ color: "var(--fg-2)" }}>{t("picker.selectFolder")}</span>
          ) : (
            <>
              <span className="crumb" onClick={() => parentPath(path) && setPath(parentPath(path)!)} title={t("picker.up")}>↑</span>
              {segments.map((s, i) => (
                <span key={i} className="crumb-wrap">
                  <span className="sep">{path.includes("\\") ? "\\" : "/"}</span>
                  <span className="crumb" onClick={() => navigateTo(i)}>{s}</span>
                </span>
              ))}
            </>
          )}
        </div>
        <div style={{ flex: 1 }} />
        <button className="ghost" onClick={onCancel}>{t("common.cancel")}</button>
        <button className="primary" onClick={() => path && onSelect(path)} disabled={!path}>
          {t("picker.select")}
        </button>
      </div>
      {rootsError && <div className="ft-error">{rootsError}</div>}
      <div className="ft-body">
        {roots.length === 0 && !rootsError && (
          <div className="empty"><span className="spinner" /> {t("common.loading")}</div>
        )}
        {roots.map((r) => (
          <TreeNode
            key={r}
            path={r}
            display={r}
            depth={0}
            isRoot
            isActive={path === r}
            lookupNode={lookupNode}
            onToggle={toggle}
            onPickCurrent={onSelect}
            onNavigate={setPath}
          />
        ))}
        {path && nodes[path]?.error && (
          <div className="ft-error" style={{ padding: 8 }}>{nodes[path]?.error}</div>
        )}
      </div>
      <div className="ft-foot">
        <span style={{ color: "var(--fg-2)", fontSize: 10 }}>
          {nodes[path]?.listing
            ? t("picker.folderSummary", {
                dirs: nodes[path]?.listing?.dirs.length ?? 0,
                files: nodes[path]?.listing?.file_count ?? 0,
              })
            : ""}
        </span>
      </div>
    </div>
  );
}

function splitPath(p: string): string[] {
  if (!p) return [];
  const isWin = /^[A-Za-z]:[\\/]/.test(p) || p.includes("\\");
  if (isWin) {
    const m = /^([A-Za-z]:)([\\\/])(.*)$/.exec(p);
    if (m) {
      const rest = m[3].split(/[\\/]/).filter(Boolean);
      return [m[1] + m[2], ...rest];
    }
    return p.split(/[\\/]/).filter(Boolean);
  }
  return p.split("/").filter(Boolean);
}

function parentPath(p: string): string | null {
  if (!p) return null;
  const isWin = /^[A-Za-z]:[\\/]/.test(p) || p.includes("\\");
  if (isWin) {
    const m = /^([A-Za-z]:)[\\/](.*)$/.exec(p);
    if (!m) return null;
    if (!m[2]) return null; // already at root
    const idx = Math.max(m[2].lastIndexOf("\\"), m[2].lastIndexOf("/"));
    if (idx < 0) return m[1] + "\\";
    return m[1] + "\\" + m[2].slice(0, idx);
  }
  const idx = p.lastIndexOf("/");
  if (idx <= 0) return idx === 0 ? "/" : null;
  return p.slice(0, idx);
}

function TreeNode({
  path,
  display,
  depth,
  isRoot,
  isActive,
  lookupNode,
  onToggle,
  onPickCurrent,
  onNavigate,
}: {
  path: string;
  display: string;
  depth: number;
  isRoot: boolean;
  isActive: boolean;
  lookupNode: (p: string) => NodeState | undefined;
  onToggle: (p: string) => void;
  onPickCurrent: (p: string) => void;
  onNavigate: (p: string) => void;
}) {
  const t = useT();
  const nodeState = lookupNode(path);
  const expanded = !!nodeState?.expanded;
  const loading = !!nodeState?.loading;
  const loaded = !!nodeState?.loaded;
  const children = nodeState?.listing?.dirs ?? [];
  const hasSubdirs = children.length > 0;
  const expandable = !loaded || hasSubdirs; // assume could have kids until we know

  return (
    <>
      <div
        className={`ft-row ${isActive ? "active" : ""}`}
        style={{ paddingLeft: 8 + depth * 14 }}
        onClick={() => onNavigate(path)}
        onDoubleClick={() => onPickCurrent(path)}
      >
        <span
          className="ft-arrow"
          onClick={(e) => { e.stopPropagation(); onToggle(path); }}
          title={t("picker.expand")}
        >
          {loading
            ? <span className="spinner" style={{ width: 10, height: 10 }} />
            : expandable
              ? (expanded ? "▾" : "▸")
              : "·"}
        </span>
        <span className="ft-name" title={path}>
          {isRoot ? "💾 " : "📁 "}{display}
        </span>
        <span style={{ flex: 1 }} />
        <button
          className="ft-pick"
          onClick={(e) => { e.stopPropagation(); onPickCurrent(path); }}
          title={t("picker.pickThis")}
        >{t("picker.pick")}</button>
      </div>
      {expanded && children.map((c: DirEntry) => (
        <TreeNode
          key={c.path}
          path={c.path}
          display={c.name}
          depth={depth + 1}
          isRoot={false}
          isActive={false}
          lookupNode={lookupNode}
          onToggle={onToggle}
          onPickCurrent={onPickCurrent}
          onNavigate={onNavigate}
        />
      ))}
    </>
  );
}