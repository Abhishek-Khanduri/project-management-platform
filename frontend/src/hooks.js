import { useCallback, useEffect, useState } from "react";
import { errorMessage } from "./api/client";

/**
 * Loads data from the API and tracks loading / error state.
 *   const { data, loading, error, reload } = useApi(() => api.get("/projects/"), []);
 * `deps` works like useEffect's dependency list: when it changes, data is reloaded.
 */
export function useApi(request, deps) {
  const [state, setState] = useState({ data: null, loading: true, error: null });

  // `request` is a new function on every render, so we re-create `load` only when `deps` change.
  const load = useCallback(() => {
    setState((previous) => ({ ...previous, loading: true, error: null }));
    return request()
      .then((response) => setState({ data: response.data, loading: false, error: null }))
      .catch((error) => setState({ data: null, loading: false, error: errorMessage(error) }));
  }, deps);

  useEffect(() => {
    load();
  }, [load]);

  return { ...state, reload: load };
}

/** Returns `value` only after it has stopped changing for `delay` ms (used for search boxes). */
export function useDebounce(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
