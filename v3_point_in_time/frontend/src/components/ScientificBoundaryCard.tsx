/** Phase 4 Step 17 — persistent scientific-boundary card. Wording is
 * fixed here, not derived from the API, because it describes what this
 * class of system is (a design/product fact), not a data value. */
export function ScientificBoundaryCard() {
  return (
    <div className="boundary-card">
      <div className="title">Scientific boundary</div>
      <div className="does">
        The system estimates <code className="inline">p(&Delta;v | H = h)</code> — a conditional physical-performance
        outlook for h &isin; {"{15, 30, 60, 90, 120}"} minutes.
      </div>
      <ul>
        <li className="does-not">Does not estimate <code className="inline">P(H = h)</code> (when a future opportunity will occur)</li>
        <li className="does-not">Does not predict queue waiting time</li>
        <li className="does-not">Does not recommend RETAIN or WITHDRAW</li>
        <li className="does-not">Does not calculate an optimal waiting time</li>
      </ul>
    </div>
  );
}
