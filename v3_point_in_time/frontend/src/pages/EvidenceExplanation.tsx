import { api } from "../services/api";
import { useAsync } from "../hooks/useAsync";
import { Loading, ErrorBox } from "../components/LoadingError";
import { StatusBadge } from "../components/StatusBadge";
import { ProvenancePanel } from "../components/ProvenancePanel";
import { ExplanationPanel } from "../components/ExplanationPanel";

interface Props {
  predictionId: string | null;
}

export function EvidenceExplanation({ predictionId }: Props) {
  const predState = useAsync(() => (predictionId ? api.getPrediction(predictionId) : Promise.resolve(null)), [predictionId]);
  const provState = useAsync(() => (predictionId ? api.getPredictionProvenance(predictionId) : Promise.resolve(null)), [predictionId]);
  const explState = useAsync(() => (predictionId ? api.getPredictionExplanation(predictionId) : Promise.resolve(null)), [predictionId]);

  if (!predictionId) {
    return (
      <div className="panel">
        <div className="panel-title">Evidence &amp; explanation</div>
        <p className="text-dim">
          No prediction selected. Click a horizon row on the Pit-Wall Outlook page, or a
          "Conditional outlook issued" event on the Historical Shadow Replay page, to inspect its full
          provenance and physical explanation here.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="panel">
        <div className="panel-title">Prediction {predictionId}</div>
        {predState.loading && <Loading />}
        {predState.error && <ErrorBox message={predState.error} />}
        {predState.data && (
          <div className="kv-list" style={{ flexDirection: "row", gap: 24, flexWrap: "wrap" }}>
            <div className="kv-row"><span className="k">Case</span><span className="v">{predState.data.case_id}</span></div>
            <div className="kv-row"><span className="k">Horizon</span><span className="v">{predState.data.horizon_minutes} min</span></div>
            <div className="kv-row"><span className="k">Inference support</span><span className="v"><StatusBadge status={predState.data.inference_support} /></span></div>
            <div className="kv-row"><span className="k">Historical scoring support</span><span className="v"><StatusBadge status={predState.data.historical_scoring_support} /></span></div>
          </div>
        )}
        {predState.data && (
          <div className="kv-list" style={{ marginTop: 10 }}>
            <div className="kv-row"><span className="k">E[&Delta;v]</span><span className="v">{predState.data.outlook.expected_delta_v.toFixed(3)} mph</span></div>
            <div className="kv-row"><span className="k">Median &Delta;v</span><span className="v">{predState.data.outlook.median_delta_v.toFixed(3)} mph</span></div>
            <div className="kv-row"><span className="k">P(improve)</span><span className="v">{(predState.data.outlook.p_improve * 100).toFixed(1)}%</span></div>
            <div className="kv-row"><span className="k">80% predictive interval</span><span className="v">[{predState.data.outlook.pi80_low.toFixed(3)}, {predState.data.outlook.pi80_high.toFixed(3)}] mph</span></div>
            <div className="kv-row"><span className="k">90% predictive interval</span><span className="v">[{predState.data.outlook.pi90_low.toFixed(3)}, {predState.data.outlook.pi90_high.toFixed(3)}] mph</span></div>
            <div className="kv-row"><span className="k">Queue-time prediction</span><span className="v">{predState.data.queue_time_prediction}</span></div>
            <div className="kv-row"><span className="k">Retain/withdraw recommendation</span><span className="v">{predState.data.retain_withdraw_recommendation}</span></div>
          </div>
        )}
      </div>

      <div className="grid-2">
        <div className="panel">
          <div className="panel-title">Provenance</div>
          {provState.loading && <Loading />}
          {provState.error && <ErrorBox message={provState.error} />}
          {provState.data && <ProvenancePanel p={provState.data} />}
        </div>

        <div className="panel">
          <div className="panel-title">Physical explanation</div>
          {explState.loading && <Loading />}
          {explState.error && <ErrorBox message={explState.error} />}
          {explState.data && <ExplanationPanel e={explState.data} />}
        </div>
      </div>
    </div>
  );
}
