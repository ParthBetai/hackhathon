"""Data-contract, disruption-boundary and independently checked demo-flow tests."""

import json
import math
from pathlib import Path

import networkx as nx
import pytest

from commonroot.contracts import ModelError
from commonroot.data import (
    MAX_FILE_BYTES,
    cylinders_to_kg,
    days_of_cover,
    demo_scenarios,
    generate_network,
    load_network,
    load_policy,
    tonnes_to_kg,
    validate_network,
)
from commonroot.scenario import apply_scenario, build_graph, trace_exposure
from commonroot.schemas import Edge, Scenario

ROOT = Path(__file__).resolve().parents[1]
DISTRICTS = {
    "north_hills", "river_bend", "east_metro", "coastal_plain", "central_gate", "western_fringe",
}


@pytest.fixture
def network():
    return generate_network()


@pytest.fixture
def policy():
    return load_policy()


def write_network(tmp_path, raw):
    path = tmp_path / "network.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def assert_error(code, action, *identifiers):
    with pytest.raises(ModelError) as caught:
        action()
    assert caught.value.code == code
    for identifier in identifiers:
        assert identifier in str(caught.value)


def test_saved_network_is_exact_seed_42_generator_output(network):
    assert load_network(ROOT / "data" / "demo") == network
    assert load_network(ROOT / "data" / "demo" / "network.json") == network
    assert network == generate_network(42)
    assert network.demands != generate_network(99).demands
    assert len(network.nodes) == 14
    assert {node.id for node in network.nodes if node.kind == "district"} == DISTRICTS
    assert len(network.demands) == 18
    assert len({(row.district_id, row.group) for row in network.demands}) == 18
    assert all(type(edge.lead_days) is int for edge in network.edges)
    assert network.unit == "kg_LPG"
    assert sum(row.daily_demand for row in network.demands) == 62450
    assert sum(node.initial_stock for node in network.nodes) == 197220
    assert all(node.initial_stock == 0 for node in network.nodes if node.kind in {"import", "refinery"})
    for node in network.nodes:
        if node.kind == "district":
            daily = sum(row.daily_demand for row in network.demands if row.district_id == node.id)
            assert 1.5 <= days_of_cover(node.initial_stock, daily) <= 2.4


@pytest.mark.parametrize("seed", [-1, 1000000, True, 1.0, "42", None])
def test_generator_rejects_non_integer_or_out_of_range_seed(seed):
    assert_error("INPUT_VALIDATION", lambda: generate_network(seed), "seed")


def test_every_material_demo_row_has_synthetic_provenance(network):
    for row in [*network.nodes, *network.edges, *network.demands]:
        assert row.provenance.kind == "synthetic"
        assert row.provenance.source_url is None
        assert "seed=42" in row.provenance.note
        assert f"generator_version={network.generator_version}" in row.provenance.note
        assert f"data_version={network.data_version}" in row.provenance.note
        assert "+05:30" in row.provenance.as_of
    assert len({(node.x, node.y) for node in network.nodes}) == len(network.nodes)


@pytest.mark.parametrize("key", ["normal", "import_shock", "route_closure", "route_delay", "facility_outage"])
def test_saved_scenarios_match_helpers_and_apply(network, policy, key):
    saved = Scenario.model_validate_json((ROOT / "scenarios" / f"{key}.json").read_text("utf-8"))
    assert saved == demo_scenarios()[key]
    inputs = apply_scenario(network, saved, policy)
    assert len(inputs.supply) == len(network.nodes) * 14
    assert len(inputs.dispatch_capacity) == len(network.nodes) * 14
    assert len(inputs.edge_capacity) == len(network.edges) * 14
    assert len(inputs.arrival_day) == len(network.edges) * 14
    assert len(inputs.demand) == len(network.demands) * 14
    assert all(type(day) is int for day in inputs.arrival_day.values())


