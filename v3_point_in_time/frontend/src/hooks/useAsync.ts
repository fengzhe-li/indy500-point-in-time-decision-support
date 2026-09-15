import { useEffect, useRef, useState } from "react";
import { ApiError } from "../services/api";

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

/** Fetch on mount / whenever a dependency changes. Deliberately simple --
 * this app has no client-side caching or optimistic state because every
 * value it shows is an immutable, already-frozen scientific record. */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ data: null, loading: true, error: null });
  const seq = useRef(0);

  useEffect(() => {
    const mySeq = ++seq.current;
    setState((s) => ({ ...s, loading: true, error: null }));
    fn()
      .then((data) => {
        if (seq.current === mySeq) setState({ data, loading: false, error: null });
      })
      .catch((err) => {
        if (seq.current === mySeq) {
          const message = err instanceof ApiError ? err.message : "Unexpected error.";
          setState({ data: null, loading: false, error: message });
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
