# Validation evidence and remaining checks

Recorded **2026-10-10** against the local working directory. This is evidence for
the synthetic demo, not certification of an operational system. The directory is
not a Git repository, so no commit/merge/deployment is asserted.

## Executed checks

Commands below ran from the project root on Windows, CPython 3.12.14, Node 24.19.0,
npm 11.17.0 and uv 0.12.10. Python dependencies are fixed by `uv.lock`; landing
dependencies by `package-lock.json`.

| Check | Command | Observed result |
| --- | --- | --- |
| Full Python + Streamlit test suite | `.venv\Scripts\python.exe -m pytest -q` | **329 passed** in 16.44 s; 3 dependency deprecation warnings. |
| Python lint | `.venv\Scripts\python.exe -m ruff check commonroot app tests` | **All checks passed**. |
| Landing production build | `npm.cmd run build` | **Passed**, Vite 8.3.4; 1,906 modules transformed. |
| CLI fixture evaluation | `.venv\Scripts\python.exe -m commonroot.cli evaluate` | **Five successful checked runs**, results below. |
| Saved-demo replay | `.venv\Scripts\python.exe -m commonroot.cli replay <run_id>` | Executed with the previously saved demo UUID: `same_output_hash=true`, `new_status=success`. |
| Documented uv CLI entry point | `uv run --frozen python -m commonroot.cli run --help` | Passed; printed scenario, preset, network, policy and output arguments. |
| Streamlit health | HTTP GET `http://127.0.0.1:8501/_stcore/health` | **200**, body `ok`. |
| Landing availability | HTTP GET `http://127.0.0.1:5173/` | **200**. |

The three warnings concern OR-Tools SWIG types lacking `__module__` attributes;
they were not suppressed and are not failed checks. The replay placeholder above
must be replaced with an actual local history UUID; it is not a literal argument.

The latest redesign build output was `dist/index.html` plus
`dist/assets/index-DvYwsljG.css` (35.86 kB) and
`dist/assets/index-DbkMaUZO.js` (260.61 kB). Asset hashes change when rebuilt with
different source. A successful Vite build is not a frontend interaction or
accessibility test.

There is no configured standalone JavaScript test/lint command, TypeScript
typecheck, Python static typechecker or coverage-percentage gate. Those checks
are **missing/not run**, not passed implicitly by pytest or Vite.

## Measured fixture results

All fixtures use seed 42, a 14-day horizon, the same synthetic network and regular
illustrative policy. Both plans returned `OPTIMAL` and passed independent
feasibility checking. The quantities below are rounded to whole kg for readability;
exports retain the solver's numeric values.

| Fixture | Baseline unmet kg | Candidate unmet kg | Measured service time (s) |
| --- | ---: | ---: | ---: |
| Normal supply | 0 | 0 | 0.115 |
| Import shock | 194,180 | 194,180 | 0.121 |
| Route closure | 103,610 | 103,610 | 0.127 |
| Route delay | 99,480 | 99,480 | 0.097 |
| Facility outage | 123,220 | 123,220 | 0.101 |

These single local observations include both plans and service orchestration but
exclude CLI process startup, history persistence, browser rendering and downloads.
They are not repeated performance benchmarks, larger-network measurements or a
production latency guarantee. Solver values differ only by floating-point noise
at the total-unmet level; all differences are within `1e-5 kg`. No total-demand
improvement is claimed. Distribution/logistics must be inspected separately.

Reproduce using `commonroot.cli evaluate`. The default import-shock input hash is
`90a3852b2035134a0bd4664ea8f9c13bc96febcceef3c307be27e0301ca2ed4c`.
Elapsed time, run IDs and timestamps naturally change. Exact plan hashes were
reproducible with the same local runtime and locked dependencies; other solver
versions/platforms may select different solutions with equal objective values.

## What the automated tests establish

| Test module | Behaviour checked |
| --- | --- |
| `tests/test_data_scenario.py` | Seeded fixtures, explicit provenance/units, missing/nonfinite/invalid data, references/cycles, file bounds, exact disruption windows and downstream tracing. |
| `tests/test_allocation.py` | Real GLOP stock-flow constraints, lead times/in-transit cargo, lost service, priority/fairness stages, independent baseline, daily floors/caps, infeasibility, missing solver/timeouts and independent detection of tampered rows. |
| `tests/test_evidence_export.py` | Mocked provider boundary, quote grounding, rejected inferred fields/credentials, bounded failures, reference-only confirmation, exact JSON/ZIP, nulls and spreadsheet formula escaping. |
| `tests/test_integration.py` | Offline no-credential simulation, CLI/replay, changed-input outcomes, atomic saved history, review/hash integrity, path traversal rejection and exact current-run exports. |
| `tests/test_ui.py` | Streamlit AppTest: initial computed run, draft/apply separation, invalid-input preservation, failed-plan UI, review/history reopening, district search, disruption presets and zero-demand coverage. |