@pytest.mark.parametrize(
    "collection,index,field,identifier",
    [
        ("nodes", 0, "initial_stock", "import_source"),
        ("nodes", 3, "daily_supply", "refinery_a"),
        ("nodes", 4, "dispatch_capacity", "bottling_east"),
        ("nodes", 8, "initial_stock", "north_hills"),
        ("edges", 0, "capacity", "route_import_terminal"),
        ("edges", 0, "lead_days", "route_import_terminal"),
        ("demands", 0, "daily_demand", "north_hills"),
    ],
)
@pytest.mark.parametrize("remove", [False, True])
def test_missing_values_identify_field_and_record(tmp_path, network, collection, index, field, identifier, remove):
    raw = network.model_dump()
    if remove:
        del raw[collection][index][field]
    else:
        raw[collection][index][field] = None
    path = write_network(tmp_path, raw)
    assert_error("DATA_INCOMPLETE", lambda: load_network(path), field, identifier)


def test_missing_values_cannot_bypass_checks_with_mutable_models(network, policy):
    network.nodes[8].initial_stock = None
    assert_error(
        "DATA_INCOMPLETE", lambda: apply_scenario(network, Scenario(), policy),
        "initial_stock", "north_hills",
    )


@pytest.mark.parametrize("whole_district", [False, True])
def test_missing_demand_rows_are_not_zero_filled(tmp_path, network, policy, whole_district):
    network.demands[:] = [
        row for row in network.demands
        if not (row.district_id == "north_hills" and (whole_district or row.group == "essential"))
    ]
    path = write_network(tmp_path, network.model_dump())
    assert_error("DATA_INCOMPLETE", lambda: load_network(path), "north_hills")
    assert_error("DATA_INCOMPLETE", lambda: apply_scenario(network, Scenario(), policy), "north_hills")


@pytest.mark.parametrize("field", ["unit", "schema_version", "seed", "generator_version", "data_version", "timezone"])
def test_uploaded_network_metadata_is_not_inferred(tmp_path, network, field):
    raw = network.model_dump()
    del raw[field]
    assert_error("DATA_INCOMPLETE", lambda: load_network(write_network(tmp_path, raw)), field)


def test_untagged_upload_is_not_silently_labelled_synthetic(tmp_path, network):
    raw = network.model_dump()
    del raw["nodes"][0]["provenance"]
    assert_error("DATA_INCOMPLETE", lambda: load_network(write_network(tmp_path, raw)), "provenance", "import_source")


@pytest.mark.parametrize(
    "collection,index,field,value",
    [
        ("nodes", 0, "initial_stock", -1),
        ("nodes", 0, "daily_supply", "100"),
        ("nodes", 0, "dispatch_capacity", True),
        ("nodes", 0, "x", math.inf),
        ("edges", 0, "lead_days", 1.0),
        ("edges", 0, "lead_days", True),
        ("edges", 0, "lead_days", -1),
        ("edges", 0, "lead_days", 31),
        ("edges", 0, "capacity", math.nan),
        ("edges", 0, "target", "not_a_node"),
        ("demands", 0, "daily_demand", -1),
        ("demands", 0, "district_id", "import_source"),
    ],
)
def test_invalid_numbers_and_references_are_rejected(tmp_path, network, collection, index, field, value):
    raw = network.model_dump()
    raw[collection][index][field] = value
    assert_error("INPUT_VALIDATION", lambda: load_network(write_network(tmp_path, raw)))


def test_unknown_distance_remains_unknown(tmp_path, network):
    raw = network.model_dump()
    raw["edges"][0]["distance_km"] = None
    assert load_network(write_network(tmp_path, raw)).edges[0].distance_km is None


def test_duplicate_ids_and_unknown_extra_fields_rejected(tmp_path, network):
    raw = network.model_dump()
    raw["nodes"].append(raw["nodes"][0].copy())
    assert_error("INPUT_VALIDATION", lambda: load_network(write_network(tmp_path, raw)))
    raw = network.model_dump()
    raw["demands"].append(raw["demands"][0].copy())
    assert_error("INPUT_VALIDATION", lambda: load_network(write_network(tmp_path, raw)))
    raw = network.model_dump()
    raw["units"] = "tonnes"
    assert_error("INPUT_VALIDATION", lambda: load_network(write_network(tmp_path, raw)), "units")


