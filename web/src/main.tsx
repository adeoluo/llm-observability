import { render } from "preact";
import { App } from "./components/App";
import { createApiClient } from "./api";
import "./styles.css";

const root = document.getElementById("app");
if (root) {
  const client = createApiClient((input, init) => fetch(input, init));
  render(<App client={client} />, root);
}
