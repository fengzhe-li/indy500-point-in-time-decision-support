interface Row {
  label: string;
  count: number;
  kind: "supported" | "illustrative" | "abstained";
}

export function AbstentionBarChart({ rows }: { rows: Row[] }) {
  const max = Math.max(1, ...rows.map((r) => r.count));
  const colorClass: Record<Row["kind"], string> = {
    supported: "bar-fill good",
    illustrative: "bar-fill warn",
    abstained: "bar-fill bad",
  };
  return (
    <div>
      {rows.map((r) => (
        <div className="bar-row" key={r.label}>
          <span className="text-1">{r.label}</span>
          <div className="bar-track">
            <div className={colorClass[r.kind]} style={{ width: `${(r.count / max) * 100}%` }} />
          </div>
          <span className="mono" style={{ textAlign: "right" }}>{r.count}</span>
        </div>
      ))}
    </div>
  );
}
