/**
 * Lightweight i18n: zh-CN + en-US, no external deps.
 *
 *   import { useT, setLanguage } from "../i18n";
 *   const t = useT();
 *   <h1>{t("app.brand")}</h1>
 *   <p>{t("status.shown", { filtered: 3, total: 10 })}</p>
 *
 * Language preference is persisted in localStorage["rowpic.lang"] and
 * detected from the browser on first load.
 */
import { useSyncExternalStore } from "react";

export type Lang = "zh-CN" | "en-US";

const STORAGE_KEY = "rowpic.lang";
const SUPPORTED: Lang[] = ["zh-CN", "en-US"];

function detectInitial(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && (SUPPORTED as string[]).includes(saved)) return saved as Lang;
  } catch {
    /* localStorage may be blocked */
  }
  const nav = typeof navigator !== "undefined" ? navigator.language : "en-US";
  if (nav.toLowerCase().startsWith("zh")) return "zh-CN";
  return "en-US";
}

// --------- the actual translation dicts ---------
type Dict = Record<string, string>;

const en: Dict = {
  // brand
  "app.brand": "rowpic",
  "app.tagline": "RAW + standard photo browser / analyzer / colorist",

  // common
  "common.ready": "Ready",
  "common.working": "Working...",
  "common.error": "Error",
  "common.cancel": "Cancel",
  "common.confirm": "Confirm",
  "common.close": "Close",
  "common.reset": "Reset",
  "common.loading": "loading...",
  "common.dash": "-",
  "common.unknown": "unknown",
  "common.yes": "Yes",
  "common.no": "No",

  // top bar
  "topbar.placeholder": "Folder path (e.g. C:\\Users\\you\\Pictures)",
  "topbar.scan": "Scan Folder",
  "topbar.scanning": "Scanning...",
  "topbar.classify": "One-Click Classify",
  "topbar.classifying": "Analyzing...",
  "topbar.noFolder": "(no folder)",
  "topbar.lang.label": "Language",

  // sidebar
  "sidebar.count": "{filtered} / {total} photos",
  "sidebar.rawHint": "RAW = camera raw",
  "sidebar.empty": "No photos. Scan a folder to begin.",
  "sidebar.category.all": "All",
  "sidebar.category.keep": "Keep",
  "sidebar.category.blurry": "Blurry",
  "sidebar.category.blurry_face": "Face-Blur",
  "sidebar.category.underexposed": "Dark",
  "sidebar.category.overexposed": "Bright",
  "sidebar.category.duplicate": "Duplicate",

  // category badge labels
  "category.keep": "Keep",
  "category.blurry": "Blurry",
  "category.blurry_face": "Face",
  "category.underexposed": "Dark",
  "category.overexposed": "Bright",
  "category.duplicate": "Dup",
  "category.unclassified": "",

  // stage
  "stage.empty": "Select a photo to preview",
  "stage.hint": "Drag the grid to move · Shift+drag to scale · Wheel to zoom",
  "stage.grid": "Grid",
  "stage.reset": "Reset",

  // composition
  "composition.none": "none",
  "composition.rule_of_thirds": "rule of thirds",
  "composition.golden_ratio": "golden ratio",
  "composition.golden_spiral": "golden spiral",
  "composition.diagonal": "diagonal",
  "composition.center_cross": "center cross",
  "composition.triangle": "triangle",
  "composition.harmonic": "harmonic",
  "composition.custom": "custom",

  // right panel tabs
  "tab.exif": "EXIF",
  "tab.hist": "Histogram",
  "tab.focus": "Focus",
  "tab.color": "Color",
  "right.noPhoto": "No photo selected",
  "right.loading": "loading...",

  // histogram
  "hist.title": "RGB + Luminance Histogram",
  "hist.legend": "R · G · B · Lum",
  "hist.clipping": "Clipping",
  "hist.highlights": "Highlights",
  "hist.shadows": "Shadows",

  // focus
  "focus.noData": "No focus data",
  "focus.overall": "Overall Sharpness",
  "focus.laplacian": "Laplacian var.",
  "focus.quality": "Quality",
  "focus.exposure": "Exposure",
  "focus.backlit": "Backlit",
  "focus.faces": "Detected Faces ({n})",
  "focus.heatmap": "Focus Heatmap",

  // exif
  "exif.file": "File",
  "exif.format": "Format",
  "exif.size": "Size",
  "exif.dimensions": "Dimensions",
  "exif.taken": "Taken",
  "exif.cameraLens": "Camera & Lens",
  "exif.make": "Make",
  "exif.model": "Model",
  "exif.lens": "Lens",
  "exif.focal": "Focal",
  "exif.software": "Software",
  "exif.exposure": "Exposure",
  "exif.aperture": "Aperture",
  "exif.shutter": "Shutter",
  "exif.iso": "ISO",
  "exif.program": "Program",
  "exif.wb": "WB",
  "exif.flash": "Flash",
  "exif.rawExtras": "RAW Extras",
  "exif.focalEquiv": "(≈ {n}mm eq.)",
  "exif.focalMm": "{n}mm",
  "exif.apertureVal": "f/{n}",

  // color panel
  "color.light": "Light",
  "color.colorSection": "Color",
  "color.exposure": "Exposure",
  "color.contrast": "Contrast",
  "color.highlights": "Highlights",
  "color.shadows": "Shadows",
  "color.whites": "Whites",
  "color.blacks": "Blacks",
  "color.saturation": "Saturation",
  "color.vibrance": "Vibrance",
  "color.temperature": "Temperature",
  "color.tint": "Tint",
  "color.oneClick": "One-Click",
  "color.auto": "Auto Tone",
  "color.ai": "AI Look",
  "color.reset": "Reset",
  "color.preview": "Preview",
  "color.previewHint": "Click AI Look / Auto Tone, or move a slider to preview.",
  "color.applied": "applied: {list}",
  "color.aiHelp": "AI Look requires ROWPIC_ENABLE_AI_COLOR=true on the backend. Edit backend/.env and restart to enable the deep-learning model path.",
  "color.evFmt": "{sign}{n} EV",
  "color.aiTitle": "AI color (server-side; falls back to Auto when no model is loaded)",

  // status bar
  "status.ready": "Ready",
  "status.working": "Working...",
  "status.shown": "{filtered} shown / {total} total",

  // errors
  "error.enterPath": "Enter a folder path to scan",
  "error.noPhotos": "No photos to classify",
  "error.classifyFailed": "Classify failed: {msg}",
  "error.scanFailed": "Scan failed: {msg}",
  "error.detailFailed": "Detail failed: {msg}",

  // classified summary
  "summary.classified": "Classified {total}: {breakdown}",

  // generic
  "generic.byte": "B",
  "generic.kb": "K",
  "generic.mb": "M",
};

