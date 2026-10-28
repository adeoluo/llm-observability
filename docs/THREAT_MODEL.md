# Threat Model - LLM Observability

## Assets

- Integrity of trace and metric data.
- Any sensitive content a caller places into span attributes.

## Trust boundaries

- **Span attributes are caller-provided data.** They are stored and may be exported, so
  they cross a boundary when traces leave the process.

## Threats and mitigations

| Threat | Vector | Impact | Mitigation |
|---|---|---|---|
| Sensitive data in traces | Caller records secrets or PII as attributes | Data leak on export | Documented guidance to redact before export; JSON export is explicit and inspectable |
| Misleading cost figures | Stale or wrong price list | Bad decisions | Prices injected and overridable; unknown models cost zero rather than guessing |
| Resource growth | Unbounded span accumulation | Memory growth | Traces are grouped and can be drained by the caller; single-process scope is documented |
| Supply-chain compromise | Malicious dependency | Code execution | Zero runtime dependencies; Dependabot and CodeQL in continuous integration |

## Residual risk

The library cannot know whether an attribute value is sensitive; preventing leakage of
caller-recorded content on export remains the operator's responsibility.
