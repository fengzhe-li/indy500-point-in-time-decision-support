import { useEffect, useState } from "react";
import { api } from "./services/api";
import { useAsync } from "./hooks/useAsync";
import { PitWallOutlook } from "./pages/PitWallOutlook";
import { ScenarioMode } from "./pages/ScenarioMode";
import { HistoricalReplay } from "./pages/HistoricalReplay";
import { EvidenceExplanation } from "./pages/EvidenceExplanation";
import { ValidationAbstention } from "./pages/ValidationAbstention";

type Page = "outlook" | "scenario" | "replay" | "evidence" | "validation";

const FEATURED_DIAGNOSTIC_CASE_ID = "2021_car60";
const FALLBACK_DEFAULT_CASE_ID = "2021_car4";

// Phase 5 Step 13 final navigation order.
const TABS: { key: Page; label: string }[] = [
  { key: "outlook", label: "Pit-Wall Outlook" },
  { key: "scenario", label: "Scenario Mode" },
  { key: "replay", label: "Historical Shadow Replay" },
  { key: "evidence", label: "Evidence & Explanation" },
  { key: "validation", label: "Validation & Abstention" },
];

export function App() {
  const [page, setPage] = useState<Page>("outlook");
  // Phase 5 Step 11: default case is resolved from the backend's
  // deterministic, non-outcome-based selection (never the illustrative
  // car-60 case) -- see app/replay_service.py:select_representative_case.
  const [caseId, setCaseId] = useState(FALLBACK_DEFAULT_CASE_ID);
  const [predictionId, setPredictionId] = useState<string | null>(null);
  const statusState = useAsync(() => api.systemStatus(), []);
  const representativeState = useAsync(() => api.getRepresentativeCase(), []);

  useEffect(() => {
    if (representativeState.data) setCaseId(representativeState.data.case_id);
  }, [representativeState.data]);

  function inspectPrediction(id: string) {
    setPredictionId(id);
    setPage("evidence");
  }

  function viewFeaturedDiagnostic() {
    setCaseId(FEATURED_DIAGNOSTIC_CASE_ID);
    setPage("replay");
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-title">
          INDY 500 V3 — POINT-IN-TIME PROBABILISTIC DECISION SUPPORT
          <small>Historical Shadow Replay + Conditional Physical Outlook · independent research prototype, not affiliated with INDYCAR or IMS</small>
        </div>
        <span className="mode-pill">{statusState.data?.operating_mode ?? "HISTORICAL_SHADOW_RESEARCH_MODE"}</span>
        {statusState.data && (
          <span className="mode-pill">
            V2 {statusState.data.v2_integrity} · regression {statusState.data.behavioural_regression}
          </span>
        )}
        <button className="mode-pill" style={{ cursor: "pointer" }} onClick={viewFeaturedDiagnostic} title="2021 car 60 — illustrative-only featured diagnostic case">
          Featured diagnostic case
        </button>
        <nav className="nav-tabs">
          {TABS.map((t) => (
            <button key={t.key} className={`nav-tab${page === t.key ? " active" : ""}`} onClick={() => setPage(t.key)}>
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="app-body">
        {page === "outlook" && <PitWallOutlook caseId={caseId} onCaseChange={setCaseId} onInspectPrediction={inspectPrediction} />}
        {page === "scenario" && <ScenarioMode />}
        {page === "replay" && <HistoricalReplay caseId={caseId} onCaseChange={setCaseId} onInspectPrediction={inspectPrediction} />}
        {page === "evidence" && <EvidenceExplanation predictionId={predictionId} />}
        {page === "validation" && <ValidationAbstention />}
      </main>

      <div className="footer-note">
        This is an independent research decision-support prototype, not affiliated with INDYCAR or Indianapolis Motor
        Speedway. It estimates p(&Delta;v | H=h) for h &isin; {"{15,30,60,90,120}"} minutes. It does not recommend
        strategy, does not predict opportunity timing, and is not connected to a live IndyCar timing feed.
      </div>
    </div>
  );
}
