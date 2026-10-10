"""Deterministic scenario schedules and originally active dependency tracing.

An affected path describes a possible dependency, never an actual cargo
assignment. It is traced on the original graph even when this scenario closes
a route, with a disrupted route's TARGET as the downstream trace root.
"""

import networkx as nx
from pydantic import ValidationError

from commonroot.contracts import ModelError, ModelInputs
from commonroot.data import days_of_cover, demo_scenarios, validate_network
from commonroot.schemas import NetworkData, Policy, Scenario

__all__ = ["apply_scenario", "build_graph", "days_of_cover", "demo_scenarios", "trace_exposure"]

SOURCE_KINDS = {"import", "refinery"}
FACILITY_KINDS = {"terminal", "refinery", "storage", "bottling", "depot"}


def _active_graph(network: NetworkData) -> nx.DiGraph:
    graph = nx.DiGraph()
    for node in sorted(network.nodes, key=lambda item: item.id):
        if node.active:
            graph.add_node(node.id, kind=node.kind, name=node.name)
    for edge in sorted(network.edges, key=lambda item: item.id):
        if edge.active and edge.source in graph and edge.target in graph:
            graph.add_edge(
                edge.source, edge.target, id=edge.id, capacity=edge.capacity,
                lead_days=edge.lead_days, distance_km=edge.distance_km,
            )
    return graph


def build_graph(network: NetworkData) -> nx.DiGraph:
    """Directed, originally active routes with active endpoints; edge IDs are attributes."""
    return _active_graph(validate_network(network))


def _validate_scenario(network: NetworkData, scenario: Scenario) -> Scenario:
    try:
        scenario = Scenario.model_validate(scenario.model_dump(mode="python"), strict=True)
    except ValidationError as exc:
        raise ModelError("INPUT_VALIDATION", f"scenario: {exc}") from exc
    if scenario.event_type == "none":
        return scenario  # No disruption asset is needed for the reference case.
    nodes = {node.id: node for node in network.nodes}
    edges = {edge.id: edge for edge in network.edges}
    if scenario.event_type in {"route_closure", "route_delay"}:
        edge = edges.get(scenario.affected_id)
        if edge is None:
            raise ModelError(
                "INPUT_VALIDATION", f"affected_id {scenario.affected_id!r}: expected a known route ID."
            )
    else:
        node = nodes.get(scenario.affected_id)
        if node is None:
            raise ModelError(
                "INPUT_VALIDATION", f"affected_id {scenario.affected_id!r}: expected a known node ID."
            )
        allowed = SOURCE_KINDS if scenario.event_type == "supply_reduction" else FACILITY_KINDS
        if node.kind not in allowed:
            raise ModelError(
                "INPUT_VALIDATION",
                f"affected_id {node.id}: {scenario.event_type} requires node kind {sorted(allowed)}, "
                f"not {node.kind}.",
            )
    return scenario


def _validate_policy(network: NetworkData, policy: Policy) -> Policy:
    try:
        policy = Policy.model_validate(policy.model_dump(mode="python"), strict=True)
    except ValidationError as exc:
        raise ModelError("INPUT_VALIDATION", f"policy: {exc}") from exc
    demand_groups = {row.group for row in network.demands}
    policy_groups = {group for tier in policy.tiers for group in tier}
    if policy_groups != demand_groups:
        raise ModelError(
            "INPUT_VALIDATION",
            f"policy.tiers must match demand groups exactly; missing={sorted(demand_groups - policy_groups)}, "
            f"unknown={sorted(policy_groups - demand_groups)}.",
        )
    return policy


def _trace(
    network: NetworkData, scenario: Scenario, graph: nx.DiGraph,
) -> tuple[list[str], list[str], list[dict]]:
    if scenario.event_type == "none":
        return [], [], []
    disrupted_edge = None
    root = scenario.affected_id
    if scenario.event_type in {"route_closure", "route_delay"}:
        disrupted_edge = next(edge for edge in network.edges if edge.id == scenario.affected_id)
        root = disrupted_edge.target
    if root not in graph:
        # A disabled selected node remains the explicit trigger, but has no
        # usable dependencies. Never reactivate it merely to trace an event.
        return [root], [disrupted_edge.id] if disrupted_edge is not None else [], []
    reachable = {root} | nx.descendants(graph, root)
    affected_edges = {
        attrs["id"] for source, target, attrs in graph.edges(data=True)
        if source in reachable and target in reachable
    }
    if disrupted_edge is not None:
        affected_edges.add(disrupted_edge.id)
    # A deterministic shortest directed witness per district avoids exponential
    # path enumeration. The full affected edge set above includes alternates.
    witnesses = nx.single_source_shortest_path(graph, root)
    paths = []
    for node in sorted(network.nodes, key=lambda item: item.id):
        if node.kind != "district" or node.id not in reachable:
            continue
        path = witnesses[node.id]
        edges = [graph[source][target]["id"] for source, target in zip(path, path[1:])]
        trigger = (
            f"Route {disrupted_edge.id} targets {root}. " if disrupted_edge is not None
            else f"Selected node {root}. "
        )
        paths.append({
            "root_id": root,
            "district_id": node.id,
            "nodes": path,
            "edges": edges,
            "disrupted_edge_id": disrupted_edge.id if disrupted_edge is not None else None,
            "explanation": (
                f"{trigger}Originally active directed path reaches {node.id}; "
                "this is a modelled dependency, not an actual shipment or confirmed shortage."
            ),
        })
    return sorted(reachable), sorted(affected_edges), paths


