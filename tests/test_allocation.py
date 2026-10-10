"""Small independent LP fixtures: no dependency on the application data generator."""

from copy import deepcopy
from math import fsum

import pytest

import commonroot.allocation as allocation
from commonroot.allocation import check_feasibility, run_baseline, run_optimizer
from commonroot.contracts import ModelInputs
from commonroot.metrics import (
    compute_metrics,
    days_of_cover,
    district_risks,
    route_peak_utilisation,
)
from commonroot.schemas import (
    Balance,
    Demand,
    Edge,
    NetworkData,
    Node,
    PlanResult,
    Policy,
    Scenario,
    ServiceRow,
    Shipment,
)

PLANNERS = [run_baseline, run_optimizer]


def node(identifier, *, kind="district", stock=0, supply=0, dispatch=100):
    return Node(
        id=identifier,
        name=identifier,
        kind=kind,
        initial_stock=stock,
        daily_supply=supply,
        dispatch_capacity=dispatch,
    )


def edge(identifier, source, target, *, capacity=100, lead=0, distance=1):
    return Edge(
        id=identifier,
        source=source,
        target=target,
        capacity=capacity,
        lead_days=lead,
        distance_km=distance,
    )


def snapshot(nodes, edges, demands, *, horizon=1, policy=None):
    """Explicit fixture schedules independent of production scenario transformation."""
    network = NetworkData(
        nodes=nodes,
        edges=edges,
        demands=[Demand(district_id=d, group=g, daily_demand=q) for d, g, q in demands],
    )
    return ModelInputs(
        network=network,
        scenario=Scenario(event_type="none", horizon_days=horizon, duration_days=1),
        policy=policy or Policy(tiers=[["essential"], ["household"]]),
        supply={(n.id, day): n.daily_supply for n in nodes for day in range(1, horizon + 1)},
        dispatch_capacity={
            (n.id, day): n.dispatch_capacity for n in nodes for day in range(1, horizon + 1)
        },
        edge_capacity={(e.id, day): e.capacity for e in edges for day in range(1, horizon + 1)},
        arrival_day={
            (e.id, day): day + e.lead_days for e in edges for day in range(1, horizon + 1)
        },
        demand={
            (d, g, day): quantity for d, g, quantity in demands for day in range(1, horizon + 1)
        },
    )


def simple(*, stock=10, demand=10, capacity=100, horizon=1, policy=None):
    return snapshot(
        [node("source", kind="import", stock=stock), node("district")],
        [edge("route", "source", "district", capacity=capacity)],
        [("district", "essential", demand)],
        horizon=horizon,
        policy=policy,
    )


def assert_valid(inputs, plan):
    assert plan.status == "OPTIMAL", plan.diagnostics
    assert plan.checks.passed, plan.checks.violations
    assert check_feasibility(inputs, plan).passed
    assert "glop" in plan.solver_version.lower()
    assert plan.metrics is not None
    assert len(plan.balances) == len(inputs.supply)
    assert len(plan.shipments) == len(inputs.edge_capacity)
    assert len(plan.service) == len(inputs.demand)
    # Independent system invariant: multi-hop dispatches are not consumption.
    initial_plus_q = fsum(n.initial_stock for n in inputs.network.nodes) + fsum(
        inputs.supply.values()
    )
    closing = fsum(row.closing for row in plan.balances if row.day == inputs.scenario.horizon_days)
    transit = fsum(
        row.quantity for row in plan.shipments if row.arrival_day > inputs.scenario.horizon_days
    )
    assert initial_plus_q == pytest.approx(
        closing + transit + fsum(row.served for row in plan.service), abs=1e-5
    )
    for row in plan.balances:
        assert row.closing >= -1e-5
        assert (
            row.opening + row.supply + row.arrivals - row.departures - row.served
            == pytest.approx(row.closing, abs=1e-5)
        )
    for row in plan.service:
        assert row.served >= -1e-5
        assert row.unmet >= -1e-5
        assert row.served + row.unmet == pytest.approx(
            inputs.demand[row.district_id, row.group, row.day], abs=1e-5
        )


def assert_failed(plan, status):
    assert plan.status == status, plan.diagnostics
    assert not plan.checks.passed
    assert plan.diagnostics
    assert not plan.shipments
    assert not plan.balances
    assert not plan.service
    assert not plan.districts
    assert plan.metrics is None


