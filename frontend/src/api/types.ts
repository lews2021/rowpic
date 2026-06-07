export type FileFormat = "raw" | "jpeg" | "png" | "tiff" | "webp" | "bmp" | "heic" | "other";
export type FocusQuality = "sharp" | "soft" | "blurry" | "unknown";
export type CategoryLabel =
  | "keep" | "blurry" | "blurry_face" | "underexposed" | "overexposed" | "duplicate" | "unclassified";

export interface ExifInfo {
  make?: string | null;
  model?: string | null;
  lens?: string | null;
  lens_model?: string | null;
  focal_length?: number | null;
  focal_length_35mm?: number | null;
  aperture?: number | null;
  shutter?: string | null;
  shutter_num?: number | null;
  iso?: number | null;
  exposure_program?: string | null;
  white_balance?: string | null;
  flash?: boolean | null;
  taken_at?: string | null;
  orientation: number;
  color_space?: string | null;
  software?: string | null;
  raw_extras: Record<string, unknown>;
}

export interface HistogramData {
  luminance: number[];
  red: number[];
  green: number[];
  blue: number[];
  clip_high: number;
  clip_low: number;
}

export interface FaceBox {
  x: number; y: number; w: number; h: number;
  sharpness: number;
  quality: FocusQuality;
  confidence: number;
}

export interface FocusReport {
  overall_sharpness: number;
  overall_quality: FocusQuality;
  exposure?: number | null;
  is_backlit: boolean;
  faces: FaceBox[];
  blur_map_thumb?: string | null;
}

export interface PhotoMeta {
  id: string;
  path: string;
  name: string;
  ext: string;
  format: FileFormat;
  size: number;
  mtime: number;
  width: number;
  height: number;
  has_preview: boolean;
  exif: ExifInfo;
  category: CategoryLabel;
  flags: string[];
}

export interface PhotoDetail extends PhotoMeta {
  histogram?: HistogramData | null;
  focus?: FocusReport | null;
  thumb_url: string;
  preview_url: string;
}

export interface ScanResult {
  root: string;
  total: number;
  photos: PhotoMeta[];
  skipped: number;
  errors: string[];
}

export interface ColorAdjustRequest {
  exposure?: number;
  contrast?: number;
  saturation?: number;
  vibrance?: number;
  temperature?: number;
  tint?: number;
  highlights?: number;
  shadows?: number;
  whites?: number;
  blacks?: number;
  auto?: boolean;
  ai?: boolean;
  ai_model?: string | null;
}

export interface ColorAdjustResult {
  image_b64: string;
  width: number;
  height: number;
  applied: Record<string, unknown>;
}

export type CompositionType =
  | "none" | "rule_of_thirds" | "golden_ratio" | "golden_spiral"
  | "diagonal" | "center_cross" | "triangle" | "harmonic" | "custom";

export interface CompositionOverlay {
  type: CompositionType;
  color: string;
  opacity: number;
  line_width: number;
  x: number;
  y: number;
  scale: number;
  rotation: number;
}

export const DEFAULT_COMPOSITION: CompositionOverlay = {
  type: "rule_of_thirds",
  color: "#ffffff",
  opacity: 0.65,
  line_width: 1.5,
  x: 0,
  y: 0,
  scale: 1.0,
  rotation: 0,
};

export interface ClassifyRequest {
  rules: string[];
  move: boolean;
  dest_template: string;
}

export interface ClassifyResult {
  total: number;
  categories: Record<string, number>;
  moves: { src: string; dest: string; category: string }[];
  per_photo: Record<string, string>;
}
