import type { PredictionExplanation } from "../types/api";

export function ExplanationPanel({ e }: { e: PredictionExplanation }) {
  const traj = e.forecast_ambient_trajectory_c;
  const uref = e.uncertainty_source_reference as {
    pi80_width_reduction_vs_full_removing_empirical_residual?: number;
    interpretation?: string;
    diagnostic_scope?: string;
    diagnostic_kind?: string;
    note?: string;
  };
  return (
    <div>
      <div className="kv-list">
        <div className="kv-row"><span className="k">Current thermal gap (track − ambient)</span><span className="v">{e.current_track_to_ambient_thermal_gap_c?.toFixed(1)} °C</span></div>
        {traj && (
          <>
            <div className="kv-row"><span className="k">Current ambient</span><span className="v">{traj.current_ambient_temp_c.toFixed(1)} °C</span></div>
            <div className="kv-row"><span className="k">Forecast ambient at target time</span><span className="v">{traj.forecast_future_ambient_temp_c.toFixed(1)} °C</span></div>
            <div className="kv-row"><span className="k">&Delta; ambient (forecast)</span><span className="v">{traj.delta_ambient_temp_c >= 0 ? "+" : ""}{traj.delta_ambient_temp_c.toFixed(2)} °C</span></div>
          </>
        )}
        <div className="kv-row"><span className="k">Predicted future track-temp change</span><span className="v">{e.predicted_future_track_temperature_change_c != null ? `${e.predicted_future_track_temperature_change_c >= 0 ? "+" : ""}${e.predicted_future_track_temperature_change_c.toFixed(2)} °C` : "—"}</span></div>
        <div className="kv-row"><span className="k">Solar elevation (mean, decision→target)</span><span className="v">{e.solar_elevation_mean_deg != null ? `${e.solar_elevation_mean_deg.toFixed(1)}°` : "—"}</span></div>
      </div>
      <p className="text-dim" style={{ fontSize: 11, marginTop: 10 }}>{e.note}</p>

      <div className="panel-title" style={{ marginTop: 14 }}>Uncertainty-source diagnostic</div>
      {uref?.diagnostic_scope && (
        <div className="illustrative-banner" style={{ color: "var(--accent)", borderColor: "var(--accent-dim)", background: "rgba(79,195,247,0.06)" }}>
          {uref.diagnostic_scope.replace(/_/g, " ")} — {uref.diagnostic_kind}
        </div>
      )}
      {uref?.pi80_width_reduction_vs_full_removing_empirical_residual != null && (
        <div className="kv-row">
          <span className="k">80% PI width reduction if empirical residual removed</span>
          <span className="v">{(uref.pi80_width_reduction_vs_full_removing_empirical_residual * 100).toFixed(1)}%</span>
        </div>
      )}
      <p className="text-dim" style={{ fontSize: 11 }}>{uref?.interpretation ?? uref?.note}</p>
    </div>
  );
}
