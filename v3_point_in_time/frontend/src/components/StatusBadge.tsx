interface Props {
  status: string;
  label?: string;
}

/** Never communicates status by color alone -- the text label is the
 * actual status string every time (Phase 4 Step 21). */
export function StatusBadge({ status, label }: Props) {
  const cls = `status-badge status-${status}`;
  return <span className={cls}>{label ?? status}</span>;
}