def test_duplicate_directed_endpoints_do_not_collapse_to_one_edge(network):
    network.edges.append(network.edges[0].model_copy(update={"id": "duplicate_route"}))
    assert_error("INPUT_VALIDATION", lambda: validate_network(network), "duplicate_route", "endpoints")


def test_zero_lead_cycles_cannot_create_same_day_circulation(network):
    network.edges.append(Edge(
        id="back_route", source="storage_a", target="terminal_a", capacity=100,
        lead_days=0, distance_km=10,
    ))
    assert_error("INPUT_VALIDATION", lambda: validate_network(network), "lead_days", "back_route")
    network.edges[-1].lead_days = 1
    assert validate_network(network).edges[-1].lead_days == 1
    network.edges[-1].lead_days = 0
    network.edges[-1].active = False
    assert not validate_network(network).edges[-1].active


def test_self_route_is_invalid(network):
    network.edges[0].target = network.edges[0].source
    assert_error("INPUT_VALIDATION", lambda: validate_network(network), "route_import_terminal", "itself")


def test_file_size_type_duplicate_keys_and_json_validation(tmp_path):
    path = tmp_path / "network.json"
    path.write_bytes(b" " * (MAX_FILE_BYTES + 1))
    assert_error("INPUT_VALIDATION", lambda: load_network(path), "5 MB")
    for contents in ['{"unit":"kg_LPG","unit":"tonnes"}', "[]", "not JSON", '{"x":NaN}']:
        path.write_text(contents, "utf-8")
        assert_error("INPUT_VALIDATION", lambda: load_network(path))
    assert_error("INPUT_VALIDATION", lambda: load_network(tmp_path / "network.csv"), ".json")
    assert_error("INPUT_VALIDATION", lambda: load_network(tmp_path / "absent.json"), "absent.json")


def test_import_reduction_only_changes_selected_supply_inside_window(network, policy):
    normal = apply_scenario(network, demo_scenarios()["normal"], policy)
    shock = apply_scenario(network, Scenario(), policy)
    for key, quantity in normal.supply.items():
        node, day = key
        factor = 0.5 if node == "import_source" and 1 <= day <= 10 else 1
        assert shock.supply[key] == quantity * factor
    assert shock.supply["refinery_a", 1] == 10000
    assert normal.edge_capacity == shock.edge_capacity
    assert normal.dispatch_capacity == shock.dispatch_capacity
    assert normal.arrival_day == shock.arrival_day
    assert normal.demand == shock.demand
    assert shock.network == network
    assert sum(normal.supply.values()) - sum(shock.supply.values()) == 275000


def test_refinery_shock_leaves_import_source_untouched(network, policy):
    scenario = Scenario(
        affected_id="refinery_a", start_day=3, duration_days=2, reduction_fraction=0.75,
    )
    inputs = apply_scenario(network, scenario, policy)
    assert inputs.supply["refinery_a", 2] == 10000
    assert inputs.supply["refinery_a", 3] == 2500
    assert inputs.supply["refinery_a", 4] == 2500
    assert inputs.supply["refinery_a", 5] == 10000
    assert inputs.supply["import_source", 3] == 55000


def test_closure_is_dispatch_window_only_with_original_graph_trace(network, policy):
    scenario = demo_scenarios()["route_closure"]
    normal = apply_scenario(network, demo_scenarios()["normal"], policy)
    closed = apply_scenario(network, scenario, policy)
    for key, capacity in normal.edge_capacity.items():
        route, day = key
        assert closed.edge_capacity[key] == (
            0 if route == scenario.affected_id and 3 <= day <= 8 else capacity
        )
    assert normal.arrival_day == closed.arrival_day
    assert normal.supply == closed.supply
    assert normal.dispatch_capacity == closed.dispatch_capacity
    assert set(closed.affected_nodes) == {"depot_west", "river_bend", "central_gate", "western_fringe"}
    assert scenario.affected_id in closed.affected_edges
    assert "route_alternate_west" not in closed.affected_edges
    graph = build_graph(network)
    assert isinstance(graph, nx.DiGraph)
    for path in closed.affected_paths:
        assert path["nodes"][0] == "depot_west"
        assert path["nodes"][-1] == path["district_id"]
        assert len(path["edges"]) == len(path["nodes"]) - 1
        assert path["disrupted_edge_id"] == scenario.affected_id
        assert [graph[a][b]["id"] for a, b in zip(path["nodes"], path["nodes"][1:])] == path["edges"]


