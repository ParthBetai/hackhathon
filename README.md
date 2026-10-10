# CommonRoot AI

Local-first LPG supply-disruption decision support. The application computes two
daily allocation plans on the same network, checks their feasibility, and exposes
the underlying stocks, shipments, unmet demand and assumptions for human review.

**This is a synthetic engineering demonstration, not an operational allocation
system.** Infrastructure, geography, demand, distances and priority assumptions
in the bundled fixtures are fictional. Recording a review does not dispatch
stock, authorise rationing or write to any external system.

## Run locally

The existing React landing page and the Python planning desk run as two services.
Both bind to loopback by default; keep them private until deployment protections
are designed. Run all commands from the project root.

### What the website is

CommonRoot is a **supply-resilience workbench**, not a generic AI dashboard. The
landing page explains the operating question and gives people a clear route into
the desk. The desk itself is an admin-style control room for a synthetic LPG
network:

- **Scenario desk:** choose an import shock, route closure, route delay or facility
  outage, then edit the impact window, demand and policy assumptions.
- **Overview:** see available mass, horizon demand, fulfilment, unmet demand,
  elevated districts and the network dependency sketch.
- **District risk:** search and inspect cover trajectories, service, balance rows
  and exposed upstream routes for one district.
- **Compare plans:** compare the independently solved baseline and candidate plans
  on the same physical inputs, including group and district outcomes.
- **Network & inputs:** inspect the exact node/route snapshot and day-by-day
  adjusted schedules behind the displayed run.
- **Review & export:** record a human simulation-only review and download the exact
  JSON, CSV or audit ZIP. Nothing dispatches LPG or writes to another system.

The visual direction is intentionally **field-operations editorial**: warm paper,
deep petrol, mint status marks, ochre pressure signals, compact run metadata and
visible dividers. It is meant to feel like a human-built operations instrument,
not a generic AI-generated SaaS template.

