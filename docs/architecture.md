# Architecture and modelling contract

## Application boundary

The React/Vite introduction remains separate from the working Streamlit planning
desk. A launch URL joins them; there is no React-to-Python REST API. Both
Streamlit and the CLI call the same Python service:

`validated inputs → adjusted daily schedules → two LP plans → independent checks
→ metrics → recorded RunBundle → review/history/export`

`run_simulation()` never calls Gemini or an operational system. The optional
source-extraction adapter is a separate, explicit user action. The architecture
follows the available v1.1 FINAL PDF's Python/Streamlit modular-monolith direction
while preserving the existing landing page. Local JSON history is not a hosted
database, a user account system or a tamper-proof audit service.

## Inputs and units

The authoritative schemas are `commonroot/schemas.py`; complete editable examples
are `data/demo/network.json`, `data/demo/policy.json` and `scenarios/*.json`.

| Input | Required meaning |
| --- | --- |
| Network metadata | Schema `1.1`, explicit data/generator versions and seed, unit `kg_LPG`, timezone `Asia/Kolkata`. |
| Node | Unique ID, kind, opening stock in kg, daily exogenous supply, aggregate outbound dispatch capacity, active flag, diagram coordinates and provenance. |
| Route | Unique ID and directed endpoints, daily capacity, whole-day lead, distance or explicit `null`, active flag and provenance. |
| Demand | One explicit daily quantity for every district/group pair, including zero-demand pairs; provenance required. |
| Policy | Ordered group tiers, optional daily demand-fraction floors/caps, explicit enforcement/verification flags and illustrative status. |
| Scenario | Event/asset, start and duration, horizon, reduction or delay, demand multiplier, extra route lead, cover threshold, seed and notes. |

Supply, demand and capacities are `kg_LPG/day`; each period is exactly one day.
The solver uses continuous mass, not integer cylinders, vehicles or deliveries.
`tonnes_to_kg()` uses 1,000 kg per metric tonne. `cylinders_to_kg()` requires an
explicit positive fill mass; it never guesses a cylinder size. Uploaded network
JSON must already use the canonical mass unit.

File loading rejects unknown fields, duplicate JSON keys, duplicate IDs/directed
route endpoints, invalid references, self-routes, nonfinite/negative quantities,
missing required values and inconsistent district/group coverage. Missing stock,
supply, capacity, lead or demand is not zero. Unknown route distance is allowed.
Uploads must explicitly identify provenance and units; defaults cannot silently
relabel them as synthetic. File limit: 5,000,000 bytes.

The fixture generator produces 14 nodes, 16 routes (one inactive), six fictional
districts and three illustrative demand groups. Seed 42 produces 62,450 kg/day
demand and 197,220 kg opening stock. Changing the seed varies district demand and
associated district stock, not real geography. SVG coordinates are layout
coordinates; distance values are synthetic logistics assumptions.

## Time, events and exposure

- Days are `1..H`, with `1 ≤ H ≤ 14`. A disruption window must fit in the horizon.
- A shipment dispatched on day `t` arrives on `t + lead_days`, plus applicable
  delays. An arrival after `H` stays in transit and cannot serve in-horizon demand.
- Zero-lead routes permit same-day transfers only in an acyclic zero-lead graph.
  There are no pre-horizon shipments or inferred pipeline stocks.
- **Supply reduction:** reduces only the selected import/refinery source's
  exogenous supply during the window. It does not rescale all supply or stocks.
- **Route closure:** sets only the selected route's dispatch capacity to zero
  during the window. Already-dispatched cargo is not cancelled.
- **Route delay:** adds delay to dispatches made during the event window, not to
  every arrival occurring in that window.
- **Facility outage:** reduces only the selected facility's aggregate dispatch
  limit. It does not destroy inventory or automatically stop local production.
- Demand multiplier applies to every district/group/day. Extra global lead
  applies to every originally active route throughout the horizon.
- Inactive nodes have zero external supply, dispatch and incident route capacity;
  their explicitly declared stock and demand remain in the model.

Exposure follows originally active downstream dependencies; a temporary closure
does not erase the dependency that caused the risk. Route events trace from the
route's target, retaining the selected route as the trigger. One deterministic
shortest path per exposed district is a dependency witness, **not** a shipment,
confirmed shortage, or enumeration of every possible path. Actual quantities are
available in the plan's daily shipment rows.

## Physical constraints

For each node and day:

`closing stock = opening stock + fixed exogenous supply + arrivals − departures − served demand`

Opening stock on the next day equals the previous closing stock. All stocks,
shipments, service and unmet demand are nonnegative. For every district/group/day:

`served + unmet = adjusted demand`

Unmet demand is lost service, **not backlog** that later deliveries can satisfy.
Every route has its own daily capacity; total outbound mass also respects the
source node's dispatch capacity. Global conservation includes cargo still in
transit at the end of the horizon. Summing multi-hop shipments double-counts the
same cargo and must not be interpreted as consumption.

Optional caps apply to each district/group/day. Hard floors apply only when
explicitly enabled and marked verified; conflicting floors fail visibly rather
than being silently relaxed. The verification flag is an input assertion, not
proof of official policy or a permission system. The regular bundled policy has
no hard floors and prioritises essential, household, then business service.

No storage ceilings, handling losses, procurement decisions, vehicle constraints,
costs or emissions factors are inferred. Exogenous supply is fixed, so mass can
accumulate at a blocked source/facility. Those assumptions limit operational use.

## Allocation strategies and checking

