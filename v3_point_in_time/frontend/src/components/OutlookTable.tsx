import type { OutlookHorizon } from "../types/api";
import { StatusBadge } from "./StatusBadge";

interface Props {
  horizons: OutlookHorizon[];
  onSelectPrediction?: (predictionId: string) => void;
}

const fmtV = (v?: number) => (v === undefined ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(3)}`);
const fmtP = (v?: number) => (v === undefined ? "—" : `${(v * 100).toFixed(1)}%`);

export function OutlookTable({ horizons, onSelectPrediction }: Props) {
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Horizon (min)</th>
          <th>E[&Delta;v] (mph)</th>
          <th>P(improve)</th>
          <th>80% PI (mph)</th>
          <th>90% PI (mph)</th>
          <th>Support</th>
        </tr>
      </thead>
      <tbody>
        {horizons.map((h) => (
          <tr
            key={h.horizon_minutes}
            onClick={() => h.prediction_id && onSelectPrediction?.(h.prediction_id)}
            style={{ cursor: h.prediction_id ? "pointer" : "default" }}
          >
            <td>{h.horizon_minutes}</td>
            <td>{fmtV(h.expected_delta_v)}</td>
            <td>{fmtP(h.p_improve)}</td>
            <td>{h.pi80_low !== undefined ? `[${fmtV(h.pi80_low)}, ${fmtV(h.pi80_high)}]` : "—"}</td>
            <td>{h.pi90_low !== undefined ? `[${fmtV(h.pi90_low)}, ${fmtV(h.pi90_high)}]` : "—"}</td>
            <td>
              <StatusBadge status={h.status} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
