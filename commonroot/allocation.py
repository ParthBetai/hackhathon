"""Deterministic, time-expanded continuous LP allocation with OR-Tools GLOP.

Both strategies build their own LP over the identical immutable input snapshot.
Every node has I[1..H+1], every edge/day has bounded flow, and every district /
group/day has served and *lost* unmet demand. There is no demand backlog. Q is
fixed, same-day transshipment is allowed, and post-horizon arrivals remain cargo
in transit. No result is published without optimal solves and an independent
check of the exported rows. All physical comparisons use absolute 1e-5 kg
tolerance; the solver itself uses tighter primal/dual tolerances.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from math import fsum, isfinite
from numbers import Real
from time import monotonic
from typing import Any, Literal

from commonroot.contracts import ModelError, ModelInputs
from commonroot.metrics import (
    TOLERANCE,
    compute_metrics,
    district_risks,
    route_peak_utilisation,
)
from commonroot.schemas import Balance, Feasibility, PlanResult, ServiceRow, Shipment

try:
    from ortools.linear_solver import pywraplp
except (ImportError, OSError):
    pywraplp = None

SOLVER_TIME_LIMIT_MS = 10_000  # Shared wall-clock budget across all stages of one plan.


def _quantity(value: Any) -> bool:
    return (
        isinstance(value, Real) and not isinstance(value, bool) and isfinite(value) and value >= 0
    )


def _validate_inputs(inputs: ModelInputs) -> None:
    """Require a complete snapshot; never replace missing physical inputs with 0."""
    horizon = inputs.scenario.horizon_days
    nodes = sorted(inputs.network.nodes, key=lambda node: node.id)
    edges = sorted(inputs.network.edges, key=lambda edge: edge.id)
    demand_pairs = {(row.district_id, row.group) for row in inputs.network.demands}
    groups = [group for tier in inputs.policy.tiers for group in tier]
    if set(group for _, group in demand_pairs) - set(groups):
        raise ModelError("INPUT_VALIDATION", "Every demand group must appear in a policy tier.")
    if inputs.policy.enforce_minimums and not inputs.policy.minimums_verified:
        raise ModelError("INPUT_VALIDATION", "Hard minimums require explicit verification.")
    for node in nodes:
        if node.initial_stock is None:
            raise ModelError("DATA_INCOMPLETE", f"Initial stock is unknown at node {node.id}.")
        if not _quantity(node.initial_stock):
            raise ModelError("INPUT_VALIDATION", f"Invalid initial stock at node {node.id}.")
    expected_node_days = {(node.id, day) for node in nodes for day in range(1, horizon + 1)}
    expected_edge_days = {(edge.id, day) for edge in edges for day in range(1, horizon + 1)}
    expected_demand = {
        (district, group, day) for district, group in demand_pairs for day in range(1, horizon + 1)
    }
    tables = (
        ("supply", inputs.supply, expected_node_days),
        ("dispatch_capacity", inputs.dispatch_capacity, expected_node_days),
        ("edge_capacity", inputs.edge_capacity, expected_edge_days),
        ("arrival_day", inputs.arrival_day, expected_edge_days),
        ("demand", inputs.demand, expected_demand),
    )
    for name, values, expected in tables:
        missing = expected - values.keys()
        extra = values.keys() - expected
        if missing:
            sample = sorted(missing, key=repr)[:5]
            raise ModelError(
                "DATA_INCOMPLETE", f"{name} is missing {len(missing)} row(s): {sample}."
            )
        if extra:
            raise ModelError(
                "INPUT_VALIDATION", f"{name} has unexpected keys: {sorted(extra, key=repr)[:5]}."
            )
        for key in sorted(expected):
            value = values[key]
            if name == "arrival_day":
                if not isinstance(value, int) or isinstance(value, bool) or value < key[1]:
                    raise ModelError(
                        "INPUT_VALIDATION", f"arrival_day{key} must be an integer >= departure day."
                    )
            elif value is None:
                raise ModelError("DATA_INCOMPLETE", f"{name}{key} is unknown.")
            elif not _quantity(value):
                raise ModelError("INPUT_VALIDATION", f"{name}{key} must be finite and nonnegative.")


def check_feasibility(
    inputs: ModelInputs, plan: PlanResult, *, tolerance: float = TOLERANCE
) -> Feasibility:
    """Independently recompute constraints from exported rows, without OR-Tools.

    Full edge/day rows (including zeros), node/day balances and demand/day rows
    are required. Metadata is cross-checked against the snapshot before trusting
    it. Stock is recomputed from fixed initial stock, fixed Q and actual shipment
    and service rows, rather than trusting a reported closing balance. Global
    conservation includes cargo arriving after H and does not count multi-hop
    shipments as separate consumption.
    """
    if not isfinite(tolerance) or tolerance <= 0:
        raise ValueError("Feasibility tolerance must be finite and positive.")
    violations: list[str] = []
    max_error = 0.0
    try:
        _validate_inputs(inputs)
    except ModelError as exc:
        return Feasibility(passed=False, violations=[f"{exc.code}: {exc}"], tolerance=tolerance)
    horizon = inputs.scenario.horizon_days
    nodes = {node.id: node for node in inputs.network.nodes}
    edges = {edge.id: edge for edge in inputs.network.edges}

    def index_rows(rows, key, expected, label, fields):
        indexed = {}
        for row in rows:
            row_key = key(row)
            if row_key in indexed:
                violations.append(f"duplicate {label}{row_key}")
            indexed[row_key] = row
            for name in fields:
                value = getattr(row, name)
                if not isinstance(value, Real) or not isfinite(value):
                    violations.append(f"nonfinite {label}{row_key}.{name}")
        missing = expected - indexed.keys()
        extra = indexed.keys() - expected
        if missing:
            violations.append(f"missing {label} rows: {sorted(missing)[:5]} ({len(missing)} total)")
        if extra:
            violations.append(f"unexpected {label} rows: {sorted(extra)[:5]}")
        return indexed

    shipment_rows = index_rows(
        plan.shipments,
        lambda row: (row.edge_id, row.day),
        set(inputs.edge_capacity),
        "shipment",
        ("quantity", "capacity"),
    )
    balance_rows = index_rows(
        plan.balances,
        lambda row: (row.node_id, row.day),
        set(inputs.supply),
        "balance",
        ("opening", "supply", "arrivals", "departures", "served", "closing"),
    )
    service_rows = index_rows(
        plan.service,
        lambda row: (row.district_id, row.group, row.day),
        set(inputs.demand),
        "service",
        ("demand", "served", "unmet"),
    )
    if violations:
        return Feasibility(passed=False, violations=violations, tolerance=tolerance)

    def close(actual, expected, label, *, balance=False):
        nonlocal max_error
        error = abs(actual - expected)
        if balance:
            max_error = max(max_error, error)
        if error > tolerance:
            violations.append(f"{label}: expected {expected:.12g}, got {actual:.12g}")

    arrivals: dict[tuple[str, int], list[float]] = defaultdict(list)
    departures: dict[tuple[str, int], list[float]] = defaultdict(list)
    served: dict[tuple[str, int], list[float]] = defaultdict(list)
    transit = []
    for key in sorted(shipment_rows):
        row = shipment_rows[key]
        edge = edges[row.edge_id]
        if row.source != edge.source or row.target != edge.target:
            violations.append(f"route_endpoints{key} do not match the network")
        arrival = inputs.arrival_day[key]
        if row.arrival_day != arrival:
            violations.append(f"arrival_day{key}: expected {arrival}, got {row.arrival_day}")
        close(row.capacity, inputs.edge_capacity[key], f"route_capacity_metadata{key}")
        if edge.distance_km is None:
            if row.distance_km is not None:
                violations.append(f"distance{key} must remain unknown")
        elif row.distance_km is None or not isfinite(row.distance_km):
            violations.append(f"distance{key} is missing/nonfinite")
        else:
            close(row.distance_km, edge.distance_km, f"distance{key}")
        if row.quantity < -tolerance:
            violations.append(f"flow_nonnegative{key}: {row.quantity:.12g}")
        if row.quantity > inputs.edge_capacity[key] + tolerance:
            violations.append(
                f"route_capacity{key}: shipment exceeds {inputs.edge_capacity[key]:.12g}"
            )
        departures[edge.source, row.day].append(row.quantity)
        if arrival <= horizon:
            arrivals[edge.target, arrival].append(row.quantity)
        else:
            transit.append(row.quantity)

    for key in sorted(service_rows):
        row = service_rows[key]
        demand = inputs.demand[key]
        close(row.demand, demand, f"demand_metadata{key}")
        close(row.served + row.unmet, demand, f"served_plus_unmet{key}")
        if row.served < -tolerance or row.unmet < -tolerance:
            violations.append(f"service_nonnegative{key}")
        if row.served > demand + tolerance or row.unmet > demand + tolerance:
            violations.append(f"demand_limit{key}")
        cap = inputs.policy.caps.get(row.group, 1.0) * demand
        if row.served > cap + tolerance:
            violations.append(f"policy_cap{key}: served {row.served:.12g} exceeds {cap:.12g}")
        if inputs.policy.enforce_minimums and inputs.policy.minimums_verified:
            floor = inputs.policy.minimum_fractions.get(row.group, 0.0) * demand
            if row.served < floor - tolerance:
                violations.append(
                    f"policy_minimum{key}: served {row.served:.12g} below {floor:.12g}"
                )
        served[row.district_id, row.day].append(row.served)

    for node_id in sorted(nodes):
        opening = nodes[node_id].initial_stock
        for day in range(1, horizon + 1):
            key = node_id, day
            row = balance_rows[key]
            incoming = fsum(arrivals[key])
            outgoing = fsum(departures[key])
            delivered = fsum(served[key])
            closing = fsum((opening, inputs.supply[key], incoming, -outgoing, -delivered))
            close(row.opening, opening, f"opening_inventory{key}", balance=True)
            close(row.supply, inputs.supply[key], f"fixed_supply{key}", balance=True)
            close(row.arrivals, incoming, f"arrivals{key}", balance=True)
            close(row.departures, outgoing, f"departures{key}", balance=True)
            close(row.served, delivered, f"district_service{key}", balance=True)
            close(row.closing, closing, f"inventory_balance{key}", balance=True)
            close(
                fsum((row.opening, row.supply, row.arrivals, -row.departures, -row.served)),
                row.closing,
                f"exported_balance_identity{key}",
                balance=True,
            )
            for name in ("opening", "supply", "arrivals", "departures", "served", "closing"):
                if getattr(row, name) < -tolerance:
                    violations.append(f"nonnegative_balance{key}.{name}")
            if closing < -tolerance:
                violations.append(f"recomputed_inventory_nonnegative{key}: {closing:.12g}")
            if outgoing > inputs.dispatch_capacity[key] + tolerance:
                violations.append(
                    f"dispatch_capacity{key}: {outgoing:.12g} exceeds {inputs.dispatch_capacity[key]:.12g}"
                )
            opening = closing

    available = fsum(node.initial_stock for node in nodes.values()) + fsum(inputs.supply.values())
    accounted = fsum(
        [row.served for row in service_rows.values()]
        + [balance_rows[node_id, horizon].closing for node_id in sorted(nodes)]
        + transit
    )
    close(accounted, available, "global_stock_service_in_transit_balance", balance=True)
    return Feasibility(
        passed=not violations,
        violations=violations,
        max_balance_error=max_error,
        tolerance=tolerance,
    )


class _Failure(RuntimeError):
    def __init__(self, code: str, diagnostics: list[str], checks: Feasibility | None = None):
        self.code = code
        self.diagnostics = diagnostics
        self.checks = checks
        super().__init__(diagnostics[0])


@dataclass
class _LP:
    solver: Any
    deadline: float
    inventory: dict = field(default_factory=dict)
    flow: dict = field(default_factory=dict)
    served: dict = field(default_factory=dict)
    unmet: dict = field(default_factory=dict)
    locks: list = field(default_factory=list)


def _constraint(solver, terms, lower, upper, label):
    row = solver.RowConstraint(lower, upper, label)
    for variable, coefficient in terms:
        # In particular, a zero-day self-loop occurs twice in a node balance.
        row.SetCoefficient(variable, row.GetCoefficient(variable) + coefficient)
    return row


def _build_model(inputs: ModelInputs, solver, deadline: float) -> _LP:
    model = _LP(solver=solver, deadline=deadline)
    infinity = solver.infinity()
    horizon = inputs.scenario.horizon_days
    nodes = sorted(inputs.network.nodes, key=lambda node: node.id)
    edges = sorted(inputs.network.edges, key=lambda edge: edge.id)
    for node in nodes:
        for day in range(1, horizon + 2):
            lower = node.initial_stock if day == 1 else 0
            upper = node.initial_stock if day == 1 else infinity
            model.inventory[node.id, day] = solver.NumVar(
                lower, upper, f"inventory[{node.id},{day}]"
            )
    for edge in edges:
        for day in range(1, horizon + 1):
            key = edge.id, day
            model.flow[key] = solver.NumVar(0, inputs.edge_capacity[key], f"flow[{edge.id},{day}]")
    for key in sorted(inputs.demand):
        district, group, day = key
        demand = inputs.demand[key]
        label = f"{district},{group},{day}"
        y = model.served[key] = solver.NumVar(0, demand, f"served[{label}]")
        u = model.unmet[key] = solver.NumVar(0, demand, f"unmet[{label}]")
        _constraint(solver, [(y, 1), (u, 1)], demand, demand, f"demand[{label}]")
        if group in inputs.policy.caps:
            _constraint(
                solver, [(y, 1)], 0, demand * inputs.policy.caps[group], f"policy_cap[{label}]"
            )
        if inputs.policy.enforce_minimums and inputs.policy.minimums_verified:
            if group in inputs.policy.minimum_fractions:
                floor = demand * inputs.policy.minimum_fractions[group]
                _constraint(solver, [(y, 1)], floor, infinity, f"policy_minimum[{label}]")

    incoming: dict[tuple[str, int], list] = defaultdict(list)
    outgoing: dict[tuple[str, int], list] = defaultdict(list)
    service: dict[tuple[str, int], list] = defaultdict(list)
    for edge in edges:
        for day in range(1, horizon + 1):
            flow = model.flow[edge.id, day]
            outgoing[edge.source, day].append(flow)
            arrival = inputs.arrival_day[edge.id, day]
            if arrival <= horizon:
                incoming[edge.target, arrival].append(flow)
    for (district, _, day), variable in model.served.items():
        service[district, day].append(variable)
    for node in nodes:
        for day in range(1, horizon + 1):
            key = node.id, day
            terms = [(model.inventory[node.id, day + 1], 1), (model.inventory[key], -1)]
            terms += [(variable, -1) for variable in incoming[key]]
            terms += [(variable, 1) for variable in outgoing[key]]
            terms += [(variable, 1) for variable in service[key]]
            _constraint(
                solver, terms, inputs.supply[key], inputs.supply[key], f"balance[{node.id},{day}]"
            )
            _constraint(
                solver,
                [(variable, 1) for variable in outgoing[key]],
                0,
                inputs.dispatch_capacity[key],
                f"dispatch_capacity[{node.id},{day}]",
            )
    return model


def _status_name(status: int) -> str:
    for name in (
        "OPTIMAL",
        "FEASIBLE",
        "INFEASIBLE",
        "UNBOUNDED",
        "ABNORMAL",
        "MODEL_INVALID",
        "NOT_SOLVED",
    ):
        if status == getattr(pywraplp.Solver, name, None):
            return name
    return f"UNKNOWN_STATUS_{status}"


def _solve_stage(
    model: _LP,
    stages: list[dict],
    name: str,
    terms: list,
    *,
    maximise: bool = False,
    lock: bool = True,
    **metadata,
) -> float:
    """Solve one objective to optimality, then add an exact equality objective lock."""
    stage = {
        "name": name,
        "order": len(stages) + 1,
        "sense": "maximise" if maximise else "minimise",
        "status": "NOT_SOLVED",
        "locked": False,
        **metadata,
    }
    stages.append(stage)
    remaining_ms = int((model.deadline - monotonic()) * 1000)
    if remaining_ms <= 0:
        stage["status"] = "TIMEOUT"
        raise _Failure(
            "TIMEOUT", [f"Shared {SOLVER_TIME_LIMIT_MS} ms plan budget expired before {name}."]
        )
    model.solver.SetTimeLimit(remaining_ms)
    objective = model.solver.Objective()
    objective.Clear()
    for variable, coefficient in terms:
        objective.SetCoefficient(variable, coefficient)
    if maximise:
        objective.SetMaximization()
    else:
        objective.SetMinimization()
    status = model.solver.Solve()
    stage["status"] = _status_name(status)
    if monotonic() >= model.deadline:
        stage["status"] = "TIMEOUT"
        raise _Failure(
            "TIMEOUT", [f"Shared {SOLVER_TIME_LIMIT_MS} ms plan budget expired during {name}."]
        )
    if status != pywraplp.Solver.OPTIMAL:
        code = {
            "INFEASIBLE": "SOLVER_INFEASIBLE",
            "UNBOUNDED": "SOLVER_UNBOUNDED",
            "ABNORMAL": "SOLVER_NUMERICAL_ERROR",
            "MODEL_INVALID": "SOLVER_ERROR",
        }.get(stage["status"], "SOLVER_NONOPTIMAL")
        raise _Failure(
            code, [f"GLOP returned {stage['status']} at {name}; no partial plan is valid."]
        )
    if not model.solver.VerifySolution(TOLERANCE, False):
        stage["status"] = "NUMERICAL_CHECK_FAILED"
        raise _Failure("NUMERICAL_CHECK_FAILED", [f"GLOP solution verification failed at {name}."])
    achieved = fsum(variable.solution_value() * coefficient for variable, coefficient in terms)
    if not isfinite(achieved):
        raise _Failure("NUMERICAL_CHECK_FAILED", [f"Nonfinite objective at {name}."])
    stage["objective_value"] = achieved
    if lock:
        _constraint(model.solver, terms, achieved, achieved, f"objective_lock[{len(stages)}]")
        model.locks.append((name, terms, achieved))
        stage["locked"] = True
        stage["lock"] = "equality; checked to absolute 1e-5 kg tolerance"
    return achieved


def _tier_terms(inputs: ModelInputs, model: _LP, tier: list[str]) -> list:
    return [(model.served[key], 1) for key in sorted(inputs.demand) if key[1] in tier]


def _tier_targets(inputs: ModelInputs, tier: list[str], budget: float) -> list[dict]:
    pairs = sorted({(district, group) for district, group, _ in inputs.demand if group in tier})
    by_pair = {
        (district, group): fsum(
            inputs.demand[district, group, day]
            for day in range(1, inputs.scenario.horizon_days + 1)
        )
        for district, group in pairs
    }
    total = fsum(by_pair.values())
    return [
        {
            "district_id": district,
            "group": group,
            "demand": demand,
            "target": budget * (demand / total) if total > 0 else 0.0,
        }
        for (district, group), demand in by_pair.items()
    ]


def _deviation_terms(
    inputs: ModelInputs, model: _LP, targets: list[dict], tier_number: int
) -> list:
    objective = []
    infinity = model.solver.infinity()
    for target in targets:
        district, group = target["district_id"], target["group"]
        label = f"{tier_number},{district},{group}"
        deviation = model.solver.NumVar(0, infinity, f"absolute_deviation[{label}]")
        aggregate = [
            (model.served[district, group, day], 1)
            for day in range(1, inputs.scenario.horizon_days + 1)
        ]
        _constraint(
            model.solver,
            aggregate + [(deviation, -1)],
            -infinity,
            target["target"],
            f"deviation_positive[{label}]",
        )
        _constraint(
            model.solver,
            aggregate + [(deviation, 1)],
            target["target"],
            infinity,
            f"deviation_negative[{label}]",
        )
        objective.append((deviation, 1))
    return objective


def _candidate_objectives(inputs: ModelInputs, model: _LP, stages: list[dict]) -> None:
    achieved = []
    for tier_number, tier in enumerate(inputs.policy.tiers, 1):
        achieved.append(
            _solve_stage(
                model,
                stages,
                "maximise_tier_service",
                _tier_terms(inputs, model, tier),
                maximise=True,
                tier=tier_number,
                groups=sorted(tier),
                unit="kg_LPG",
                description="Protect this tier's total before considering any lower tier or logistics.",
            )
        )
    for tier_number, (tier, total) in enumerate(zip(inputs.policy.tiers, achieved, strict=True), 1):
        targets = _tier_targets(inputs, tier, total)
        _solve_stage(
            model,
            stages,
            "minimise_tier_proportional_deviation",
            _deviation_terms(inputs, model, targets, tier_number),
            tier=tier_number,
            groups=sorted(tier),
            unit="kg_LPG",
            targets=targets,
            target_basis="achieved tier service, proportional to district/group horizon demand",
        )


def _baseline_objectives(inputs: ModelInputs, model: _LP, stages: list[dict]) -> None:
    pooled = fsum(
        node.initial_stock for node in sorted(inputs.network.nodes, key=lambda node: node.id)
    )
    pooled += fsum(inputs.supply[key] for key in sorted(inputs.supply))
    remaining = pooled
    for tier_number, tier in enumerate(inputs.policy.tiers, 1):
        tier_demand = fsum(inputs.demand[key] for key in sorted(inputs.demand) if key[1] in tier)
        budget = min(remaining, tier_demand)
        remaining = max(0.0, remaining - budget)
        targets = _tier_targets(inputs, tier, budget)
        _solve_stage(
            model,
            stages,
            "minimise_pooled_reference_deviation",
            _deviation_terms(inputs, model, targets, tier_number),
            tier=tier_number,
            groups=sorted(tier),
            unit="kg_LPG",
            targets=targets,
            pooled_available=pooled,
            ideal_tier_budget=budget,
            target_basis="initial stock + fixed Q pooled without topology, timing, floors or caps; tier-ordered proportional demand targets",
        )
    for tier_number, tier in enumerate(inputs.policy.tiers, 1):
        _solve_stage(
            model,
            stages,
            "maximise_remaining_tier_service",
            _tier_terms(inputs, model, tier),
            maximise=True,
            tier=tier_number,
            groups=sorted(tier),
            unit="kg_LPG",
            description="Service tie-break subject to every previously locked proportional deviation.",
        )


def _logistics_objective(inputs: ModelInputs, model: _LP, stages: list[dict]) -> None:
    edges = {edge.id: edge for edge in inputs.network.edges}
    unknown = sorted(edge.id for edge in edges.values() if edge.distance_km is None)
    terms = [
        (model.flow[key], 1 if unknown else edges[key[0]].distance_km) for key in sorted(model.flow)
    ]
    _solve_stage(
        model,
        stages,
        "minimise_flow_quantity" if unknown else "minimise_distance_kg_km",
        terms,
        lock=False,
        unit="kg_LPG route-dispatches" if unknown else "kg_LPG km",
        unknown_distance_routes=unknown,
        description=(
            "Distance is unknown; minimise route-dispatched quantity without inventing distances."
            if unknown
            else "Minimise shipment quantity times route distance after all policy/fairness locks."
        ),
    )


def _export_rows(inputs: ModelInputs, model: _LP, plan_type: str, version: str) -> PlanResult:
    horizon = inputs.scenario.horizon_days
    shipments = []
    arrivals: dict[tuple[str, int], list[float]] = defaultdict(list)
    departures: dict[tuple[str, int], list[float]] = defaultdict(list)
    service_by_day: dict[tuple[str, int], list[float]] = defaultdict(list)
    for edge in sorted(inputs.network.edges, key=lambda edge: edge.id):
        for day in range(1, horizon + 1):
            key = edge.id, day
            quantity = model.flow[key].solution_value()
            arrival = inputs.arrival_day[key]
            shipments.append(
                Shipment(
                    edge_id=edge.id,
                    source=edge.source,
                    target=edge.target,
                    day=day,
                    arrival_day=arrival,
                    quantity=quantity,
                    capacity=inputs.edge_capacity[key],
                    distance_km=edge.distance_km,
                )
            )
            departures[edge.source, day].append(quantity)
            if arrival <= horizon:
                arrivals[edge.target, arrival].append(quantity)
    service = []
    for key in sorted(inputs.demand):
        district, group, day = key
        served = model.served[key].solution_value()
        service.append(
            ServiceRow(
                district_id=district,
                group=group,
                day=day,
                demand=inputs.demand[key],
                served=served,
                unmet=model.unmet[key].solution_value(),
            )
        )
        service_by_day[district, day].append(served)
    balances = []
    for node in sorted(inputs.network.nodes, key=lambda node: node.id):
        for day in range(1, horizon + 1):
            key = node.id, day
            balances.append(
                Balance(
                    node_id=node.id,
                    day=day,
                    opening=model.inventory[key].solution_value(),
                    supply=inputs.supply[key],
                    arrivals=fsum(arrivals[key]),
                    departures=fsum(departures[key]),
                    served=fsum(service_by_day[key]),
                    closing=model.inventory[node.id, day + 1].solution_value(),
                )
            )
    return PlanResult(
        plan_type=plan_type,
        status="OPTIMAL",
        solver_version=version,
        shipments=shipments,
        balances=balances,
        service=service,
    )


def _binding_constraints(inputs: ModelInputs, plan: PlanResult) -> list[str]:
    """Label tight primal bounds, not an IIS or a claim of causal sensitivity."""
    labels = []
    outgoing_nodes = {edge.source for edge in inputs.network.edges}
    for row in plan.shipments:
        if abs(row.quantity - row.capacity) <= TOLERANCE:
            labels.append(f"route_capacity[{row.edge_id},{row.day}]")
    for row in plan.balances:
        if row.node_id in outgoing_nodes:
            if abs(row.departures - inputs.dispatch_capacity[row.node_id, row.day]) <= TOLERANCE:
                labels.append(f"dispatch_capacity[{row.node_id},{row.day}]")
        if abs(row.closing) <= TOLERANCE:
            labels.append(f"inventory_zero[{row.node_id},{row.day + 1}]")
        if row.day == 1 and abs(row.opening) <= TOLERANCE:
            labels.append(f"inventory_zero[{row.node_id},1]")
    for row in plan.service:
        suffix = f"[{row.district_id},{row.group},{row.day}]"
        if abs(row.served - row.demand) <= TOLERANCE:
            labels.append(f"demand_limit{suffix}")
        if row.group in inputs.policy.caps:
            if abs(row.served - inputs.policy.caps[row.group] * row.demand) <= TOLERANCE:
                labels.append(f"policy_cap{suffix}")
        if inputs.policy.enforce_minimums and inputs.policy.minimums_verified:
            if row.group in inputs.policy.minimum_fractions:
                floor = inputs.policy.minimum_fractions[row.group] * row.demand
                if abs(row.served - floor) <= TOLERANCE:
                    labels.append(f"policy_minimum{suffix}")
    return sorted(labels)


def _infeasibility_context(inputs: ModelInputs) -> list[str]:
    """Explain provable necessary-condition conflicts, without inventing an IIS."""
    notes = [
        "GLOP does not expose an IIS through this interface. The following are necessary-condition checks and constraint context, not a minimal conflicting set."
    ]
    policy = inputs.policy
    if not (policy.enforce_minimums and policy.minimums_verified):
        notes.append(
            "No hard service minimums are enabled; inspect solver numerics and objective locks."
        )
        return notes
    required = {
        key: demand * policy.minimum_fractions.get(key[1], 0.0)
        for key, demand in inputs.demand.items()
    }
    positive = [key for key in sorted(required) if required[key] > 0]
    total_minimum = fsum(required.values())
    available = fsum(node.initial_stock for node in inputs.network.nodes) + fsum(
        inputs.supply.values()
    )
    notes.append(
        f"Verified policy {policy.id} requires {total_minimum:.12g} kg across {len(positive)} positive district/group/day minimums; pooled initial stock + Q is {available:.12g} kg."
    )
    if total_minimum > available + TOLERANCE:
        notes.append(
            f"Pooled minimum-service shortfall: {total_minimum - available:.12g} kg even before route/time restrictions."
        )
    for key in positive:
        cap = inputs.demand[key] * policy.caps.get(key[1], 1.0)
        if required[key] > cap + TOLERANCE:
            notes.append(
                f"policy_minimum{key}={required[key]:.12g} exceeds policy_cap{key}={cap:.12g}."
            )

    # This is deliberately an optimistic upper bound: inbound capacity assumes
    # unlimited upstream stock and ignores competing departures. Exceeding it
    # proves a local conflict; satisfying it does not prove feasibility.
    for node in sorted(inputs.network.nodes, key=lambda node: node.id):
        if node.kind != "district":
            continue
        for day in range(1, inputs.scenario.horizon_days + 1):
            minimum = fsum(
                value
                for (district, _, t), value in required.items()
                if district == node.id and t <= day
            )
            gross = node.initial_stock + fsum(inputs.supply[node.id, t] for t in range(1, day + 1))
            gross += fsum(
                min(inputs.edge_capacity[edge.id, t], inputs.dispatch_capacity[edge.source, t])
                for edge in inputs.network.edges
                if edge.target == node.id
                for t in range(1, day + 1)
                if inputs.arrival_day[edge.id, t] <= day
            )
            if minimum > gross + TOLERANCE:
                notes.append(
                    f"District {node.id} through day {day}: cumulative verified minimum {minimum:.12g} kg exceeds optimistic stock/Q/arriving-capacity bound {gross:.12g} kg."
                )
                break
    notes.append(
        "Review time-indexed policy_minimum, route_capacity and dispatch_capacity constraints; unmet demand is not a backlog and a later delivery cannot satisfy an earlier floor."
    )
    return notes


def _run(inputs: ModelInputs, plan_type: Literal["baseline", "candidate"]) -> PlanResult:
    stages: list[dict] = []
    version = "unavailable"
    try:
        _validate_inputs(inputs)
        if pywraplp is None:
            raise _Failure(
                "SOLVER_UNAVAILABLE",
                [
                    "OR-Tools GLOP could not be imported. Install the project's pinned OR-Tools dependency; neither plan has a fallback."
                ],
            )
        solver = pywraplp.Solver.CreateSolver("GLOP")
        if solver is None:
            raise _Failure(
                "SOLVER_UNAVAILABLE",
                ["The installed OR-Tools package could not create a GLOP solver."],
            )
        version = solver.SolverVersion()
        deadline = monotonic() + SOLVER_TIME_LIMIT_MS / 1000
        # GLOP does not implement generic MPSolver.SetNumThreads (returns False).
        # Its supported num_omp_threads parameter is explicitly fixed below.
        settings = (
            "num_omp_threads: 1\nrandom_seed: 0\n"
            "primal_feasibility_tolerance: 1e-9\n"
            "dual_feasibility_tolerance: 1e-9\n"
            "solution_feasibility_tolerance: 1e-8"
        )
        if not solver.SetSolverSpecificParametersAsString(settings):
            raise _Failure(
                "SOLVER_ERROR",
                ["GLOP rejected the deterministic single-thread/tolerance settings."],
            )
        model = _build_model(inputs, solver, deadline)
        if plan_type == "candidate":
            _candidate_objectives(inputs, model, stages)
        else:
            _baseline_objectives(inputs, model, stages)
        _logistics_objective(inputs, model, stages)
        for name, terms, achieved in model.locks:
            actual = fsum(
                variable.solution_value() * coefficient for variable, coefficient in terms
            )
            if not isfinite(actual) or abs(actual - achieved) > TOLERANCE:
                raise _Failure(
                    "NUMERICAL_CHECK_FAILED",
                    [f"Lexicographic lock {name} changed from {achieved:.12g} to {actual:.12g}."],
                )
        plan = _export_rows(inputs, model, plan_type, version)
        plan.checks = check_feasibility(inputs, plan)
        if not plan.checks.passed:
            raise _Failure(
                "NUMERICAL_CHECK_FAILED",
                ["Independent exported-row feasibility check failed.", *plan.checks.violations],
                checks=plan.checks,
            )
        plan.districts = district_risks(inputs, plan.balances, plan.service)
        plan.metrics = compute_metrics(
            inputs, plan.shipments, plan.balances, plan.service, plan.districts
        )
        plan.binding_constraints = _binding_constraints(inputs, plan)
        stages[-1]["route_peak_utilisation"] = route_peak_utilisation(plan.shipments)
        plan.stages = stages
        plan.diagnostics = [
            *inputs.warnings,
            "Single-thread GLOP; fixed sorted variable order; exact sequential objective locks; independent absolute 1e-5 kg feasibility checks.",
            "Unmet demand is lost service, not backlog. Post-horizon arrivals are in transit and cannot serve this horizon.",
            "Fairness is aggregated across the horizon; earliest service is not an objective. Equally optimal daily schedules can differ across solver versions.",
            "Binding labels identify tight primal bounds, not a causal sensitivity analysis or an IIS.",
        ]
        if stages[-1]["unknown_distance_routes"]:
            plan.diagnostics.append(
                "Distance kg-km is not computable because at least one route distance is unknown; final tie-break minimises route-dispatched quantity."
            )
        return plan
    except ModelError as exc:
        failure = _Failure(exc.code, [str(exc)])
    except _Failure as exc:
        failure = exc
        if exc.code == "SOLVER_INFEASIBLE":
            failure.diagnostics.extend(_infeasibility_context(inputs))
    except Exception as exc:
        failure = _Failure("SOLVER_ERROR", [f"{type(exc).__name__}: {exc}"])
    return PlanResult(
        plan_type=plan_type,
        status=failure.code,
        solver_version=version,
        stages=stages,
        diagnostics=failure.diagnostics,
        checks=failure.checks
        or Feasibility(passed=False, violations=failure.diagnostics.copy(), tolerance=TOLERANCE),
    )


def run_baseline(inputs: ModelInputs) -> PlanResult:
    """Find the feasible proportional-reference plan in a separately built LP.

    Objective order: pool all initial stock + fixed Q, give each policy tier its
    unconstrained ideal budget in priority order, and split that budget among
    district/group pairs proportional to their horizon demand. Sequentially
    minimise each tier's aggregate-pair L1 deviations and lock each optimum.
    Then maximise each tier's remaining service, locking each total, and finally
    minimise distance kg-km (only if every route has distance) or flow quantity.

    The targets ignore timing/topology/caps/floors, but the *LP never does*: both
    plans enforce exactly the same balances, capacities and verified policy.
    Reference targets are not guaranteed attainable or maximally efficient.
    L1 optima can tie when proportional targets are unattainable; no daily
    earliest-service or additional max-min fairness objective is implied.
    Failure returns status/diagnostics only, with no allocation or metric rows.
    """
    return _run(inputs, "baseline")


def run_optimizer(inputs: ModelInputs) -> PlanResult:
    """Maximise policy-tier service lexicographically in a fresh GLOP LP.

    First maximise each tier total in configured order and lock it. Next, for
    each tier in order, minimise/lock aggregate district/group horizon L1
    deviations from proportional shares of its *achieved* total. Last minimise
    distance kg-km when every route distance is known, otherwise flow quantity.
    Logistics cannot trade away service or a previously locked fairness result.
    Identical or lower grand totals than the baseline are valid: tier priority
    is the objective, and the engine never manufactures an improvement.
    """
    return _run(inputs, "candidate")
