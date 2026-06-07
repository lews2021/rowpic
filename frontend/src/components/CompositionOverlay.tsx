import { useCallback, useEffect, useRef, useState } from "react";
import type { CompositionOverlay as Overlay, CompositionType } from "../api/types";
import { DEFAULT_COMPOSITION } from "../api/types";
import { useT } from "../i18n";

interface Props {
  width: number;
  height: number;
  imageNaturalWidth: number;
  imageNaturalHeight: number;
  faces?: { x: number; y: number; w: number; h: number; sharpness: number; quality: string }[];
  onChange?: (o: Overlay) => void;
}

const COMPOSITIONS: CompositionType[] = [
  "rule_of_thirds", "golden_ratio", "golden_spiral",
  "diagonal", "center_cross", "triangle", "harmonic", "none",
];

// ---- pure drawing helpers ----

function drawRuleOfThirds(ctx: CanvasRenderingContext2D, w: number, h: number, color: string, lw: number) {
  ctx.beginPath();
  ctx.strokeStyle = color; ctx.lineWidth = lw;
  for (const x of [w / 3, 2 * w / 3]) {
    ctx.moveTo(x, 0); ctx.lineTo(x, h);
  }
  for (const y of [h / 3, 2 * h / 3]) {
    ctx.moveTo(0, y); ctx.lineTo(w, y);
  }
  ctx.stroke();
}

function drawGoldenRatio(ctx: CanvasRenderingContext2D, w: number, h: number, color: string, lw: number) {
  const phi = 1.0 / 1.618;
  ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = lw;
  for (const x of [w * (1 - phi), w * phi]) {
    ctx.moveTo(x, 0); ctx.lineTo(x, h);
  }
  for (const y of [h * (1 - phi), h * phi]) {
    ctx.moveTo(0, y); ctx.lineTo(w, y);
  }
  ctx.stroke();
}

function drawGoldenSpiral(ctx: CanvasRenderingContext2D, w: number, h: number, color: string, lw: number) {
  // Logarithmic spiral whose radius is multiplied by phi every quarter turn.
  //   r(theta) = rMax * exp(-b * (theta - thetaStart))
  //   where b = ln(phi) / (pi/2)  =>  every +pi/2 in theta divides r by phi.
  // We sample 96 points along 2.5 turns; the result is a smooth, classic
  // golden spiral centered in the canvas.
  ctx.beginPath();
  ctx.strokeStyle = color;
  ctx.lineWidth = lw;

  const phi = 1.6180339887498949;
  const b = Math.log(phi) / (Math.PI / 2);

  const cx = w / 2;
  const cy = h / 2;
  const rMax = Math.min(w, h) * 0.48;
  const turns = 2.5;
  const totalAngle = turns * 2 * Math.PI;
  const steps = 96;
  const thetaStart = -Math.PI / 2; // start at top of canvas

  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const theta = thetaStart + t * totalAngle;
    const r = rMax * Math.exp(-b * t * totalAngle);
    const x = cx + r * Math.cos(theta);
    const y = cy + r * Math.sin(theta);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
}

function drawDiagonal(ctx: CanvasRenderingContext2D, w: number, h: number, color: string, lw: number) {
  ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = lw;
  ctx.moveTo(0, 0); ctx.lineTo(w, h);
  ctx.moveTo(w, 0); ctx.lineTo(0, h);
  ctx.stroke();
}

function drawCenterCross(ctx: CanvasRenderingContext2D, w: number, h: number, color: string, lw: number) {
  ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = lw;
  ctx.moveTo(w / 2, 0); ctx.lineTo(w / 2, h);
  ctx.moveTo(0, h / 2); ctx.lineTo(w, h / 2);
  ctx.stroke();
}

function drawTriangle(ctx: CanvasRenderingContext2D, w: number, h: number, color: string, lw: number) {
  ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = lw;
  // Downward triangle (GoldenGate / landscape)
  ctx.moveTo(0, h * 0.2);
  ctx.lineTo(w, h * 0.2);
  ctx.lineTo(w / 2, h);
  ctx.closePath();
  ctx.stroke();
}

function drawHarmonic(ctx: CanvasRenderingContext2D, w: number, h: number, color: string, lw: number) {
  // Harmonic: 4 sub-rectangles preserving the outer ratio
  const segments = [1 / 4, 1 / 2, 3 / 4];
  ctx.beginPath(); ctx.strokeStyle = color; ctx.lineWidth = lw;
  for (const s of segments) {
    ctx.moveTo(0, h * s); ctx.lineTo(w, h * s);
    ctx.moveTo(w * s, 0); ctx.lineTo(w * s, h);
  }
  ctx.stroke();
}

const DRAWERS: Record<CompositionType, (ctx: CanvasRenderingContext2D, w: number, h: number, color: string, lw: number) => void> = {
  rule_of_thirds: drawRuleOfThirds,
  golden_ratio: drawGoldenRatio,
  golden_spiral: drawGoldenSpiral,
  diagonal: drawDiagonal,
  center_cross: drawCenterCross,
  triangle: drawTriangle,
  harmonic: drawHarmonic,
  custom: () => {},
  none: () => {},
};