const zh: Dict = {
  // brand
  "app.brand": "rowpic",
  "app.tagline": "RAW + 标准照片浏览器 / 分析器 / 调色器",

  // common
  "common.ready": "就绪",
  "common.working": "处理中…",
  "common.error": "错误",
  "common.cancel": "取消",
  "common.confirm": "确认",
  "common.close": "关闭",
  "common.reset": "重置",
  "common.loading": "加载中…",
  "common.dash": "—",
  "common.unknown": "未知",
  "common.yes": "是",
  "common.no": "否",

  // top bar
  "topbar.placeholder": "照片目录路径（如 C:\\Users\\you\\Pictures）",
  "topbar.scan": "扫描目录",
  "topbar.scanning": "扫描中…",
  "topbar.classify": "一键归类",
  "topbar.classifying": "分析中…",
  "topbar.noFolder": "（未选目录）",
  "topbar.lang.label": "语言",

  // sidebar
  "sidebar.count": "{filtered} / {total} 张",
  "sidebar.rawHint": "RAW = 相机原始格式",
  "sidebar.empty": "暂无照片。请先扫描目录。",
  "sidebar.category.all": "全部",
  "sidebar.category.keep": "保留",
  "sidebar.category.blurry": "虚焦",
  "sidebar.category.blurry_face": "脸糊",
  "sidebar.category.underexposed": "欠曝",
  "sidebar.category.overexposed": "过曝",
  "sidebar.category.duplicate": "重复",

  // category badge labels
  "category.keep": "保留",
  "category.blurry": "虚焦",
  "category.blurry_face": "脸糊",
  "category.underexposed": "欠曝",
  "category.overexposed": "过曝",
  "category.duplicate": "重",
  "category.unclassified": "",

  // stage
  "stage.empty": "请在左侧选择一张照片",
  "stage.hint": "拖拽移动参考线 · Shift+拖拽缩放 · 滚轮缩放",
  "stage.grid": "参考线",
  "stage.reset": "重置",

  // composition
  "composition.none": "无",
  "composition.rule_of_thirds": "三分法",
  "composition.golden_ratio": "黄金分割",
  "composition.golden_spiral": "黄金螺旋",
  "composition.diagonal": "对角线",
  "composition.center_cross": "中心十字",
  "composition.triangle": "三角",
  "composition.harmonic": "和声",
  "composition.custom": "自定义",

  // right panel tabs
  "tab.exif": "EXIF",
  "tab.hist": "直方图",
  "tab.focus": "对焦",
  "tab.color": "调色",
  "right.noPhoto": "未选择照片",
  "right.loading": "加载中…",

  // histogram
  "hist.title": "RGB + 亮度直方图",
  "hist.legend": "红 · 绿 · 蓝 · 亮度",
  "hist.clipping": "剪切检测",
  "hist.highlights": "高光剪切",
  "hist.shadows": "暗部剪切",

  // focus
  "focus.noData": "无对焦数据",
  "focus.overall": "整体锐度",
  "focus.laplacian": "拉普拉斯方差",
  "focus.quality": "质量",
  "focus.exposure": "曝光",
  "focus.backlit": "逆光",
  "focus.faces": "检测到人脸（{n}）",
  "focus.heatmap": "对焦热力图",

  // exif
  "exif.file": "文件",
  "exif.format": "格式",
  "exif.size": "大小",
  "exif.dimensions": "尺寸",
  "exif.taken": "拍摄时间",
  "exif.cameraLens": "相机与镜头",
  "exif.make": "厂商",
  "exif.model": "型号",
  "exif.lens": "镜头",
  "exif.focal": "焦距",
  "exif.software": "软件",
  "exif.exposure": "曝光",
  "exif.aperture": "光圈",
  "exif.shutter": "快门",
  "exif.iso": "ISO",
  "exif.program": "模式",
  "exif.wb": "白平衡",
  "exif.flash": "闪光",
  "exif.rawExtras": "RAW 附加信息",
  "exif.focalEquiv": "（≈{n}mm 等效）",
  "exif.focalMm": "{n}mm",
  "exif.apertureVal": "f/{n}",

  // color panel
  "color.light": "光线",
  "color.colorSection": "颜色",
  "color.exposure": "曝光",
  "color.contrast": "对比度",
  "color.highlights": "高光",
  "color.shadows": "阴影",
  "color.whites": "白点",
  "color.blacks": "黑点",
  "color.saturation": "饱和度",
  "color.vibrance": "自然饱和度",
  "color.temperature": "色温",
  "color.tint": "色调",
  "color.oneClick": "一键",
  "color.auto": "自动色调",
  "color.ai": "AI 调色",
  "color.reset": "重置",
  "color.preview": "预览",
  "color.previewHint": "点击 AI 调色 / 自动色调，或拖动滑块查看效果。",
  "color.applied": "已应用：{list}",
  "color.aiHelp": "AI 调色需要在后端开启 ROWPIC_ENABLE_AI_COLOR=true。编辑 backend/.env 后重启即可启用深度学习模型路径。",
  "color.evFmt": "{sign}{n} EV",
  "color.aiTitle": "AI 调色（服务端处理；未加载模型时回退到自动色调）",

  // status bar
  "status.ready": "就绪",
  "status.working": "处理中…",
  "status.shown": "显示 {filtered} / 共 {total} 张",

  // errors
  "error.enterPath": "请输入要扫描的目录",
  "error.noPhotos": "没有可归类的照片",
  "error.classifyFailed": "归类失败：{msg}",
  "error.scanFailed": "扫描失败：{msg}",
  "error.detailFailed": "详情加载失败：{msg}",

  // classified summary
  "summary.classified": "已归类 {total} 张：{breakdown}",

  // generic
  "generic.byte": "B",
  "generic.kb": "K",
  "generic.mb": "M",
};

