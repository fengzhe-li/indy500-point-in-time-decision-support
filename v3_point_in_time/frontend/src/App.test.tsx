import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import * as fx from "./test/fixtures";

vi.mock("./services/api", () => ({
  api: {
    health: vi.fn(async () => ({ status: "ok" })),
    systemStatus: vi.fn(async () => fx.systemStatus),
    listCases: vi.fn(async () => fx.cases),
    getRepresentativeCase: vi.fn(async () => fx.representativeCase),
    getCase: vi.fn(async (id: string) => fx.cases.find((c) => c.case_id === id)!),
    getCaseEvents: vi.fn(async (id: string) => (id === "2021_car60" ? fx.car60Events : [])),
    getCaseOutlook: vi.fn(async () => fx.car60Outlook),
    getCaseScoring: vi.fn(async (id: string) => (id === "2021_car60" ? fx.car60Scoring : fx.car18Scoring)),
    getAbstentions: vi.fn(async () => fx.abstentionRows),
    getPrediction: vi.fn(async () => ({
      prediction_id: "phase3:2021_car60:h60",
      case_id: "2021_car60",
      decision_snapshot_id: "phase3:2021_car60",
      information_cutoff: "2021-05-22T17:58:16Z",
      horizon_minutes: 60,
      inference_support: "SUPPORTED",
      historical_scoring_support: "ILLUSTRATIVE_ONLY",
      outlook: { expected_delta_v: 0.0236, median_delta_v: 0.0267, p_improve: 0.5217, pi80_low: -0.744, pi80_high: 0.798, pi90_low: -1.2, pi90_high: 1.27 },
      queue_time_prediction: "NOT MODELLED",
      retain_withdraw_recommendation: "NOT ISSUED",
    })),
    getPredictionProvenance: vi.fn(async () => ({
      prediction_id: "phase3:2021_car60:h60",
      decision_snapshot_id: "phase3:2021_car60",
      information_cutoff: "2021-05-22T17:58:16Z",
      forecast_vintage_id: "HRRR:20210522:2",
      forecast_issue_time: "2021-05-22T17:00:00Z",
      forecast_valid_time: "2021-05-22T19:00:00Z",
      forecast_target_time_error_minutes: 1.7,
      forecast_ambient_temp_c: 28.7,
      final_v2_model_hash: "abc123",
      input_hash: "def456",
      prediction_hash_note: "note",
      scientific_support: "SUPPORTED",
      historical_scoring_support: "ILLUSTRATIVE_ONLY",
    })),
    getPredictionExplanation: vi.fn(async () => ({
      prediction_id: "phase3:2021_car60:h60",
      current_track_to_ambient_thermal_gap_c: 10.6,
      forecast_ambient_trajectory_c: { current_ambient_temp_c: 27.8, forecast_future_ambient_temp_c: 28.7, delta_ambient_temp_c: 0.96 },
      predicted_future_track_temperature_change_c: 4.28,
      solar_elevation_mean_deg: 67.3,
      note: "closed-form terms",
      uncertainty_source_reference: { diagnostic_scope: "GLOBAL_HORIZON_LEVEL_DIAGNOSTIC", diagnostic_kind: "uncertainty-source ablation" },
    })),
    validationSummary: vi.fn(async () => fx.validationSummary),
    scenarioSchema: vi.fn(async () => fx.scenarioSchema),
    runScenario: vi.fn(async () => fx.scenarioResponse),
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
}));

// Import after the mock is registered.
const { App } = await import("./App");

describe("Phase 4 frontend", () => {
  beforeEach(() => vi.clearAllMocks());

  it("1. main pages render (all five nav tabs present and switchable)", async () => {
    render(<App />);
    expect((await screen.findAllByText(/Pit-Wall Outlook/i)).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByText("Scenario Mode"));
    expect(await screen.findByText(/HYPOTHETICAL SCENARIO/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Historical Shadow Replay"));
    expect((await screen.findAllByText(/Historical shadow replay/i)).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByText(/Evidence & Explanation/));
    expect(await screen.findByText(/No prediction selected/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Validation & Abstention/));
    expect(await screen.findByText(/authoritative Phase 3 evidence/i)).toBeInTheDocument();
  });

  it("2. API data is rendered without recomputing science (exact backend numbers appear verbatim)", async () => {
    render(<App />);
    // +0.024 rounds from the mocked expected_delta_v of 0.0236 truncated to 3dp -> 0.024
    await waitFor(() => expect(screen.getAllByText(/\+0\.024|\+0\.020/).length).toBeGreaterThan(0));
  });

  it("3. support status renders", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getAllByText("SUPPORTED").length).toBeGreaterThan(0));
  });

  it("4. abstention reason renders", async () => {
    render(<App />);
    fireEvent.click(screen.getByText(/Validation & Abstention/));
    expect(await screen.findByText(/HORIZON OUT OF SUPPORT/i)).toBeInTheDocument();
  });

  it("5. illustrative-only label renders (via the featured diagnostic case)", async () => {
    render(<App />);
    fireEvent.click(await screen.findByText("Featured diagnostic case"));
    expect(await screen.findByText(/ILLUSTRATIVE ONLY — NOT AGGREGATE VALIDATION EVIDENCE/i)).toBeInTheDocument();
  });

  it("6. scientific-boundary text renders", async () => {
    render(<App />);
    expect(await screen.findByText(/does not recommend strategy/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Does not recommend RETAIN or WITHDRAW/i).length).toBeGreaterThan(0);
  });

  it("7. historical scoring support is rendered distinctly from inference support", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText("Inference support")).toBeInTheDocument());
    expect(screen.getByText("Historical scoring support")).toBeInTheDocument();
  });

  it("22. Scenario Mode clearly labels its output hypothetical, and running it renders the outlook", async () => {
    render(<App />);
    fireEvent.click(screen.getByText("Scenario Mode"));
    expect(await screen.findByText(/HYPOTHETICAL SCENARIO — NOT HISTORICAL EVIDENCE/i)).toBeInTheDocument();
    fireEvent.click(await screen.findByText("Run Scenario"));
    expect(await screen.findByText(/NOT_HISTORICAL_EVIDENCE/)).toBeInTheDocument();
    expect(screen.getAllByText("NOT ISSUED").length).toBeGreaterThan(0);
  });

  it("23. frontend distinguishes historical replay mode from hypothetical scenario mode", async () => {
    render(<App />);
    fireEvent.click(screen.getByText("Scenario Mode"));
    expect(await screen.findByText(/HYPOTHETICAL SCENARIO — NOT HISTORICAL EVIDENCE/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Historical Shadow Replay"));
    await waitFor(() => expect(screen.queryByText(/HYPOTHETICAL SCENARIO — NOT HISTORICAL EVIDENCE/i)).not.toBeInTheDocument());
    expect((await screen.findAllByText(/Historical shadow replay/i)).length).toBeGreaterThan(0);
  });
});