def test_delay_applies_to_dispatched_shipments_not_arrival_window(network, policy):
    scenario = demo_scenarios()["route_delay"]
    normal = apply_scenario(network, demo_scenarios()["normal"], policy)
    delayed = apply_scenario(network, scenario, policy)
    for key, day_of_arrival in normal.arrival_day.items():
        route, dispatch_day = key
        extra = 3 if route == scenario.affected_id and 2 <= dispatch_day <= 8 else 0
        assert delayed.arrival_day[key] == day_of_arrival + extra
    # Dispatched before the event, although it arrives during the window.
    assert delayed.arrival_day[scenario.affected_id, 1] == 2
    assert delayed.arrival_day[scenario.affected_id, 2] == 6
    assert delayed.edge_capacity == normal.edge_capacity
    assert delayed.supply == normal.supply


def test_late_arrivals_are_not_clipped_into_horizon(network, policy):
    scenario = Scenario(
        event_type="route_delay", affected_id="route_import_terminal", start_day=14,
        duration_days=1, delay_days=3,
    )
    inputs = apply_scenario(network, scenario, policy)
    assert inputs.arrival_day["route_import_terminal", 14] == 18


@pytest.mark.parametrize("reduction", [0.25, 1.0])
def test_facility_outage_changes_only_selected_dispatch(network, policy, reduction):
    raw = demo_scenarios()["facility_outage"].model_dump()
    raw["reduction_fraction"] = reduction
    scenario = Scenario.model_validate(raw)
    normal = apply_scenario(network, demo_scenarios()["normal"], policy)
    outage = apply_scenario(network, scenario, policy)
    for key, capacity in normal.dispatch_capacity.items():
        node, day = key
        factor = 1 - reduction if node == "bottling_east" and 4 <= day <= 8 else 1
        assert outage.dispatch_capacity[key] == capacity * factor
    assert normal.edge_capacity == outage.edge_capacity
    assert normal.supply == outage.supply
    assert normal.arrival_day == outage.arrival_day
    assert normal.demand == outage.demand


def test_global_demand_and_lead_assumptions_are_explicit(network, policy):
    normal = apply_scenario(network, demo_scenarios()["normal"], policy)
    scenario = Scenario(event_type="none", demand_multiplier=1.25, extra_lead_days=2)
    adjusted = apply_scenario(network, scenario, policy)
    for key, quantity in normal.demand.items():
        assert adjusted.demand[key] == quantity * 1.25
    for edge in network.edges:
        for day in range(1, 15):
            assert adjusted.arrival_day[edge.id, day] == normal.arrival_day[edge.id, day] + (2 if edge.active else 0)
    assert any("Global assumption: demand_multiplier=1.25" in text for text in adjusted.warnings)
    assert any("Global assumption: extra_lead_days=2" in text for text in adjusted.warnings)
    assert adjusted.affected_nodes == []
    assert adjusted.affected_edges == []


def test_inactive_nodes_have_no_supply_dispatch_or_incident_flows(network, policy):
    inactive = {"refinery_a", "bottling_west"}
    for node in network.nodes:
        if node.id in inactive:
            node.active = False
    inputs = apply_scenario(network, Scenario(), policy)
    for node in inactive:
        assert all(inputs.supply[node, day] == inputs.dispatch_capacity[node, day] == 0 for day in range(1, 15))
        assert node not in inputs.affected_nodes
    for edge in network.edges:
        if edge.source in inactive or edge.target in inactive or not edge.active:
            assert all(inputs.edge_capacity[edge.id, day] == 0 for day in range(1, 15))
            assert edge.id not in inputs.affected_edges


