import type { ReplayEvent } from "../types/api";

interface Props {
  events: ReplayEvent[];
  selectedId: string | null;
  onSelect: (event: ReplayEvent) => void;
}

const LATER_TYPES = new Set(["FUTURE_ATTEMPT_OBSERVED", "PREDICTION_SCORED"]);

function dotClass(e: ReplayEvent): string {
  if (e.event_type === "SHADOW_INFERENCE_ISSUED") return "dot issued";
  if (e.event_type === "SHADOW_INFERENCE_ABSTAINED") return "dot abstained";
  if (e.event_type === "PREDICTION_SCORED") return "dot scored";
  if (e.event_type === "FUTURE_ATTEMPT_OBSERVED") return "dot observed";
  return "dot";
}

function label(e: ReplayEvent): string {
  const p = e.payload as Record<string, any>;
  switch (e.event_type) {
    case "PHYSICAL_STATE_OBSERVED":
      return `Physical state observed — track ${p.current_track_temp_c?.toFixed?.(1)}°C, ambient ${p.current_ambient_temp_c?.toFixed?.(1)}°C`;
    case "FORECAST_AVAILABLE":
      return `Forecast available for h=${p.horizon_minutes} min (issued ${p.forecast_issue_time})`;
    case "SHADOW_INFERENCE_ISSUED":
      return `Conditional outlook issued — h=${p.horizon_minutes} min, E[Δv]=${p.expected_delta_v >= 0 ? "+" : ""}${p.expected_delta_v?.toFixed(3)} mph`;
    case "SHADOW_INFERENCE_ABSTAINED":
      return `Abstained (${p.scope ?? "?"}) — ${e.abstention_reason_codes.join(", ")}`;
    case "FUTURE_ATTEMPT_OBSERVED":
      return `Future attempt observed — Δv=${p.observed_delta_v >= 0 ? "+" : ""}${p.observed_delta_v?.toFixed(3)} mph`;
    case "PREDICTION_SCORED":
      return `Prediction scored (h=${p.anchor_horizon_minutes} min) — ${e.evaluation_status}`;
    case "APPLICABILITY_CHANGED":
      return `Case category: ${p.category}`;
    default:
      return e.event_type;
  }
}

export function EventTimeline({ events, selectedId, onSelect }: Props) {
  return (
    <div className="timeline">
      {events.map((e) => (
        <div
          key={e.event_id}
          className={`timeline-item${e.event_id === selectedId ? " selected" : ""}`}
          onClick={() => onSelect(e)}
        >
          <div className="t">{e.event_time.replace("T", " ").replace("Z", "")}</div>
          <div className={dotClass(e)} />
          <div>
            <div className="label">
              {e.event_type.replaceAll("_", " ")}
              {LATER_TYPES.has(e.event_type) && <span className="later-tag">OBSERVED LATER</span>}
            </div>
            <div className="sub">{label(e)}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