@pytest.mark.parametrize("planner", PLANNERS)
def test_multihop_time_balance_and_lost_service(planner):
    inputs = snapshot(
        [
            node("source", kind="import", stock=10, supply=3, dispatch=8),
            node("depot", kind="depot"),
            node("district", stock=1),
        ],
        [
            edge("inbound", "source", "depot", capacity=6, lead=1),
            edge("last_mile", "depot", "district", capacity=4),
        ],
        [("district", "essential", 5)],
        horizon=2,
    )
    plan = planner(inputs)
    assert_valid(inputs, plan)
    # Horizon fairness does not specify an earliest-service tie-break: the
    # district may consume its opening unit on day 1 or carry it to day 2.
    assert plan.service[0].served <= 1 + 1e-5
    assert plan.service[0].unmet >= 4 - 1e-5
    assert [row.arrivals for row in plan.balances if row.node_id == "district"] == pytest.approx(
        [0, 4]
    )
    assert fsum(row.unmet for row in plan.service) == pytest.approx(5)
    assert plan.metrics.total_available == 17
    assert plan.metrics.total_served == pytest.approx(5)
    assert fsum(row.quantity for row in plan.shipments) == pytest.approx(8)
    assert plan.metrics.in_transit == pytest.approx(0)


@pytest.mark.parametrize("planner", PLANNERS)
def test_inventory_carries_between_days_and_q_is_fixed(planner):
    inputs = simple(stock=0, demand=0, horizon=2)
    inputs.supply["source", 1] = 5
    inputs.demand["district", "essential", 2] = 5
    inputs.edge_capacity["route", 2] = 0
    plan = planner(inputs)
    assert_valid(inputs, plan)
    district = [row for row in plan.balances if row.node_id == "district"]
    assert district[0].closing == pytest.approx(5)
    assert district[1].opening == pytest.approx(5)
    assert district[1].served == pytest.approx(5)
    assert district[1].closing == pytest.approx(0)
    assert plan.metrics.total_supply == 5


@pytest.mark.parametrize("planner", PLANNERS)
def test_dispatch_capacity_is_shared_across_outgoing_routes(planner):
    inputs = snapshot(
        [node("source", kind="import", stock=10, dispatch=4), node("a"), node("b")],
        [edge("to_a", "source", "a", capacity=10), edge("to_b", "source", "b", capacity=10)],
        [("a", "essential", 10), ("b", "essential", 10)],
    )
    plan = planner(inputs)
    assert_valid(inputs, plan)
    assert fsum(row.served for row in plan.service) == pytest.approx(4)
    assert fsum(row.quantity for row in plan.shipments) == pytest.approx(4)
    assert "dispatch_capacity[source,1]" in plan.binding_constraints


@pytest.mark.parametrize("planner", PLANNERS)
def test_zero_day_cycles_and_self_loop_cannot_create_stock(planner):
    inputs = snapshot(
        [node("a", kind="depot"), node("b")],
        [edge("ab", "a", "b"), edge("ba", "b", "a"), edge("self", "b", "b")],
        [("b", "essential", 10)],
        horizon=2,
    )
    plan = planner(inputs)
    assert_valid(inputs, plan)
    assert plan.metrics.total_served == pytest.approx(0)
    assert all(row.quantity == pytest.approx(0) for row in plan.shipments)


@pytest.mark.parametrize("planner", PLANNERS)
def test_explicit_time_dependent_arrivals_override_base_lead(planner):
    inputs = simple(stock=0, demand=5, capacity=5, horizon=3)
    for day in range(1, 4):
        inputs.supply["source", day] = 5
    inputs.arrival_day = {("route", 1): 4, ("route", 2): 2, ("route", 3): 4}
    plan = planner(inputs)
    assert_valid(inputs, plan)
    assert plan.service[0].served == pytest.approx(0)
    assert fsum(row.served for row in plan.service) == pytest.approx(5)
    # Material received on day 2 can be held for day 3, but never used on day 1.
    assert [row.arrivals for row in plan.balances if row.node_id == "district"] == pytest.approx(
        [0, 5, 0]
    )
    assert [row.arrival_day for row in plan.shipments] == [4, 2, 4]
    assert plan.metrics.total_unmet == pytest.approx(10)
    assert plan.metrics.in_transit == pytest.approx(0)
    assert plan.districts[0].first_unmet_day == 1