The core LP is not mocked in its behavioural and integration tests. Gemini HTTP
is mocked: provider adapter coverage does **not** prove that a live account/model
currently accepts the request. AppTest executes Python widget state and assertions,
not a visual browser or a real browser download.

## Redesign pass

The latest UI pass changed the public landing page and Streamlit presentation layer
without changing `commonroot/` solver/data contracts. The landing page now explains
the product as a supply-resilience workbench and uses a field-operations editorial
direction: a static control-room snapshot, explicit run evidence, workflow rows
and a clear simulation-only boundary. The Streamlit desk now has a masthead, run
status rail, six-column KPI ledger, selected-district ribbon, input/review banners,
stronger tabs/controls and responsive table/chart surfaces.

Post-redesign verification: `329 passed`, Ruff passed, `npm.cmd run build` passed,
and both local health endpoints returned HTTP 200. The redesign was not visually
approved in a browser because the built-in browser timed out during both a screenshot
observation and a text observation. This is the remaining visual sign-off item.

## Manual browser checklist

**Status: not completed.** The built-in browser open attempt timed out before
dispatch and no browser tab was returned. HTTP health and AppTest results are
reported separately; neither is substituted for visual verification.

With both services running, complete these checks in a normal browser:

1. At desktop width, open `http://localhost:5173`, use the dashboard links, and
   verify `http://localhost:8501` opens. Check the dashboard's back-link. On a
   narrow viewport, also check the landing hamburger-menu launch link.
2. Inspect the desk at approximately 1440 px and 390 px widths. Verify sidebar
   controls, tabs, text, graph and table scrolling remain usable without clipped
   actions or overlapping labels. Test font fallback with remote fonts disabled.
3. Change demand from 1.0 to 1.3. Confirm the recorded ID/KPIs stay unchanged
   until **Run simulation**, then verify the new input snapshot and run ID.
4. Enter an invalid impact window. Verify the error identifies it and the prior
   result is explicitly labelled as still displayed. Correct it and run again.
5. Inspect a district's stock series, service-by-group table and dependency paths;
   compare baseline/candidate risk and allocation without treating exposure as a
   confirmed shortage. Test a search with no matching district.
6. Run all event presets, then the infeasibility stress policy. Confirm failed
   plans have no recommendation values and **Record review** is disabled.
7. Return to a successful regular-policy run, record an acknowledged review and
   download JSON, CSV and ZIP. Verify each refers to the displayed run, preserves
   nulls/units, and the ZIP opens. Reopen it from history after a page refresh.
8. Navigate with only the keyboard. Verify visible focus, accessible control
   labels, legible contrast and risk status text that does not depend on colour.
9. Without Gemini credentials, verify manual simulations/exports remain usable.
   Live extraction should be checked separately only with authorised account
   configuration and a non-sensitive excerpt. Confirm quotes before saving;
   scenario parameters must not change automatically.

## Known gaps and release boundaries

- **Visual/responsive/accessibility QA:** blocked as above; no screenshots or
  browser-completion claims. The next concrete check is checklist item 1, then
  the desktop/narrow layout and download checks.
- **Live Gemini:** not called with credentials; no provider billing, account
  entitlement or live-model schema compatibility verified.
- **Scale:** measured only the 14-node fixture. No 100-node benchmark, concurrent
  user load test or large-history stress test has been executed.
- **Deployment/security:** loopback demo only. No authentication, authorisation,
  encrypted persistence, signed audit trail, multi-user isolation or deployment
  smoke test. Core numeric work is offline; font loading and explicitly requested
  Gemini extraction are not.
- **Domain validation:** no real facility, stock, demand, policy or logistics
  dataset has been validated. Distances are synthetic; costs/emissions unavailable.
  Floors marked verified are still caller assertions, not official authority.
- **Specification source:** v1.1 FINAL PDF was available; corresponding DOCX was
  missing and was not cross-checked.
- **Existing landing content:** client-only contact-form success, illustrative
  cases/testimonial and placeholder external/legal links remain presentation
  content. They are not working message delivery or independently verified claims.
- **Clean-machine/cross-platform setup:** the lockfiles and documented uv entry
  point work in this Windows environment; a fresh machine and macOS/Linux have not
  been independently tested.

## Local service handoff

The last checks found the landing page on port **5173** and Streamlit on **8501**.
They were launched as local background processes earlier in the session; launch
tool receipts were ambiguous, but the independent health requests succeeded.
Optional process output is under `outputs/vite.stdout.log`,
`outputs/vite.stderr.log`, `outputs/streamlit.stdout.log` and
`outputs/streamlit.stderr.log`. Logs are private local diagnostics, not source
files or proof that all UI interactions passed.

Before launching duplicates, check the URLs. If a service is no longer available,
restart its command from [the README](../README.md#run-locally). A server being
healthy at the recorded check does not mean it will remain running after the
terminal/app/machine stops. No background scheduler or auto-start was installed.

Numeric demo artifacts are in `outputs/demo/run.json` and `outputs/demo/audit.zip`;
history is in `outputs/runs/` unless overridden. Do not publish that directory
without reviewing uploaded data, review notes and source excerpts first.