def trace_exposure(
    network: NetworkData, scenario: Scenario,
) -> tuple[list[str], list[str], list[dict]]:
    """Return affected node IDs, edge IDs, and district paths with `nodes`/`edges` ID arrays.

    For an edge event the selected edge is in the affected edge set and in each
    path's disrupted_edge_id. The path arrays start at its target and contain
    only the downstream node/edge sequence, so the arrays remain contiguous.
    """
    network = validate_network(network)
    scenario = _validate_scenario(network, scenario)
    return _trace(network, scenario, _active_graph(network))


def apply_scenario(network: NetworkData, scenario: Scenario, policy: Policy) -> ModelInputs:
    """Build an independent, fully explicit 1..H snapshot for both allocation plans.

    A route delay affects shipments DISPATCHED within the event window. Global
    extra_lead_days is added to every active route for the whole horizon.
    Capacity changes never rescale inventory, demand, or any unselected supply.
    Arrival days after H are retained rather than clipped into the horizon.
    """
    network = validate_network(network)
    scenario = _validate_scenario(network, scenario)
    policy = _validate_policy(network, policy)
    graph = _active_graph(network)
    active_nodes = set(graph.nodes)
    active_edges = {attrs["id"] for _, _, attrs in graph.edges(data=True)}
    affected_nodes, affected_edges, affected_paths = _trace(network, scenario, graph)
    days = range(1, scenario.horizon_days + 1)
    end_day = scenario.start_day + scenario.duration_days - 1
    supply = {}
    dispatch_capacity = {}
    edge_capacity = {}
    arrival_day = {}
    demand = {}
    for node in network.nodes:
        for day in days:
            in_window = scenario.start_day <= day <= end_day
            quantity = float(node.daily_supply) if node.active else 0.0
            capacity = float(node.dispatch_capacity) if node.active else 0.0
            if node.id == scenario.affected_id and in_window:
                if scenario.event_type == "supply_reduction":
                    quantity *= 1 - scenario.reduction_fraction
                elif scenario.event_type == "facility_outage":
                    capacity *= 1 - scenario.reduction_fraction
            supply[node.id, day] = quantity
            dispatch_capacity[node.id, day] = capacity
    for edge in network.edges:
        active = edge.id in active_edges
        for day in days:
            in_window = scenario.start_day <= day <= end_day
            capacity = float(edge.capacity) if active else 0.0
            arrival = day + edge.lead_days + (scenario.extra_lead_days if active else 0)
            if edge.id == scenario.affected_id and in_window:
                if scenario.event_type == "route_closure":
                    capacity = 0.0
                elif scenario.event_type == "route_delay":
                    arrival += scenario.delay_days
            edge_capacity[edge.id, day] = capacity
            arrival_day[edge.id, day] = arrival
    for row in network.demands:
        for day in days:
            demand[row.district_id, row.group, day] = row.daily_demand * scenario.demand_multiplier
    warnings = list(network.assumptions)
    warnings.extend([
        f"Global assumption: demand_multiplier={scenario.demand_multiplier:g} applies to all district/group demand on every day.",
        f"Global assumption: extra_lead_days={scenario.extra_lead_days} applies to every originally active route for the entire horizon.",
        "Exposure follows originally active downstream dependencies, including the selected disrupted route as a trigger; it does not prove actual shipments or shortages.",
    ])
    if policy.illustrative:
        warnings.append(f"Policy {policy.id} v{policy.version} is illustrative, not official authority.")
    if scenario.seed != network.seed:
        warnings.append(
            f"Scenario seed {scenario.seed} differs from loaded network seed {network.seed}; "
            "the loaded input is used unchanged, without regeneration."
        )
    if len(active_nodes) < len(network.nodes):
        warnings.append(
            "Inactive nodes have zero external supply, zero dispatch and zero incident route capacity; "
            "declared stocks and demand remain explicit."
        )
    if scenario.event_type in {"route_closure", "route_delay"} and scenario.affected_id not in active_edges:
        warnings.append(
            f"Selected route {scenario.affected_id} is already inactive or has an inactive endpoint; "
            "its capacity stays zero. Exposure is traced from its target through usable downstream routes."
        )
    return ModelInputs(
        network=network, scenario=scenario, policy=policy, supply=supply,
        edge_capacity=edge_capacity, dispatch_capacity=dispatch_capacity,
        arrival_day=arrival_day, demand=demand, affected_nodes=affected_nodes,
        affected_edges=affected_edges, affected_paths=affected_paths, warnings=warnings,
    )