@pytest.mark.parametrize("planner", PLANNERS)
def test_late_abundant_supply_cannot_fulfil_lost_earlier_demand(planner):
    inputs = simple(stock=0, demand=5, horizon=2)
    inputs.supply["source", 2] = 20
    plan = planner(inputs)
    assert_valid(inputs, plan)
    assert [row.served for row in plan.service] == pytest.approx([0, 5])
    assert [row.unmet for row in plan.service] == pytest.approx([5, 0])
    assert plan.metrics.total_available == 20
    assert plan.metrics.total_served == pytest.approx(5)


@pytest.mark.parametrize("planner", PLANNERS)
def test_priority_cannot_be_traded_for_shorter_distance(planner):
    inputs = snapshot(
        [node("source", kind="import", stock=5), node("urgent"), node("nearby")],
        [
            edge("long", "source", "urgent", distance=100_000),
            edge("short", "source", "nearby", distance=1),
        ],
        [("urgent", "essential", 5), ("nearby", "household", 5)],
    )
    plan = planner(inputs)
    assert_valid(inputs, plan)
    assert plan.metrics.group_served == pytest.approx({"essential": 5, "household": 0})
    assert plan.metrics.distance_kg_km == pytest.approx(500_000)
    assert all(stage["locked"] for stage in plan.stages[:-1])


@pytest.mark.parametrize("planner", PLANNERS)
def test_same_tier_proportionality_is_district_group_horizon_demand(planner):
    inputs = snapshot(
        [node("source", kind="import", stock=10), node("a"), node("b")],
        [edge("a_route", "source", "a"), edge("b_route", "source", "b")],
        [("a", "essential", 10), ("b", "household", 20)],
        policy=Policy(tiers=[["essential", "household"]]),
    )
    plan = planner(inputs)
    assert_valid(inputs, plan)
    assert plan.metrics.group_served["essential"] == pytest.approx(10 / 3)
    assert plan.metrics.group_served["household"] == pytest.approx(20 / 3)
    assert plan.metrics.group_fulfilment["essential"] == pytest.approx(1 / 3)
    assert plan.metrics.group_fulfilment["household"] == pytest.approx(1 / 3)


def test_baseline_uses_pooled_targets_not_the_candidate_solution():
    inputs = snapshot(
        [node("source", kind="import", stock=10), node("a"), node("b")],
        [edge("a_route", "source", "a", capacity=1), edge("b_route", "source", "b", capacity=10)],
        [("a", "essential", 10), ("b", "essential", 10)],
        policy=Policy(tiers=[["essential"]]),
    )
    baseline, candidate = run_baseline(inputs), run_optimizer(inputs)
    assert_valid(inputs, baseline)
    assert_valid(inputs, candidate)
    assert [row.served for row in baseline.service] == pytest.approx([1, 5])
    assert [row.served for row in candidate.service] == pytest.approx([1, 9])
    assert baseline.stages[0]["ideal_tier_budget"] == 10
    assert baseline.stages[0]["objective_value"] == pytest.approx(4)
    assert candidate.stages[0]["objective_value"] == pytest.approx(10)
    assert candidate.stages[1]["objective_value"] == pytest.approx(8)


def test_equal_plans_are_reported_without_manufactured_improvement():
    inputs = simple(stock=5, demand=10)
    baseline, candidate = run_baseline(inputs), run_optimizer(inputs)
    assert_valid(inputs, baseline)
    assert_valid(inputs, candidate)
    assert baseline.metrics == candidate.metrics
    assert baseline.service == candidate.service
    assert baseline.shipments == candidate.shipments


@pytest.mark.parametrize("planner", PLANNERS)
def test_hard_lower_tier_floor_and_daily_cap_are_respected(planner):
    inputs = snapshot(
        [node("district", stock=20)],
        [],
        [("district", "essential", 10), ("district", "household", 10)],
        horizon=2,
        policy=Policy(
            tiers=[["essential"], ["household"]],
            minimum_fractions={"household": 0.5},
            caps={"essential": 0.5},
            enforce_minimums=True,
            minimums_verified=True,
        ),
    )
    plan = planner(inputs)
    assert_valid(inputs, plan)
    assert all(row.served == pytest.approx(5) for row in plan.service)
    assert plan.metrics.group_served == pytest.approx({"essential": 10, "household": 10})
    assert "policy_minimum[district,household,1]" in plan.binding_constraints
    assert "policy_cap[district,essential,1]" in plan.binding_constraints