def test_exposure_is_downstream_and_excludes_unrelated_inactive_links(network):
    nodes, edges, paths = trace_exposure(network, Scenario())
    assert "import_source" in nodes
    assert "refinery_a" not in nodes
    assert "route_domestic_west" not in edges
    assert "route_domestic_east" not in edges
    assert "route_reserve_storage_depot" not in edges
    assert {path["district_id"] for path in paths} == DISTRICTS
    for edge in network.edges:
        if edge.id == "route_east_metro":
            edge.active = False
    nodes, edges, paths = trace_exposure(network, Scenario())
    assert "east_metro" not in nodes
    assert "route_east_metro" not in edges
    assert "east_metro" not in {path["district_id"] for path in paths}


@pytest.mark.parametrize(
    "event,affected",
    [
        ("supply_reduction", "missing"),
        ("supply_reduction", "bottling_east"),
        ("supply_reduction", "route_import_terminal"),
        ("route_closure", "bottling_east"),
        ("route_delay", "missing"),
        ("facility_outage", "north_hills"),
        ("facility_outage", "import_source"),
    ],
)
def test_event_target_ids_and_kinds_are_validated(network, policy, event, affected):
    scenario = Scenario(event_type=event, affected_id=affected)
    assert_error("INPUT_VALIDATION", lambda: apply_scenario(network, scenario, policy), "affected_id", affected)


def test_selected_already_closed_edge_is_still_the_trace_trigger(network, policy):
    scenario = Scenario(event_type="route_closure", affected_id="route_reserve_storage_depot")
    inputs = apply_scenario(network, scenario, policy)
    assert scenario.affected_id in inputs.affected_edges
    assert set(inputs.affected_nodes) == {"depot_east", "north_hills", "east_metro", "coastal_plain"}
    assert all(path["nodes"][0] == "depot_east" for path in inputs.affected_paths)
    assert all(inputs.edge_capacity[scenario.affected_id, day] == 0 for day in range(1, 15))
    assert any("already inactive" in warning for warning in inputs.warnings)


def test_selected_disabled_source_cannot_be_reactivated_by_a_scenario(network, policy):
    network.nodes[0].active = False
    inputs = apply_scenario(network, Scenario(), policy)
    assert all(inputs.supply["import_source", day] == 0 for day in range(1, 15))
    assert all(inputs.dispatch_capacity["import_source", day] == 0 for day in range(1, 15))
    assert all(inputs.edge_capacity["route_import_terminal", day] == 0 for day in range(1, 15))
    assert inputs.affected_nodes == ["import_source"]
    assert inputs.affected_paths == []


def test_snapshot_is_independent_of_mutating_caller_objects(network, policy):
    scenario = Scenario()
    first = apply_scenario(network, scenario, policy)
    second = apply_scenario(network, scenario, policy)
    assert first == second
    network.nodes[0].daily_supply = 123
    scenario.reduction_fraction = 0.75
    policy.tiers[0].append("another_group")
    assert first.network.nodes[0].daily_supply == 55000
    assert first.scenario.reduction_fraction == 0.5
    assert first.policy.tiers[0] == ["essential"]
    assert first.supply["import_source", 1] == 27500


def test_policy_groups_match_demand_and_hard_rules_require_verification(tmp_path, network, policy):
    policy.tiers[-1] = ["unknown_group"]
    assert_error("INPUT_VALIDATION", lambda: apply_scenario(network, Scenario(), policy), "policy.tiers", "business", "unknown_group")
    raw = load_policy().model_dump()
    raw["minimum_fractions"] = {"essential": 1.0}
    raw["enforce_minimums"] = True
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(raw), "utf-8")
    assert_error("INPUT_VALIDATION", lambda: load_policy(path), "verification")
    raw["enforce_minimums"] = False
    del raw["tiers"]
    path.write_text(json.dumps(raw), "utf-8")
    assert_error("DATA_INCOMPLETE", lambda: load_policy(path), "tiers")


def test_infeasible_policy_remains_explicit_for_solver(network):
    policy = load_policy(ROOT / "data" / "demo" / "policy_infeasible.json")
    inputs = apply_scenario(network, Scenario(), policy)
    assert inputs.policy.enforce_minimums and inputs.policy.minimums_verified
    assert inputs.policy.illustrative
    assert all(floor == 1 for floor in inputs.policy.minimum_fractions.values())
    assert sum(inputs.demand.values()) > sum(inputs.supply.values()) + sum(node.initial_stock for node in network.nodes)