const DICTS: Record<Lang, Dict> = { "en-US": en, "zh-CN": zh };

// --------- reactive language state ---------
let _lang: Lang = detectInitial();
const _subs = new Set<() => void>();

function subscribe(cb: () => void) {
  _subs.add(cb);
  return () => { _subs.delete(cb); };
}

function getSnapshot() {
  return _lang;
}

function getServerSnapshot(): Lang {
  return _lang;
}

export function setLanguage(lang: Lang) {
  if (lang === _lang) return;
  _lang = lang;
  try { localStorage.setItem(STORAGE_KEY, lang); } catch { /* ignore */ }
  _subs.forEach((cb) => cb());
}

export function getLanguage(): Lang {
  return _lang;
}

export function useLang(): Lang {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

export function useT(): (key: string, params?: Record<string, string | number>) => string {
  const lang = useLang();
  return (key, params) => translate(lang, key, params);
}

export function t(key: string, params?: Record<string, string | number>): string {
  return translate(_lang, key, params);
}

function translate(lang: Lang, key: string, params?: Record<string, string | number>): string {
  const dict = DICTS[lang] || en;
  let s = dict[key];
  if (s === undefined) s = en[key] ?? key;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      s = s.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
    }
  }
  return s;
}

export const SUPPORTED_LANGS = SUPPORTED;
export const LANG_LABELS: Record<Lang, string> = { "zh-CN": "中文", "en-US": "English" };

export { translate };