@pytest.mark.parametrize("planner", PLANNERS)
@pytest.mark.parametrize("verified", [False, True])
def test_minimums_are_not_enforced_without_enforcement_flag(planner, verified):
    inputs = simple(
        stock=0,
        policy=Policy(
            tiers=[["essential"]],
            minimum_fractions={"essential": 1},
            minimums_verified=verified,
            enforce_minimums=False,
        ),
    )
    plan = planner(inputs)
    assert_valid(inputs, plan)
    assert plan.metrics.total_served == 0


@pytest.mark.parametrize("planner", PLANNERS)
@pytest.mark.parametrize("conflict", ["supply", "cap", "arrival"])
def test_infeasible_verified_minimum_has_diagnostics_and_no_data(planner, conflict):
    policy = Policy(
        tiers=[["essential"]],
        minimum_fractions={"essential": 1},
        enforce_minimums=True,
        minimums_verified=True,
    )
    inputs = simple(stock=100, policy=policy)
    if conflict == "supply":
        inputs.network.nodes[0].initial_stock = 1
    elif conflict == "cap":
        inputs.policy.caps = {"essential": 0.5}
    else:
        inputs.arrival_day["route", 1] = 2
    plan = planner(inputs)
    assert_failed(plan, "SOLVER_INFEASIBLE")
    assert any("does not expose an IIS" in message for message in plan.diagnostics)
    assert any("minimum" in message for message in plan.diagnostics)


@pytest.mark.parametrize("planner", PLANNERS)
@pytest.mark.parametrize(
    "bad_input, expected",
    [
        ("stock", "DATA_INCOMPLETE"),
        ("schedule", "DATA_INCOMPLETE"),
        ("nan", "INPUT_VALIDATION"),
        ("arrival", "INPUT_VALIDATION"),
        ("group", "INPUT_VALIDATION"),
    ],
)
def test_incomplete_or_invalid_snapshot_is_not_filled_in(planner, bad_input, expected):
    inputs = simple()
    if bad_input == "stock":
        inputs.network.nodes[0].initial_stock = None
    elif bad_input == "schedule":
        del inputs.supply["source", 1]
    elif bad_input == "nan":
        inputs.demand["district", "essential", 1] = float("nan")
    elif bad_input == "arrival":
        inputs.arrival_day["route", 1] = 0
    else:
        inputs.policy = Policy(tiers=[["other"]])
    assert_failed(planner(inputs), expected)


@pytest.mark.parametrize("planner", PLANNERS)
def test_known_distance_is_final_logistics_tiebreak(planner):
    inputs = snapshot(
        [node("source", kind="import", stock=5), node("district")],
        [
            edge("expensive", "source", "district", distance=10),
            edge("cheap", "source", "district", distance=1),
        ],
        [("district", "essential", 5)],
    )
    plan = planner(inputs)
    assert_valid(inputs, plan)
    assert {row.edge_id: row.quantity for row in plan.shipments} == pytest.approx(
        {"cheap": 5, "expensive": 0}
    )
    assert plan.metrics.distance_kg_km == pytest.approx(5)


@pytest.mark.parametrize("planner", PLANNERS)
def test_unknown_distance_remains_null_even_on_idle_route(planner):
    inputs = simple()
    inputs.network.edges[0].distance_km = None
    inputs.edge_capacity["route", 1] = 0
    plan = planner(inputs)
    assert_valid(inputs, plan)
    assert plan.metrics.distance_kg_km is None
    assert plan.stages[-1]["name"] == "minimise_flow_quantity"
    assert plan.stages[-1]["unknown_distance_routes"] == ["route"]
    assert plan.stages[-1]["route_peak_utilisation"] == {"route": None}


@pytest.mark.parametrize("planner", PLANNERS)
@pytest.mark.parametrize(
    "stock, demand, risk, snapshot_cover, minimum, first_low",
    [
        (30, 10, "Watch", 3, 1, 2),
        (50, 10, "Stable", 5, 3, None),
        (0, 10, "High", 0, 0, 1),
        (5, 0, "Not computable", None, None, None),
    ],
)
def test_snapshot_cover_is_separate_from_projected_closing_cover(
    planner, stock, demand, risk, snapshot_cover, minimum, first_low
):
    inputs = snapshot(
        [node("district", stock=stock)], [], [("district", "essential", demand)], horizon=2
    )
    plan = planner(inputs)
    assert_valid(inputs, plan)
    district = plan.districts[0]
    assert district.risk == risk
    assert district.snapshot_cover == snapshot_cover
    assert district.minimum_cover == minimum
    assert district.first_low_day == first_low
    if demand == 0:
        assert district.fulfilled_fraction is None
        assert plan.metrics.fulfilment is None
        assert plan.metrics.group_fulfilment["essential"] is None


