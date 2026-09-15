import type { ReplayCaseSummary } from "../types/api";

interface Props {
  cases: ReplayCaseSummary[];
  value: string;
  onChange: (caseId: string) => void;
}

export function CaseSelector({ cases, value, onChange }: Props) {
  return (
    <select className="case-select" value={value} onChange={(e) => onChange(e.target.value)}>
      {cases.map((c) => (
        <option key={c.case_id} value={c.case_id}>
          {c.case_id} — {c.category === "ILLUSTRATIVE_ONLY" ? "illustrative" : "conditional outlook only"}
        </option>
      ))}
    </select>
  );
}
