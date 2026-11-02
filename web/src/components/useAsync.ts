import { useEffect, useState } from "preact/hooks";

export type AsyncState<T> =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; value: T };

/** Run `load` whenever `deps` change and expose its loading, error, or ready state. */
export function useAsync<T>(load: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ kind: "loading" });
  useEffect(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    load().then(
      (value) => {
        if (!cancelled) setState({ kind: "ready", value });
      },
      (error: unknown) => {
        if (!cancelled) {
          setState({ kind: "error", message: error instanceof Error ? error.message : String(error) });
        }
      },
    );
    return () => {
      cancelled = true;
    };
  }, deps);
  return state;
}