def test_unknown_cover_denominators_remain_null():
    assert days_of_cover(10, None) is None
    assert days_of_cover(None, 10) is None
    assert days_of_cover(10, 0) is None
    assert days_of_cover(10, float("nan")) is None
    assert days_of_cover(10, 2) == 5


@pytest.mark.parametrize("planner", PLANNERS)
def test_route_peak_uses_daily_capacity_and_exposure_is_traced(planner):
    inputs = simple(stock=0, demand=2, capacity=4, horizon=2)
    inputs.supply["source", 1] = 2
    inputs.supply["source", 2] = 2
    inputs.edge_capacity["route", 1] = 2
    inputs.affected_edges = ["route"]
    inputs.affected_nodes = ["source"]
    plan = planner(inputs)
    assert_valid(inputs, plan)
    assert route_peak_utilisation(plan.shipments) == pytest.approx({"route": 1})
    assert plan.metrics.peak_route_utilisation == pytest.approx(1)
    assert plan.districts[0].affected
    assert plan.districts[0].affected_routes == ["route"]


def test_post_horizon_cargo_is_conserved_but_cannot_serve():
    inputs = simple(stock=10, demand=5)
    inputs.arrival_day["route", 1] = 3
    plan = PlanResult(
        plan_type="candidate",
        status="OPTIMAL",
        shipments=[
            Shipment(
                edge_id="route",
                source="source",
                target="district",
                day=1,
                arrival_day=3,
                quantity=4,
                capacity=100,
                distance_km=1,
            )
        ],
        balances=[
            Balance(
                node_id="source",
                day=1,
                opening=10,
                supply=0,
                arrivals=0,
                departures=4,
                served=0,
                closing=6,
            ),
            Balance(
                node_id="district",
                day=1,
                opening=0,
                supply=0,
                arrivals=0,
                departures=0,
                served=0,
                closing=0,
            ),
        ],
        service=[
            ServiceRow(
                district_id="district", group="essential", day=1, demand=5, served=0, unmet=5
            )
        ],
    )
    assert check_feasibility(inputs, plan).passed
    metrics = compute_metrics(inputs, plan.shipments, plan.balances, plan.service)
    assert metrics.in_transit == 4
    assert metrics.total_served == 0
    assert metrics.total_unmet == 5
    assert district_risks(inputs, plan.balances, plan.service)[0].inbound == 0
    # A fabricated arrival paired with service would otherwise look balanced.
    plan.balances[1].arrivals = 4
    plan.balances[1].served = 4
    plan.service[0].served = 4
    plan.service[0].unmet = 1
    checks = check_feasibility(inputs, plan)
    assert not checks.passed
    assert any("arrivals" in violation for violation in checks.violations)


@pytest.mark.parametrize(
    "tamper",
    [
        "opening",
        "supply",
        "arrivals",
        "departures",
        "served",
        "closing",
        "demand",
        "unmet",
        "arrival_day",
        "source",
        "capacity",
        "distance",
        "negative",
        "nan",
        "missing",
        "duplicate",
    ],
)
def test_independent_checker_rejects_tampered_exported_rows(tamper):
    inputs = simple(stock=5)
    plan = run_optimizer(inputs)
    assert_valid(inputs, plan)
    if tamper in ("opening", "supply", "arrivals", "departures", "served", "closing"):
        setattr(plan.balances[0], tamper, getattr(plan.balances[0], tamper) + 1)
    elif tamper in ("demand", "unmet"):
        setattr(plan.service[0], tamper, getattr(plan.service[0], tamper) + 1)
    elif tamper == "arrival_day":
        plan.shipments[0].arrival_day += 1
    elif tamper == "source":
        plan.shipments[0].source = "district"
    elif tamper == "capacity":
        plan.shipments[0].capacity += 1
    elif tamper == "distance":
        plan.shipments[0].distance_km = None
    elif tamper == "negative":
        plan.shipments[0].quantity = -1
    elif tamper == "nan":
        plan.service[0].served = float("nan")
    elif tamper == "missing":
        plan.shipments.clear()
    else:
        plan.service.append(plan.service[0].model_copy())
    assert not check_feasibility(inputs, plan).passed