// ---- component ----

export default function CompositionOverlayCanvas(props: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dragState = useRef<null | { startX: number; startY: number; ox: number; oy: number; mode: "move" | "scale" }>(null);
  const t = useT();
  const [overlay, setOverlay] = useState<Overlay>(DEFAULT_COMPOSITION);
  const [dragging, setDragging] = useState(false);

  // Sync overlay -> parent
  useEffect(() => {
    props.onChange?.(overlay);
  }, [overlay]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    if (canvas.width !== props.width * dpr || canvas.height !== props.height * dpr) {
      canvas.width = props.width * dpr;
      canvas.height = props.height * dpr;
      canvas.style.width = props.width + "px";
      canvas.style.height = props.height + "px";
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, props.width, props.height);

    ctx.save();
    ctx.globalAlpha = overlay.opacity;
    ctx.translate(props.width / 2 + overlay.x, props.height / 2 + overlay.y);
    ctx.rotate((overlay.rotation * Math.PI) / 180);
    ctx.scale(overlay.scale, overlay.scale);
    ctx.translate(-props.width / 2, -props.height / 2);
    const drawer = DRAWERS[overlay.type];
    drawer(ctx, props.width, props.height, overlay.color, overlay.line_width);
    ctx.restore();

    // face boxes
    if (props.faces && props.imageNaturalWidth > 0) {
      ctx.save();
      ctx.strokeStyle = "#74c0fc";
      ctx.lineWidth = 2;
      for (const f of props.faces) {
        const sx = props.width / props.imageNaturalWidth;
        const sy = props.height / props.imageNaturalHeight;
        const x = f.x * sx, y = f.y * sy, w = f.w * sx, h = f.h * sy;
        ctx.strokeRect(x, y, w, h);
        ctx.fillStyle = f.quality === "blurry" ? "rgba(255,107,107,0.9)"
          : f.quality === "soft" ? "rgba(255,212,59,0.9)"
          : "rgba(81,207,102,0.9)";
        ctx.font = "12px ui-monospace, monospace";
        ctx.fillText(`${f.sharpness.toFixed(0)} ${f.quality}`, x + 4, y + 14);
      }
      ctx.restore();
    }
  }, [props.width, props.height, props.imageNaturalWidth, props.imageNaturalHeight, props.faces, overlay]);

  useEffect(() => { draw(); }, [draw]);

  const onPointerDown = (e: React.PointerEvent) => {
    e.currentTarget.setPointerCapture(e.pointerId);
    setDragging(true);
    dragState.current = {
      startX: e.clientX,
      startY: e.clientY,
      ox: overlay.x,
      oy: overlay.y,
      mode: e.shiftKey ? "scale" : "move",
    };
  };
  const onPointerMove = (e: React.PointerEvent) => {
    const s = dragState.current;
    if (!s) return;
    const dx = e.clientX - s.startX;
    const dy = e.clientY - s.startY;
    if (s.mode === "move") {
      setOverlay((o) => ({ ...o, x: s.ox + dx, y: s.oy + dy }));
    } else {
      const factor = 1 + (dx + dy) / 200;
      setOverlay((o) => ({ ...o, scale: Math.max(0.2, Math.min(4, o.scale * factor)) }));
    }
  };
  const onPointerUp = (e: React.PointerEvent) => {
    e.currentTarget.releasePointerCapture(e.pointerId);
    setDragging(false);
    dragState.current = null;
  };
  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    setOverlay((o) => ({ ...o, scale: Math.max(0.2, Math.min(4, o.scale * factor)) }));
  };

  return (
    <>
      <canvas
        ref={canvasRef}
        className={`overlay-canvas ${dragging ? "dragging" : ""}`}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onWheel={onWheel}
        style={{ width: props.width, height: props.height }}
      />
      <div style={{
        position: "absolute", top: 8, right: 8,
        display: "flex", gap: 4, alignItems: "center",
        background: "rgba(20,22,28,0.85)",
        padding: "4px 8px", borderRadius: 6, fontSize: 11,
        pointerEvents: "auto",
      }}>
        <span style={{ color: "var(--fg-2)" }}>{t("stage.grid")}:</span>
        <select
          value={overlay.type}
          onChange={(e) => setOverlay((o) => ({ ...o, type: e.target.value as CompositionType }))}
        >
          {COMPOSITIONS.map((c) => <option key={c} value={c}>{t(`composition.${c}`)}</option>)}
        </select>
        <input
          type="color" value={overlay.color}
          onChange={(e) => setOverlay((o) => ({ ...o, color: e.target.value }))}
          style={{ padding: 0, background: "transparent", border: "none" }}
        />
        <button onClick={() => setOverlay({ ...DEFAULT_COMPOSITION, type: overlay.type })}>{t("stage.reset")}</button>
      </div>
    </>
  );
}
