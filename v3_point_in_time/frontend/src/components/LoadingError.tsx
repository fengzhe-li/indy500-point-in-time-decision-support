export function Loading({ label = "Loading…" }: { label?: string }) {
  return <div className="loading-box">{label}</div>;
}

/** Renders backend errors -- including scientific abstention that
 * surfaces as a 404 -- as a plain inline message, never a crash. */
export function ErrorBox({ message }: { message: string }) {
  return <div className="error-box">{message}</div>;
}
