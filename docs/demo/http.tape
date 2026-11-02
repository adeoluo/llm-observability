# Records docs/demo/http.gif from a real run: `vhs docs/demo/http.tape` from the repo root.
Output docs/demo/http.gif
Set Shell "bash"
Set FontSize 15
Set Width 1300
Set Height 520
Set Padding 18
Set Theme "Catppuccin Mocha"
Set TypingSpeed 22ms

Hide
Type `export PS1='$ ' && uv sync -q && source .venv/bin/activate` Enter
Sleep 2s
Type `python -m llm_observability sample-traces --count 50 --output /tmp/traces.json` Enter
Sleep 2s
Type `python -m llm_observability serve --port 18340 >/dev/null 2>&1 &` Enter
Sleep 2s
Sleep 8s
Type `clear` Enter
Sleep 1s
Show
Type `curl -s localhost:18340/api/traces -d @/tmp/traces.json; echo` Enter
Sleep 2.5s
Type `curl -s 'localhost:18340/api/traces?status=error&min_latency_ms=1000' | jq -c '{total, ids: [.traces[].trace_id]}'` Enter
Sleep 2.5s
Type `curl -s localhost:18340/api/summary | jq -c '{traces, error_rate, latency_p50_ms, latency_p95_ms, total_cost_usd}'` Enter
Sleep 3s
Type `curl -s localhost:18340/api/summary | jq -c '.by_model[] | {model, calls, cost_usd}'` Enter
Sleep 3.5s
Hide
Type `kill %1` Enter
Type `rm -f /tmp/traces.json` Enter
Sleep 1s
