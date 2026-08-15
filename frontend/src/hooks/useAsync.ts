import { useCallback, useEffect, useRef, useState } from "react";

interface AsyncState<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
  reload: () => void;
}

export function useAsync<T>(
  loader: () => Promise<T>,
  deps: ReadonlyArray<unknown>,
): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    error: null,
    loading: true,
    reload: () => undefined,
  });
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const run = useCallback(() => {
    let cancelled = false;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    loaderRef
      .current()
      .then((data) => {
        if (cancelled) return;
        setState({ data, error: null, loading: false, reload: run });
      })
      .catch((error: Error) => {
        if (cancelled) return;
        setState({ data: null, error, loading: false, reload: run });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const cancel = run();
    return () => {
      cancel?.();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { ...state, reload: run };
}
