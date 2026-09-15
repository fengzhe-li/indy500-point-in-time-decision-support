import { api } from "../services/api";
import { useAsync } from "../hooks/useAsync";
import { Loading, ErrorBox } from "../components/LoadingError";
import { StatusBadge } from "../components/StatusBadge";
import { AbstentionBarChart } from "../components/AbstentionBarChart";
import { ScientificBoundaryCard } from "../components/ScientificBoundaryCard";

export function ValidationAbstention() {
  const summaryState = useAsync(() => api.validationSummary(), []);
  const casesState = useAsync(() => api.listCases(), []);
  const abstentionsState = useAsync(() => api.getAbstentions(), []);

  const s = summaryState.data;

  return (
    <div>
      <div className="panel">
        <div className="panel-title">Validation, applicability &amp; abstention — authoritative Phase 3 evidence</div>
        {summaryState.loading && <Loading />}
        {summaryState.error && <ErrorBox message={summaryState.error} />}
        {s && (
          <div className="grid-3">
            <div className="kv-list">
              <div className="kv-row"><span className="k">Total transitions considered</span><span className="v">{s.total_transitions_considered}</span></div>
              <div className="kv-row"><span className="k">Candidate cases with replay timeline</span><span className="v">{s.candidate_cases_with_replay_timeline}</span></div>
              <div className="kv-row"><span className="k">Conditional inference supported</span><span className="v">{s.conditional_inference_supported}</span></div>
            </div>
            <div className="kv-list">
              <div className="kv-row"><span className="k">Historical scoring formally supported</span><span className="v">{s.historical_scoring_formally_supported}</span></div>
              <div className="kv-row"><span className="k">Illustrative only</span><span className="v">{s.illustrative_only}</span></div>
              <div className="kv-row"><span className="k">Abstained (insufficient timestamp)</span><span className="v">{s.abstained_insufficient_timestamp}</span></div>
            </div>
            <div className="kv-list">
              <div className="kv-row"><span className="k">Phase 3 freeze status</span><span className="v">{s.phase3_freeze_status}</span></div>
              <div className="kv-row"><span className="k">Historical scoring validation</span><span className="v"><StatusBadge status="NOT_ESTABLISHED" /></span></div>
            </div>
          </div>
        )}
        {s && <p className="text-dim" style={{ fontSize: 11.5, marginTop: 10 }}>{s.note}</p>}
      </div>

      <div className="grid-2">
        <div className="panel">
          <div className="panel-title">Case outcomes</div>
          {s && (
            <AbstentionBarChart
              rows={[
                { label: "Conditional outlook supported", count: s.conditional_inference_supported, kind: "supported" },
                { label: "Illustrative only", count: s.illustrative_only, kind: "illustrative" },
                { label: "Abstained — insufficient timestamp", count: s.abstained_insufficient_timestamp, kind: "abstained" },
                { label: "Abstained — out of support", count: s.abstained_out_of_support, kind: "abstained" },
                { label: "Abstained — forecast unavailable", count: s.abstained_forecast_unavailable, kind: "abstained" },
              ]}
            />
          )}
        </div>

        <div className="panel">
          <div className="panel-title">Abstention reason breakdown</div>
          {s && Object.keys(s.abstention_reason_counts).length > 0 ? (
            <AbstentionBarChart
              rows={Object.entries(s.abstention_reason_counts).map(([label, count]) => ({
                label: label.replaceAll("_", " "),
                count,
                kind: "abstained" as const,
              }))}
            />
          ) : (
            <Loading />
          )}
          <p className="text-dim" style={{ fontSize: 11, marginTop: 8 }}>
            Abstention is a scientific feature of this system, not an application error: each row above is a
            case where the evidence did not justify an inference or a historical scoring claim, and the reason
            is recorded rather than hidden.
          </p>
        </div>
      </div>

      <div className="panel">
        <div className="panel-title">All replay cases</div>
        {casesState.data && (
          <table className="data-table">
            <thead>
              <tr>
                <th>Case</th>
                <th>Category</th>
                <th>Historical scoring</th>
                <th>Realised horizon (min)</th>
                <th>Observed &Delta;v</th>
              </tr>
            </thead>
            <tbody>
              {casesState.data.map((c) => (
                <tr key={c.case_id}>
                  <td>{c.case_id}</td>
                  <td><StatusBadge status={c.category} /></td>
                  <td><StatusBadge status={c.historical_scoring_status} /></td>
                  <td>{c.realised_horizon_minutes?.toFixed(1) ?? "—"}</td>
                  <td>{c.observed_delta_v != null ? `${c.observed_delta_v >= 0 ? "+" : ""}${c.observed_delta_v.toFixed(3)}` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {abstentionsState.data && (
          <p className="text-dim" style={{ fontSize: 11, marginTop: 10 }}>
            31 additional pre-candidate transitions were excluded before a decision timestamp could be defensibly
            constructed (ambiguous multi-attempt pairing or no usable timestamp) and have no replay timeline; see
            the abstention reason breakdown above.
          </p>
        )}
      </div>

      <div className="panel">
        <ScientificBoundaryCard />
      </div>
    </div>
  );
}
