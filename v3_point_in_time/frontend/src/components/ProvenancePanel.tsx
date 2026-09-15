import type { PredictionProvenance } from "../types/api";
import { StatusBadge } from "./StatusBadge";

function short(hash: string | null, n = 16): string {
  if (!hash) return "—";
  return hash.length > n ? `${hash.slice(0, n)}…` : hash;
}

export function ProvenancePanel({ p }: { p: PredictionProvenance }) {
  return (
    <div className="kv-list">
      <div className="kv-row"><span className="k">Decision snapshot</span><span className="v">{p.decision_snapshot_id}</span></div>
      <div className="kv-row"><span className="k">Information cutoff</span><span className="v">{p.information_cutoff}</span></div>
      <div className="kv-row"><span className="k">Forecast vintage</span><span className="v">{p.forecast_vintage_id ?? "none available"}</span></div>
      <div className="kv-row"><span className="k">Forecast issue time</span><span className="v">{p.forecast_issue_time ?? "—"}</span></div>
      <div className="kv-row"><span className="k">Forecast valid time</span><span className="v">{p.forecast_valid_time ?? "—"}</span></div>
      <div className="kv-row">
        <span className="k">Target-time mismatch</span>
        <span className="v">{p.forecast_target_time_error_minutes != null ? `${p.forecast_target_time_error_minutes.toFixed(1)} min` : "—"}</span>
      </div>
      <div className="kv-row"><span className="k">Forecast ambient temp</span><span className="v">{p.forecast_ambient_temp_c != null ? `${p.forecast_ambient_temp_c.toFixed(1)} °C` : "—"}</span></div>
      <div className="kv-row"><span className="k">FINAL_V2 model hash</span><span className="v">{short(p.final_v2_model_hash)}</span></div>
      <div className="kv-row"><span className="k">Input hash</span><span className="v">{short(p.input_hash)}</span></div>
      <div className="kv-row">
        <span className="k">Scientific support</span>
        <span className="v"><StatusBadge status={p.scientific_support} /></span>
      </div>
      <div className="kv-row">
        <span className="k">Historical scoring support</span>
        <span className="v"><StatusBadge status={p.historical_scoring_support} /></span>
      </div>
    </div>
  );
}