def test_conversions_and_noncomputable_cover():
    assert tonnes_to_kg(1.25) == 1250
    assert cylinders_to_kg(10, 14.2) == 142
    assert cylinders_to_kg(2.5, 19) == 47.5
    assert tonnes_to_kg(0) == cylinders_to_kg(0, 14.2) == 0
    assert days_of_cover(100, 25) == 4
    assert days_of_cover(0, 25) == 0
    assert days_of_cover(None, 25) is None
    assert days_of_cover(100, None) is None
    assert days_of_cover(100, 0) is None
    assert days_of_cover(None, None) is None


@pytest.mark.parametrize("value", [-1, math.inf, math.nan, True, "4", None])
def test_conversion_input_validation(value):
    assert_error("INPUT_VALIDATION", lambda: tonnes_to_kg(value))
    assert_error("INPUT_VALIDATION", lambda: cylinders_to_kg(value, 14.2))
    assert_error("INPUT_VALIDATION", lambda: cylinders_to_kg(1, value))
    if value is not None:
        assert_error("INPUT_VALIDATION", lambda: days_of_cover(value, 1))
        assert_error("INPUT_VALIDATION", lambda: days_of_cover(1, value))
    assert_error("INPUT_VALIDATION", lambda: cylinders_to_kg(1, 0), "fill_mass")


def max_deliverable_demand(inputs):
    """Independent time-expanded max-flow oracle for fixture quality (no policy objective).

    Every kg enters once as opening stock or daily supply. Storage carries it
    forward, one dispatch gate shares each facility limit across routes, and a
    district/day sink caps served demand. Out-of-horizon deliveries have no
    connection to a demand sink. This checks the fixture's physical potential,
    independently of the application's baseline/optimisation implementations.
    """
    graph = nx.DiGraph()
    source, sink = "external_supply", "served_demand"
    horizon = inputs.scenario.horizon_days
    total_available = sum(node.initial_stock for node in inputs.network.nodes) + sum(inputs.supply.values())
    for node in inputs.network.nodes:
        for day in range(1, horizon + 1):
            stock = (node.id, day, "stock")
            dispatch = (node.id, day, "dispatch")
            opening = node.initial_stock if day == 1 else 0
            graph.add_edge(source, stock, capacity=opening + inputs.supply[node.id, day])
            graph.add_edge(stock, dispatch, capacity=inputs.dispatch_capacity[node.id, day])
            if day < horizon:
                graph.add_edge(stock, (node.id, day + 1, "stock"), capacity=total_available)
            if node.kind == "district":
                requested = sum(
                    quantity for (district, _, demand_day), quantity in inputs.demand.items()
                    if district == node.id and demand_day == day
                )
                graph.add_edge(stock, sink, capacity=requested)
    for edge in inputs.network.edges:
        for day in range(1, horizon + 1):
            arrival = inputs.arrival_day[edge.id, day]
            if arrival <= horizon:
                graph.add_edge(
                    (edge.source, day, "dispatch"), (edge.target, arrival, "stock"),
                    capacity=inputs.edge_capacity[edge.id, day],
                )
    return nx.maximum_flow_value(graph, source, sink)


def test_default_shock_has_real_unmet_and_materially_less_without_shock(network, policy):
    normal = apply_scenario(network, demo_scenarios()["normal"], policy)
    shock = apply_scenario(network, Scenario(), policy)
    total_demand = sum(shock.demand.values())
    initial = sum(node.initial_stock for node in network.nodes)
    # Even before accounting for transport lag, there is insufficient physical
    # mass in the default shock. No allocation algorithm can erase this deficit.
    mass_deficit = total_demand - initial - sum(shock.supply.values())
    assert mass_deficit == 42080
    normal_unmet = total_demand - max_deliverable_demand(normal)
    shock_unmet = total_demand - max_deliverable_demand(shock)
    assert shock_unmet >= mass_deficit
    assert normal_unmet < shock_unmet * 0.5
    assert shock_unmet - normal_unmet > total_demand * 0.05