@pytest.mark.parametrize(
    "constraint", ["route_capacity", "dispatch_capacity", "policy_cap", "policy_minimum"]
)
def test_independent_checker_recomputes_hard_limits(constraint):
    inputs = simple(stock=5)
    plan = run_optimizer(inputs)
    assert_valid(inputs, plan)
    if constraint == "route_capacity":
        inputs.edge_capacity["route", 1] = 4
        plan.shipments[0].capacity = 4
    elif constraint == "dispatch_capacity":
        inputs.dispatch_capacity["source", 1] = 4
    elif constraint == "policy_cap":
        inputs.policy.caps = {"essential": 0.4}
    else:
        inputs.policy = Policy(
            tiers=[["essential"]],
            minimum_fractions={"essential": 0.6},
            enforce_minimums=True,
            minimums_verified=True,
        )
    checks = check_feasibility(inputs, plan)
    assert not checks.passed
    assert any(constraint in violation for violation in checks.violations)


@pytest.mark.parametrize("planner", PLANNERS)
def test_reproducible_under_input_reordering_and_does_not_mutate_snapshot(planner):
    inputs = snapshot(
        [node("source", kind="import", stock=11), node("a"), node("b")],
        [edge("a", "source", "a", capacity=3), edge("b", "source", "b", capacity=8)],
        [("a", "essential", 3), ("a", "household", 2), ("b", "essential", 5)],
        horizon=2,
    )
    before = deepcopy(inputs)
    first = planner(inputs)
    assert_valid(inputs, first)
    assert inputs == before
    shuffled = deepcopy(inputs)
    shuffled.network.nodes.reverse()
    shuffled.network.edges.reverse()
    shuffled.network.demands.reverse()
    for name in ("supply", "edge_capacity", "dispatch_capacity", "arrival_day", "demand"):
        setattr(shuffled, name, dict(reversed(list(getattr(shuffled, name).items()))))
    second = planner(shuffled)
    assert_valid(shuffled, second)
    assert first.model_dump() == second.model_dump()


@pytest.mark.parametrize("planner", PLANNERS)
def test_missing_ortools_is_an_explicit_failure_for_both_plans(monkeypatch, planner):
    monkeypatch.setattr(allocation, "pywraplp", None)
    assert_failed(planner(simple()), "SOLVER_UNAVAILABLE")


@pytest.mark.parametrize("planner", PLANNERS)
def test_shared_time_budget_expiry_returns_no_partial_plan(monkeypatch, planner):
    monkeypatch.setattr(allocation, "SOLVER_TIME_LIMIT_MS", 0)
    assert_failed(planner(simple()), "TIMEOUT")


@pytest.mark.parametrize("planner", PLANNERS)
@pytest.mark.parametrize("failure", ["nonoptimal", "numerical"])
def test_rejects_nonoptimal_or_numerically_unverified_solver(monkeypatch, planner, failure):
    create = allocation.pywraplp.Solver.CreateSolver

    class SolverProxy:
        def __init__(self, solver):
            self.solver = solver
            self.calls = 0

        def __getattr__(self, name):
            return getattr(self.solver, name)

        def Solve(self):
            self.calls += 1
            if failure == "nonoptimal" and self.calls == 2:
                return allocation.pywraplp.Solver.FEASIBLE
            return self.solver.Solve()

        def VerifySolution(self, *args):
            return False if failure == "numerical" else self.solver.VerifySolution(*args)

    monkeypatch.setattr(
        allocation.pywraplp.Solver, "CreateSolver", lambda name: SolverProxy(create(name))
    )
    expected = "SOLVER_NONOPTIMAL" if failure == "nonoptimal" else "NUMERICAL_CHECK_FAILED"
    plan = planner(simple())
    assert_failed(plan, expected)
    if failure == "nonoptimal":
        assert plan.stages[0]["status"] == "OPTIMAL"
        assert plan.stages[1]["status"] == "FEASIBLE"


@pytest.mark.parametrize("planner", PLANNERS)
def test_independent_postsolve_failure_removes_all_data_rows(monkeypatch, planner):
    export = allocation._export_rows

    def corrupt_export(*args):
        plan = export(*args)
        plan.balances[0].closing += 1
        return plan

    monkeypatch.setattr(allocation, "_export_rows", corrupt_export)
    result = planner(simple())
    assert_failed(result, "NUMERICAL_CHECK_FAILED")
    assert result.checks.max_balance_error >= 1 - 1e-5
    assert any("inventory_balance" in item for item in result.checks.violations)
