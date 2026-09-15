import { useMemo, useState } from "react";
import { api } from "../services/api";
import { useAsync } from "../hooks/useAsync";
import { Loading, ErrorBox } from "../components/LoadingError";
import { CaseSelector } from "../components/CaseSelector";
import { OutlookCurveChart } from "../components/OutlookCurveChart";
import { OutlookTable } from "../components/OutlookTable";
import { StatusBadge } from "../components/StatusBadge";
import { ScientificBoundaryCard } from "../components/ScientificBoundaryCard";
import type { ReplayEvent } from "../types/api";

interface Props {
  caseId: string;
  onCaseChange: (id: string) => void;
  onInspectPrediction: (predictionId: string) => void;
}

function findPayload(events: ReplayEvent[], type: string): Record<string, any> | undefined {
  return events.find((e) => e.event_type === type)?.payload as Record<string, any> | undefined;
}

export function PitWallOutlook({ caseId, onCaseChange, onInspectPrediction }: Props) {
  const casesState = useAsync(() => api.listCases(), []);
  const caseState = useAsync(() => api.getCase(caseId), [caseId]);
  const eventsState = useAsync(() => api.getCaseEvents(caseId), [caseId]);
  const outlookState = useAsync(() => api.getCaseOutlook(caseId), [caseId]);
  const scoringState = useAsync(() => api.getCaseScoring(caseId), [caseId]);

  const currentState = useMemo(() => (eventsState.data ? findPayload(eventsState.data, "PHYSICAL_STATE_OBSERVED") : undefined), [eventsState.data]);
  const forecastAt60 = useMemo(
    () => eventsState.data?.find((e) => e.event_type === "FORECAST_AVAILABLE" && (e.payload as any).horizon_minutes === 60)?.payload as Record<string, any> | undefined,
    [eventsState.data]
  );

  return (
    <div>
      <div className="panel">
        <div className="panel-title">
          <span>Pit-wall outlook — historical shadow / research mode</span>
          {casesState.data && <CaseSelector cases={casesState.data} value={caseId} onChange={onCaseChange} />}
        </div>
        {caseState.loading && <Loading />}
        {caseState.error && <ErrorBox message={caseState.error} />}
        {caseState.data && (
          <div className="kv-list" style={{ flexDirection: "row", gap: 24, flexWrap: "wrap" }}>
            <div className="kv-row"><span className="k">Case</span><span className="v">{caseState.data.case_id}</span></div>
            <div className="kv-row"><span className="k">Decision time</span><span className="v">{caseState.data.decision_time}</span></div>
            <div className="kv-row"><span className="k">Category</span><span className="v"><StatusBadge status={caseState.data.category} /></span></div>
          </div>
        )}
      </div>

      <div className="grid-2">
        <div>
          <div className="panel">
            <div className="panel-title">Conditional physical outlook</div>
            <p className="text-dim" style={{ fontSize: 11.5, marginTop: -4 }}>
              "If another opportunity occurs at horizon h…" — this curve is a conditional physical-performance
              estimate, not a forecast of when the next opportunity will occur.
            </p>
            {outlookState.loading && <Loading />}
            {outlookState.error && <ErrorBox message={outlookState.error} />}
            {outlookState.data && (
              <>
                <OutlookCurveChart horizons={outlookState.data.horizons} />
                <div style={{ marginTop: 10 }}>
                  <OutlookTable horizons={outlookState.data.horizons} onSelectPrediction={onInspectPrediction} />
                </div>
              </>
            )}
          </div>

          <div className="panel">
            <div className="panel-title">Applicability</div>
            <div className="kv-list">
              <div className="kv-row">
                <span className="k">Inference support</span>
                <span className="v">
                  <StatusBadge status={outlookState.data?.horizons.some((h) => h.status === "SUPPORTED") ? "SUPPORTED" : "OUT_OF_SUPPORT"} />
                </span>
              </div>
              <div className="kv-row">
                <span className="k">Historical scoring support</span>
                <span className="v">{scoringState.data ? <StatusBadge status={scoringState.data.status} /> : "—"}</span>
              </div>
              {scoringState.data?.note && <p className="text-dim" style={{ fontSize: 11.5, margin: "4px 0 0" }}>{scoringState.data.note}</p>}
            </div>
          </div>
        </div>

        <div>
          <div className="panel">
            <div className="panel-title">Current physical state</div>
            {currentState ? (
              <div className="kv-list">
                <div className="kv-row"><span className="k">Track temperature</span><span className="v">{currentState.current_track_temp_c?.toFixed(1)} °C</span></div>
                <div className="kv-row"><span className="k">Ambient temperature</span><span className="v">{currentState.current_ambient_temp_c?.toFixed(1)} °C</span></div>
                <div className="kv-row"><span className="k">Track-to-ambient gap</span><span className="v">{(currentState.current_track_temp_c - currentState.current_ambient_temp_c).toFixed(1)} °C</span></div>
              </div>
            ) : (
              <Loading />
            )}
          </div>

          <div className="panel">
            <div className="panel-title">Forecast vintage (h = 60 min)</div>
            {forecastAt60 ? (
              <div className="kv-list">
                <div className="kv-row"><span className="k">Issue time</span><span className="v">{forecastAt60.forecast_issue_time}</span></div>
                <div className="kv-row"><span className="k">Valid time</span><span className="v">{forecastAt60.forecast_valid_time}</span></div>
                <div className="kv-row"><span className="k">Target-time mismatch</span><span className="v">{forecastAt60.valid_time_error_minutes?.toFixed(1)} min</span></div>
                <div className="kv-row"><span className="k">Forecast ambient</span><span className="v">{forecastAt60.forecast_ambient_temp_c?.toFixed(1)} °C</span></div>
              </div>
            ) : (
              <p className="text-dim" style={{ fontSize: 11.5 }}>No forecast vintage available for this horizon.</p>
            )}
          </div>

          <div className="panel">
            <ScientificBoundaryCard />
          </div>
        </div>
      </div>
    </div>
  );
}
