import { useEffect, useState } from "preact/hooks";
import type { ApiClient } from "../api";
import { parseRoute, routeHash, type Route } from "../router";
import { SummaryPage } from "./SummaryPage";
import { TraceDetailPage } from "./TraceDetailPage";
import { TraceListPage } from "./TraceListPage";

export interface AppProps {
  client: ApiClient;
}

export function navigate(route: Route): void {
  window.location.hash = routeHash(route);
}

export function App({ client }: AppProps) {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash));

  useEffect(() => {
    const onChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const tracesActive = route.page === "traces" || route.page === "trace";
  return (
    <div class="shell">
      <header class="topbar">
        <a class="brand" href="#/traces">
          <img src={`${import.meta.env.BASE_URL}favicon.svg`} alt="" width={22} height={22} />
          LLM Observability
        </a>
        <nav>
          <a href="#/traces" class={tracesActive ? "active" : ""}>
            Traces
          </a>
          <a href="#/summary" class={route.page === "summary" ? "active" : ""}>
            Summary
          </a>
        </nav>
      </header>
      <main>
        {route.page === "traces" && <TraceListPage client={client} filters={route.filters} />}
        {route.page === "trace" && <TraceDetailPage client={client} traceId={route.traceId} />}
        {route.page === "summary" && <SummaryPage client={client} />}
      </main>
    </div>
  );
}