Prerequisites: Node.js/npm and [uv](https://docs.astral.sh/uv/getting-started/installation/).
Validated locally on Windows with Node **24.19.0**, npm **11.17.0**, uv **0.12.10**
and CPython **3.12.14**. The Python project requires Python 3.12;
`.python-version` selects 3.12.14. Use the provided lockfiles.

**Terminal 1 — landing page**

```powershell
npm.cmd ci
npm.cmd run dev
```

Open <http://localhost:5173>. The dashboard launch links open port 8501.
On macOS/Linux use `npm` instead of `npm.cmd` (those platforms have not been
validated in this workspace).

**Terminal 2 — working planning desk**

```powershell
uv sync --frozen
uv run --frozen python -m streamlit run app/streamlit_app.py
```

Open <http://localhost:8501>. Alternatively, on Windows with the environment
already installed:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
```

No API keys are needed for the simulation, solver, history or exports. The core
numeric workflow runs locally without network calls. Web fonts have local font
fallbacks when the network is unavailable. Stop each server with Ctrl+C in its
own terminal.

## Five-minute walkthrough

1. Open the planning desk. It computes and saves the default **Import shock**
   scenario: 50% import-source reduction on days 1–10 of a 14-day horizon.
2. Inspect **Overview**, then **District risk**. Search for a district to inspect
   opening stock, daily closing stock, service by group and first unmet day.
3. Change demand, timing or an asset in the sidebar. The previous recorded run
   stays visible with a **Draft not applied** warning until **Run simulation**.
4. Open **Compare plans**. Both strategies obey the same physical constraints.
   Equal unmet demand is reported as equal, not a fabricated improvement.
5. Choose **Route closure**, **Route delay** or **Facility outage**, then run it.
   **Network & inputs** exposes the exact schedules and dependency paths.
6. Try **Infeasibility stress test** under Policy assumption. A failed plan has
   diagnostics instead of risk/allocation values; review is disabled. Return to
   the regular policy and run again before recording a review.
7. In **Review & export**, acknowledge the simulation boundary, optionally add a
   note, and record the review. Download the exact displayed JSON, risk CSV or
   audit ZIP. **Run history → Reopen selected run** restores the saved snapshot
   and original ID without rerunning the solver.

The **Source review** tab is optional. With explicit Gemini configuration it can
extract literal claims from pasted text for human reference review. It does not
set scenario parameters. Confirmed excerpts attach to the next simulation run;
inspect them before sharing any export.

## Configuration

`.env` is optional. If needed, create it from `.env.example` and edit it locally;
do not commit it. Existing environment variables take precedence.

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | Optional server-side Gemini credential; never put it in a `VITE_` variable. |
| `GEMINI_MODEL` | Explicit model available to your account; no default model is invented. |
| `COMMONROOT_OUTPUT_DIR` | Run history directory; defaults to `outputs/runs`. |
| `VITE_DASHBOARD_URL` | Public dashboard launch URL for Vite; otherwise uses the landing hostname on port 8501. |
| `COMMONROOT_LANDING_URL` | Dashboard back-link; defaults to `http://localhost:5173`. |

Vite embeds its public configuration at build time; restart development or rebuild
after changing it. Streamlit loads the root `.env`. Missing Gemini configuration
leaves manual scenarios fully usable. A supplied source URL is a reference label,
not permission to fetch the page; the user supplies the excerpt. Extraction sends
that excerpt to the configured provider, so never paste secrets or private data
that you are not authorised to send.

Run history is local, unencrypted JSON. It can contain uploaded network data,
review notes and explicitly confirmed excerpts. `outputs/`, `.env*` (except the
example), `.venv/` and Streamlit secrets are ignored by Git; that is not an access
control or backup policy.

## Offline CLI

```powershell
# Compute the saved scenario, persist a new run, and write run.json + audit.zip.
uv run --frozen python -m commonroot.cli run --scenario scenarios/import_shock.json

# Compute all five fixtures and print measured results; also saves new history runs.
uv run --frozen python -m commonroot.cli evaluate

# Print available arguments, including --network, --policy and --out.
uv run --frozen python -m commonroot.cli run --help
```

The default export destination is `outputs/demo/`; a later run replaces those two
export files. History uses separate UUID-named files under `outputs/runs/`. To
avoid replacing a previous export, use a different `--out` directory.

To regenerate a network, run
`uv run --frozen python -m commonroot.cli generate --seed 42 --out outputs/network.json`.
To recompute a saved run, use
`uv run --frozen python -m commonroot.cli replay <run_id>`, replacing `<run_id>`
with the UUID printed by `run` or shown in the desk. Replay compares numeric
output hashes; it does not overwrite the original result. Preserve the same
lockfile/runtime for reproducibility.

## Checks

```powershell
uv run --frozen python -m pytest -q
uv run --frozen python -m ruff check commonroot app tests
npm.cmd run build
```

Latest local verification: **329 tests passed**, Ruff passed, Vite build passed.
See [validation evidence](docs/validation.md) for exact commands, fixture outputs,
coverage boundaries and checks that were **not** completed. `npm.cmd run preview`
can serve the built landing page, but it does not start the Python service.

## Project map

| Location | Responsibility |
| --- | --- |
| `src/`, `index.html`, `vite.config.js` | Preserved React landing page and dashboard launch links. |
| `app/streamlit_app.py` | Draft controls, current-run lifecycle, history and orchestration. |
| `app/views.py`, `app/visuals.py`, `app/style.css` | Report views, diagram and visual system. |
| `app/evidence_view.py` | Optional reference-only source review. |
| `commonroot/schemas.py`, `commonroot/contracts.py` | Typed domain contracts and model errors. |
| `commonroot/data.py`, `commonroot/scenario.py` | Fixture validation, generation, adjusted schedules and exposure tracing. |
| `commonroot/allocation.py`, `commonroot/metrics.py` | Two LP strategies, independent checks and derived metrics. |
| `commonroot/service.py`, `commonroot/store.py` | Run orchestration, hashes, review and atomic local history. |
| `commonroot/export.py`, `commonroot/cli.py` | Exact-run exports and offline entry points. |
| `commonroot/evidence.py` | Bounded optional Gemini adapter; never a numeric decision engine. |
| `data/demo/`, `scenarios/`, `tests/` | Synthetic inputs, reproducible examples and regression tests. |

## Scope and next verification

Read [architecture and model assumptions](docs/architecture.md) before interpreting
results or uploading another dataset. The implementation uses the available
**CommonRoot AI PRD/TRD v1.1 FINAL PDF**. The corresponding DOCX was not available
for cross-checking; no claim of DOCX review is made.

The next release check is the desktop/mobile browser walkthrough in
[validation evidence](docs/validation.md#manual-browser-checklist). Automated
Streamlit tests passed, but browser visual QA was blocked by a tool timeout.
Live Gemini, larger-network performance, production deployment and operational
data validation remain unverified. There is no authentication or multi-user
authorisation. Do not expose this local demo directly to the public internet.

The landing page's contact form is a client-side demonstration, not a delivered
message. Its presentation cases, testimonial and placeholder links are not
verified product evidence. The landing page is preserved separately from the
working planning desk, not represented as an operational integration.
