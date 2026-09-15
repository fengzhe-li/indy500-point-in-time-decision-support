import { useMemo, useState, useEffect } from "react";
import { api } from "../services/api";
import { useAsync } from "../hooks/useAsync";
import { Loading, ErrorBox } from "../components/LoadingError";
import { CaseSelector } from "../components/CaseSelector";
import { EventTimeline } from "../components/EventTimeline";
import { InformationCutoffBanner } from "../components/InformationCutoffBanner";
import { StatusBadge } from "../components/StatusBadge";
import type { ReplayEvent } from "../types/api";

interface Props {
  caseId: string;
  onCaseChange: (id: string) => void;
  onInspectPrediction: (predictionId: string) => void;
}

const LATER_TYPES = new Set(["FUTURE_ATTEMPT_OBSERVED", "PREDICTION_SCORED"]);

export function HistoricalReplay({ caseId, onCaseChange, onInspectPrediction }: Props) {
  const casesState = useAsync(() => api.listCases(), []);
  const caseState = useAsync(() => api.getCase(caseId), [caseId]);
  const eventsState = useAsync(() => api.getCaseEvents(caseId), [caseId]);
  const scoringState = useAsync(() => api.getCaseScoring(caseId), [caseId]);
  const [selected, setSelected] = useState<ReplayEvent | null>(null);

  useEffect(() => setSelected(null), [caseId]);

  const events = eventsState.data ?? [];
  const active = selected ?? events[0] ?? null;
  const isIllustrative = caseState.data?.category === "ILLUSTRATIVE_ONLY";

  const knownAtSelected = useMemo(() => {
    if (!active) return [];
    return events.filter((e) => e.event_time <= active.event_time && !LATER_TYPES.has(e.event_type));
  }, [events, active]);
  const observedLaterThanSelected = useMemo(() => {
    if (!active) return [];
    return events.filter((e) => LATER_TYPES.has(e.event_type) && e.event_time > active.event_time);
  }, [events, active]);

  return (
    <div>
      <div className="panel">
        <div className="panel-title">
          <span>Historical shadow replay</span>
          {casesState.data && <CaseSelector cases={casesState.data} value={caseId} onChange={onCaseChange} />}
        </div>
        {caseState.data && (
          <div className="kv-list" style={{ flexDirection: "row", gap: 24, flexWrap: "wrap" }}>
            <div className="kv-row"><span className="k">Case</span><span className="v">{caseState.data.case_id}</span></div>
            <div className="kv-row"><span className="k">Category</span><span className="v"><StatusBadge status={caseState.data.category} /></span></div>
            <div className="kv-row"><span className="k">Events</span><span className="v">{caseState.data.event_count}</span></div>
          </div>
        )}
      </div>

      {isIllustrative && scoringState.data && (
        <div className="illustrative-banner">
          FEATURED DIAGNOSTIC CASE — ILLUSTRATIVE ONLY — NOT AGGREGATE VALIDATION EVIDENCE. Realised horizon{" "}
          {scoringState.data.realised_horizon_minutes?.toFixed(1)} min vs. nearest calibrated anchor{" "}
          {scoringState.data.anchor_horizon_minutes} min. Forecast-conditioned and realised-environment physical
          expectations were similar; the observed performance change was much larger. This case is retained and
          featured because it demonstrates a genuine evidence/model boundary, not hidden because the result looks
          unfavourable. The cause of that unexplained deviation is not established by this system.
        </div>
      )}

      <div className="grid-2">
        <div className="panel">
          <div className="panel-title">Event sequence ({events.length})</div>
          {eventsState.loading && <Loading />}
          {eventsState.error && <ErrorBox message={eventsState.error} />}
          {events.length > 0 && <EventTimeline events={events} selectedId={active?.event_id ?? null} onSelect={setSelected} />}
        </div>

        <div>
          {active && <InformationCutoffBanner cutoff={active.information_cutoff} />}

          <div className="panel">
            <div className="panel-title">Known at selected timestamp ({knownAtSelected.length} events)</div>
            <div className="kv-list">
              {knownAtSelected.slice(-6).map((e) => (
                <div className="kv-row" key={e.event_id}>
                  <span className="k">{e.event_type.replaceAll("_", " ")}</span>
                  <span className="v">{e.event_time}</span>
                </div>
              ))}
              {knownAtSelected.length === 0 && <span className="text-dim">Nothing known yet at this point in the replay.</span>}
            </div>
          </div>

          {observedLaterThanSelected.length > 0 && (
            <div className="panel">
              <div className="panel-title">Observed later <span className="later-tag">OBSERVED LATER</span></div>
              <div className="kv-list">
                {observedLaterThanSelected.map((e) => (
                  <div className="kv-row" key={e.event_id}>
                    <span className="k">{e.event_type.replaceAll("_", " ")}</span>
                    <span className="v">{e.event_time}</span>
                  </div>
                ))}
              </div>
              <p className="text-dim" style={{ fontSize: 11, marginTop: 8 }}>
                Shown for retrospective comparison only — never part of the information available at the selected replay timestamp.
              </p>
            </div>
          )}

          {active?.event_type === "SHADOW_INFERENCE_ISSUED" && active.prediction_id && (
            <div className="panel">
              <div className="panel-title">Selected event</div>
              <p className="text-dim" style={{ fontSize: 12 }}>Conditional outlook issued for h={String((active.payload as any).horizon_minutes)} min.</p>
              <button
                className="nav-tab active"
                style={{ width: "100%" }}
                onClick={() => onInspectPrediction(active.prediction_id!)}
              >
                Inspect evidence &amp; explanation →
              </button>
            </div>
          )}

          {active?.event_type === "SHADOW_INFERENCE_ABSTAINED" && (
            <div className="panel">
              <div className="panel-title">Selected event — abstention</div>
              <div className="kv-list">
                <div className="kv-row"><span className="k">Scope</span><span className="v">{String((active.payload as any).scope ?? "—")}</span></div>
                <div className="kv-row"><span className="k">Reason code(s)</span><span className="v">{active.abstention_reason_codes.join(", ") || "—"}</span></div>
              </div>
              {(active.payload as any).note && <p className="text-dim" style={{ fontSize: 11.5, marginTop: 8 }}>{(active.payload as any).note}</p>}
            </div>
          )}

          {active?.event_type === "PREDICTION_SCORED" && (
            <div className="panel">
              <div className="panel-title">Selected event — historical scoring</div>
              <div className="kv-list">
                <div className="kv-row"><span className="k">Status</span><span className="v"><StatusBadge status={active.evaluation_status} /></span></div>
                <div className="kv-row"><span className="k">Counts toward aggregate validation</span><span className="v">{String((active.payload as any).counts_toward_aggregate_validation)}</span></div>
                <div className="kv-row"><span className="k">Observed &Delta;v</span><span className="v">{(active.payload as any).observed_delta_v?.toFixed(3)} mph</span></div>
                <div className="kv-row"><span className="k">Predicted E[&Delta;v]</span><span className="v">{(active.payload as any).expected_delta_v?.toFixed(3)} mph</span></div>
              </div>
              {active.prediction_id && (
                <button className="nav-tab active" style={{ width: "100%", marginTop: 8 }} onClick={() => onInspectPrediction(active.prediction_id!)}>
                  Inspect evidence &amp; explanation →
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
