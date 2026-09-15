import { useState } from "react";
import { api, ApiError } from "../services/api";
import { useAsync } from "../hooks/useAsync";
import { Loading, ErrorBox } from "../components/LoadingError";
import { OutlookCurveChart } from "../components/OutlookCurveChart";
import { OutlookTable } from "../components/OutlookTable";
import { ScientificBoundaryCard } from "../components/ScientificBoundaryCard";
import type { OutlookHorizon, ScenarioResponse } from "../types/api";

function toOutlookHorizons(response: ScenarioResponse): OutlookHorizon[] {
  return response.horizons.map((h) => ({
    horizon_minutes: h.horizon_minutes,
    status: h.status,
    expected_delta_v: h.expected_delta_v,
    median_delta_v: h.median_delta_v,
    p_improve: h.p_improve,
    pi80_low: h.pi80_low,
    pi80_high: h.pi80_high,
    pi90_low: h.pi90_low,
    pi90_high: h.pi90_high,
    applicability_status: h.status,
    abstention_reason_codes: h.reasons,
  }));
}

export function ScenarioMode() {
  const schemaState = useAsync(() => api.scenarioSchema(), []);
  const [trackTemp, setTrackTemp] = useState<string>("");
  const [ambientTemp, setAmbientTemp] = useState<string>("");
  const [forecastAmbient, setForecastAmbient] = useState<string>("");
  const [decisionTime, setDecisionTime] = useState<string>("");
  const [result, setResult] = useState<ScenarioResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function applyPreset(key: string) {
    const preset = schemaState.data?.presets[key];
    if (!preset) return;
    setTrackTemp(String(preset.current_track_temp_c));
    setAmbientTemp(String(preset.current_ambient_temp_c));
    setForecastAmbient(String(preset.forecast_future_ambient_temp_c));
    setResult(null);
  }

  async function runScenario() {
    setRunning(true);
    setError(null);
    try {
      const response = await api.runScenario({
        current_track_temp_c: trackTemp === "" ? undefined : Number(trackTemp),
        current_ambient_temp_c: ambientTemp === "" ? undefined : Number(ambientTemp),
        forecast_future_ambient_temp_c: forecastAmbient === "" ? undefined : Number(forecastAmbient),
        decision_time: decisionTime === "" ? undefined : decisionTime,
      });
      setResult(response);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Scenario inference failed.");
    } finally {
      setRunning(false);
    }
  }

  const allInputInsufficient = result?.horizons.every((h) => h.status === "INPUT_INSUFFICIENT");

  return (
    <div>
      <div className="illustrative-banner" style={{ color: "var(--accent)", borderColor: "var(--accent-dim)", background: "rgba(79,195,247,0.06)" }}>
        HYPOTHETICAL SCENARIO — NOT HISTORICAL EVIDENCE. Inputs below are hypothetical and run through the same
        frozen FINAL_V2 inference engine as historical replay, but the result is ephemeral: it is never written to
        historical replay storage and never contributes to validation metrics.
      </div>

      <div className="grid-2">
        <div className="panel">
          <div className="panel-title">Hypothetical input</div>
          {schemaState.loading && <Loading />}
          {schemaState.error && <ErrorBox message={schemaState.error} />}
          {schemaState.data && (
            <>
              <p className="text-dim" style={{ fontSize: 11.5, marginTop: -4 }}>
                Only the scientific inputs FINAL_V2's frozen adapter actually requires are exposed here — see{" "}
                <code className="inline">GET /api/scenario/schema</code>.
              </p>
              <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
                {Object.entries(schemaState.data.presets).map(([key, preset]) => (
                  <button key={key} className="nav-tab" style={{ border: "1px solid var(--line)" }} onClick={() => applyPreset(key)}>
                    {preset.label}
                  </button>
                ))}
              </div>
              <div className="kv-list">
                <label className="kv-row">
                  <span className="k">Current track temperature (°C)</span>
                  <input className="case-select v" style={{ width: 110, textAlign: "right" }} type="number" step="0.1"
                    value={trackTemp} onChange={(e) => setTrackTemp(e.target.value)} />
                </label>
                <label className="kv-row">
                  <span className="k">Current ambient temperature (°C)</span>
                  <input className="case-select v" style={{ width: 110, textAlign: "right" }} type="number" step="0.1"
                    value={ambientTemp} onChange={(e) => setAmbientTemp(e.target.value)} />
                </label>
                <label className="kv-row">
                  <span className="k">Hypothetical future ambient (°C)</span>
                  <input className="case-select v" style={{ width: 110, textAlign: "right" }} type="number" step="0.1"
                    value={forecastAmbient} onChange={(e) => setForecastAmbient(e.target.value)} />
                </label>
                <label className="kv-row">
                  <span className="k">Decision time (optional, ISO-8601 UTC)</span>
                  <input className="case-select v" style={{ width: 200, textAlign: "right" }} type="text" placeholder="defaults to now"
                    value={decisionTime} onChange={(e) => setDecisionTime(e.target.value)} />
                </label>
              </div>
              <p className="text-dim" style={{ fontSize: 11, marginTop: 8 }}>
                "Hypothetical future ambient" is a <strong>USER-SUPPLIED HYPOTHETICAL FORECAST</strong> applied
                uniformly at every horizon's target time — it is not tied to any real forecast vintage.
              </p>
              <button className="nav-tab active" style={{ width: "100%", marginTop: 8 }} onClick={runScenario} disabled={running}>
                {running ? "Running…" : "Run Scenario"}
              </button>
              {error && <div style={{ marginTop: 8 }}><ErrorBox message={error} /></div>}
            </>
          )}
        </div>

        <div className="panel">
          <ScientificBoundaryCard />
        </div>
      </div>

      {result && (
        <div className="panel">
          <div className="panel-title">
            <span>Conditional physical outlook — {result.scenario_id}</span>
            <span className="status-badge status-INPUT_INSUFFICIENT">{result.mode}</span>
          </div>
          <p className="text-dim" style={{ fontSize: 11.5, marginTop: -4 }}>{result.note}</p>
          {allInputInsufficient ? (
            <ErrorBox message="INPUT_INSUFFICIENT — enter track temperature, ambient temperature, and a hypothetical future ambient value to run inference." />
          ) : (
            <>
              <OutlookCurveChart horizons={toOutlookHorizons(result)} />
              <div style={{ marginTop: 10 }}>
                <OutlookTable horizons={toOutlookHorizons(result)} />
              </div>
            </>
          )}
          <div className="kv-list" style={{ marginTop: 12 }}>
            <div className="kv-row"><span className="k">Evidence status</span><span className="v">{result.evidence_status}</span></div>
            <div className="kv-row"><span className="k">Forecast provenance</span><span className="v">{result.input.forecast_provenance}</span></div>
            <div className="kv-row"><span className="k">Decision time used</span><span className="v">{result.input.decision_time}</span></div>
            <div className="kv-row"><span className="k">Model hash</span><span className="v">{result.model_hash.slice(0, 16)}…</span></div>
            <div className="kv-row"><span className="k">Input hash</span><span className="v">{result.input_hash.slice(0, 16)}…</span></div>
            <div className="kv-row"><span className="k">Queue-time prediction</span><span className="v">{result.queue_time_prediction}</span></div>
            <div className="kv-row"><span className="k">Retain/withdraw recommendation</span><span className="v">{result.retain_withdraw_recommendation}</span></div>
          </div>
        </div>
      )}
    </div>
  );
}
