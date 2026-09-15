// Thin fetch wrapper. This is the ONLY place the frontend talks to the
// backend. No component reads a CSV/JSON file directly, and nothing
// here recomputes a scientific value -- every function is a 1:1 GET
// against a FastAPI route.
import type {
  SystemStatus,
  ReplayCaseSummary,
  ReplayEvent,
  CaseOutlook,
  CaseScoring,
  PredictionDetail,
  PredictionProvenance,
  PredictionExplanation,
  ValidationSummary,
  AbstentionSummaryRow,
  RepresentativeCase,
  ScenarioRequest,
  ScenarioResponse,
  ScenarioSchema,
} from "../types/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function getJSON<T>(path: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`);
  } catch {
    throw new ApiError(0, "Cannot reach the V3 API. Is the backend running (scripts/run_v3_app.sh)?");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Cannot reach the V3 API. Is the backend running (scripts/run_v3_app.sh)?");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const parsed = await res.json();
      detail = parsed.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => getJSON<{ status: string }>("/health"),
  systemStatus: () => getJSON<SystemStatus>("/system/status"),
  listCases: () => getJSON<ReplayCaseSummary[]>("/replay/cases"),
  getRepresentativeCase: () => getJSON<RepresentativeCase>("/replay/cases/representative"),
  getCase: (caseId: string) => getJSON<ReplayCaseSummary>(`/replay/cases/${encodeURIComponent(caseId)}`),
  getCaseEvents: (caseId: string) => getJSON<ReplayEvent[]>(`/replay/cases/${encodeURIComponent(caseId)}/events`),
  getCaseOutlook: (caseId: string) => getJSON<CaseOutlook>(`/replay/cases/${encodeURIComponent(caseId)}/outlook`),
  getCaseScoring: (caseId: string) => getJSON<CaseScoring>(`/replay/cases/${encodeURIComponent(caseId)}/scoring`),
  getAbstentions: () => getJSON<AbstentionSummaryRow[]>("/replay/abstentions"),
  getPrediction: (predictionId: string) => getJSON<PredictionDetail>(`/predictions/${encodeURIComponent(predictionId)}`),
  getPredictionProvenance: (predictionId: string) =>
    getJSON<PredictionProvenance>(`/predictions/${encodeURIComponent(predictionId)}/provenance`),
  getPredictionExplanation: (predictionId: string) =>
    getJSON<PredictionExplanation>(`/predictions/${encodeURIComponent(predictionId)}/explanation`),
  validationSummary: () => getJSON<ValidationSummary>("/validation/summary"),
  scenarioSchema: () => getJSON<ScenarioSchema>("/scenario/schema"),
  runScenario: (req: ScenarioRequest) => postJSON<ScenarioResponse>("/scenario/infer", req),
};
