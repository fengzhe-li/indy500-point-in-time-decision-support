import type { OutlookHorizon } from "../types/api";

interface Props {
  horizons: OutlookHorizon[];
}

const W = 640;
const H = 260;
const PAD_L = 52;
const PAD_R = 16;
const PAD_T = 16;
const PAD_B = 34;
const X_MAX = 130;

function xScale(h: number) {
  return PAD_L + (h / X_MAX) * (W - PAD_L - PAD_R);
}

/** Plain SVG chart -- no chart-library dependency. Draws the 80%
 * predictive-interval band and the expected-value curve only for
 * horizons the backend marked SUPPORTED; abstained/unsupported
 * horizons are shown as gaps with a marker, never interpolated. */
export function OutlookCurveChart({ horizons }: Props) {
  const supported = horizons.filter((h) => h.status === "SUPPORTED");
  const values = supported.flatMap((h) => [h.pi80_low!, h.pi80_high!, h.expected_delta_v!]);
  const yMax = Math.max(0.5, ...values.map((v) => Math.abs(v))) * 1.15;
  const yMin = -yMax;

  function yScale(v: number) {
    return PAD_T + ((yMax - v) / (yMax - yMin)) * (H - PAD_T - PAD_B);
  }

  const bandPath =
    supported.length > 0
      ? `M ${supported.map((h) => `${xScale(h.horizon_minutes)},${yScale(h.pi80_high!)}`).join(" L ")} ` +
        `L ${[...supported].reverse().map((h) => `${xScale(h.horizon_minutes)},${yScale(h.pi80_low!)}`).join(" L ")} Z`
      : "";

  const linePath =
    supported.length > 0
      ? `M ${supported.map((h) => `${xScale(h.horizon_minutes)},${yScale(h.expected_delta_v!)}`).join(" L ")}`
      : "";

  const zeroY = yScale(0);
  const ticks = [0, 30, 60, 90, 120];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="Conditional physical outlook curve">
      {/* zero reference */}
      <line x1={PAD_L} y1={zeroY} x2={W - PAD_R} y2={zeroY} stroke="#2c333d" strokeDasharray="3,3" />
      {/* y axis */}
      <line x1={PAD_L} y1={PAD_T} x2={PAD_L} y2={H - PAD_B} stroke="#2c333d" />
      <text x={8} y={yScale(yMax) + 4} fill="#75808d" fontSize="9" fontFamily="monospace">{yMax.toFixed(2)}</text>
      <text x={8} y={zeroY + 4} fill="#75808d" fontSize="9" fontFamily="monospace">0.000</text>
      <text x={8} y={yScale(yMin) + 4} fill="#75808d" fontSize="9" fontFamily="monospace">{yMin.toFixed(2)}</text>

      {/* x axis ticks */}
      {ticks.map((t) => (
        <g key={t}>
          <line x1={xScale(t)} y1={H - PAD_B} x2={xScale(t)} y2={H - PAD_B + 4} stroke="#2c333d" />
          <text x={xScale(t)} y={H - PAD_B + 16} fill="#75808d" fontSize="10" fontFamily="monospace" textAnchor="middle">
            {t}
          </text>
        </g>
      ))}
      <text x={W / 2} y={H - 4} fill="#75808d" fontSize="9.5" textAnchor="middle">
        conditional opportunity horizon h (minutes) — not a forecast of when an opportunity occurs
      </text>

      {bandPath && <path d={bandPath} fill="#4fc3f7" opacity={0.14} stroke="none" />}
      {linePath && <path d={linePath} fill="none" stroke="#4fc3f7" strokeWidth={1.75} />}

      {horizons.map((h) => {
        const x = xScale(h.horizon_minutes);
        if (h.status !== "SUPPORTED") {
          return (
            <g key={h.horizon_minutes}>
              <line x1={x} y1={PAD_T} x2={x} y2={H - PAD_B} stroke="#d9695f" strokeDasharray="2,3" opacity={0.5} />
              <circle cx={x} cy={zeroY} r={3} fill="none" stroke="#d9695f" strokeWidth={1.5} />
            </g>
          );
        }
        return <circle key={h.horizon_minutes} cx={x} cy={yScale(h.expected_delta_v!)} r={3.5} fill="#4fc3f7" />;
      })}
    </svg>
  );
}