Both strategies build independent **OR-Tools GLOP** linear programs on the same
adjusted snapshot and physical constraints. The baseline never borrows the
candidate solution.

1. **Baseline:** pool opening stock plus fixed supply to set proportional
   district/group targets in priority order. Minimise and lock each tier's
   absolute target deviation. Then maximise and lock remaining tier service in
   order. The targets ignore timing/topology; the actual feasible LP does not.
2. **Candidate:** maximise and lock each tier's service in order. Using those
   achieved totals, minimise and lock proportional district/group deviations in
   priority order.
3. **Final logistics stage, both plans:** minimise shipment mass × route distance
   if all distances are known. If any distance is unknown, minimise route-dispatched
   mass instead and leave the distance metric unknown.

These are sequential objectives with equality locks, not a weighted sum that can
trade essential service against a shorter route. Fairness is aggregated over the
horizon; earlier daily service is not a further objective. Nonunique daily plans
can remain even when stage objectives match. A candidate is not guaranteed to
improve total unmet demand relative to the baseline.

Each plan has a shared 10,000 ms solver-stage budget, single-threaded settings and
seed 0. That is **not** a ten-second end-to-end application SLA. After solving, an
independent checker reconstructs arrival, stock, service and capacity constraints
from exported rows with absolute `1e-5 kg` tolerance. Only an `OPTIMAL` plan with
passed checks supplies metrics. Missing solver, infeasibility, timeouts and failed
numerical checks produce diagnostics and empty result tables; no fallback plan is
presented as an optimum.

## Metrics and interpretation

- **Opening snapshot cover:** opening district stock / scenario-adjusted average
  daily district demand.
- **Minimum projected cover:** minimum daily closing district stock / the same
  demand denominator. It is not the opening snapshot.
- **High:** aggregate unmet district demand exceeds numerical tolerance.
- **Watch:** no material unmet demand, but projected cover falls below the
  selected threshold on at least one day.
- **Stable:** computable projected cover never falls below the threshold and no
  material unmet demand is present.
- **Not computable:** cover denominator is zero/unknown. Null is never displayed
  as zero or infinite coverage.
- **Fulfilment:** served / demand; null for zero demand. CSV uses a fraction,
  while UI tables may display a percentage.
- **Distance proxy:** `kg_LPG km`, not vehicle kilometres. Unknown distance on
  even an idle route makes this metric unavailable. Cost/emissions are unavailable.

Risk is a deterministic simulation label, not a probability, forecast confidence
or evidence that a real district is affected. A dependency exposure flag does not
itself make a district High risk. Comparisons clamp differences within the stated
tolerance to zero; no percent reduction is computed when baseline unmet is zero.

## Run lifecycle, history and exports

Sidebar widgets edit a draft. Only a completed run or explicit history reopen
replaces the displayed numerical results. Recording a review updates its metadata
without recomputing. Invalid drafts preserve and label the previous run; a solved
infeasible case is recorded as a failed run with no recommendation.

`RunBundle` contains scenario, network, policy, exact adjusted schedules, both
plans, comparison, affected paths, warnings, reference evidence and review. Its
manifest records a UUID, UTC creation time, app/model/data/generator/policy and
dependency versions, seed, actual solver status, elapsed time and SHA-256 hashes.
The synthetic share counts tagged node/route/demand records, not individual fields.

- The input hash covers network, scenario, policy and adjusted schedules.
- The output hash covers the two complete plan results.
- Run ID, timestamps, elapsed time, review and reference evidence are outside
  those numerical hashes. Reviewing does not change the calculated output hash.
- The store checks the hashes and filename UUID and prevents reusing an existing
  ID for different numerical content. Atomic replacement avoids partial writes;
  files are limited to 15,000,000 bytes. Invalid history entries are omitted.
- Hashes detect inconsistency, **not authenticity**: they are unsigned and can be
  recomputed by a local editor. There is no append-only review audit trail or
  concurrent multi-user transaction/locking guarantee.

Exports read the displayed bundle without rerunning a model. The ZIP contains
`run.json`, the original manifest/inputs/policy, both shipment/balance/service
tables, both district-risk tables, comparison, affected paths and warnings.
Failed/unchecked plans contribute header-only CSVs and retain diagnostics in JSON.
Numbers are not display-rounded; nulls are JSON null/empty CSV cells. Potential
spreadsheet formulas in text are apostrophe-prefixed; exact text remains in JSON.
Exporting the same bundle produces the same ZIP bytes.

Review requires an explicit acknowledgement and a successful checked run. Its
status is `reviewed_simulation_only`; operational action remains `none`.

## Optional source evidence and deployment limits

Gemini extraction requires both server-side configuration values and the user's
explicit send action. Only the bounded pasted excerpt is used as source data;
URLs are not fetched. Strict response validation rejects inferred model parameters,
fabricated quotes, unknown fields and changed authority markers. Literal
substring matching establishes textual grounding, not the truth of a claim.

An explicitly confirmed excerpt is retained as `reviewed_for_reference`, with
`review_scope=reference_only` and `automatic_model_changes=false`. The UI queues
one reference for the next run; the service contract allows up to ten bounded
records. Raw provider responses and environment credentials are not exports.
Stored excerpts can still be sensitive: review before saving or sharing them.

The app is a private local demo: no login/RBAC, tenant isolation, encrypted
history, verified live feeds, operational writeback or production deployment has
been implemented. Do not change the bind address to public access without a
separate deployment/security design. Local paths and review metadata are not a
substitute for an organisational access-control and retention policy.
