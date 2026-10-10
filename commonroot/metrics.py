"""Metrics from checked, exported stock/flow rows; never from a solver objective.

Cover uses scenario-adjusted average daily demand over the entire horizon. Opening
snapshot cover and the minimum *closing* cover are deliberately different fields.
Distances are unknown if any route lacks a distance, even when that route is idle.
"""

from collections import defaultdict
from math import fsum, isfinite

from commonroot.contracts import ModelInputs
from commonroot.schemas import Balance, DistrictRisk, Metrics, ServiceRow, Shipment

TOLERANCE = 1e-5


def days_of_cover(stock: float | None, daily_demand: float | None) -> float | None:
    """Return days, or null for an unknown/zero denominator or unknown stock."""
    if stock is None or daily_demand is None:
        return None
    if not isfinite(stock) or not isfinite(daily_demand) or daily_demand <= 0:
        return None
    return stock / daily_demand


def route_peak_utilisation(shipments: list[Shipment]) -> dict[str, float | None]:
    """Peak daily dispatched/capacity per route; an always-closed route is null.

    A zero-capacity day has no utilisation denominator. Such days are excluded,
    rather than presented as either infinite utilisation or operating capacity.
    """
    peaks: dict[str, float | None] = {}
    for row in sorted(shipments, key=lambda row: (row.edge_id, row.day)):
        peaks.setdefault(row.edge_id, None)
        if row.capacity > 0:
            value = row.quantity / row.capacity
            current = peaks[row.edge_id]
            peaks[row.edge_id] = value if current is None else max(current, value)
    return peaks


def district_risks(
    inputs: ModelInputs,
    balances: list[Balance],
    service: list[ServiceRow],
    *,
    tolerance: float = TOLERANCE,
) -> list[DistrictRisk]:
    """Build district risk rows, keeping snapshot and projected cover separate.

    Unmet demand above numerical tolerance is High. Otherwise a projected closing
    cover below the configured threshold is Watch, a computable cover is Stable,
    and an unknown/zero demand denominator is Not computable. Inbound counts only
    arrivals inside the horizon, not upstream shipments or local production.
    """
    horizon = inputs.scenario.horizon_days
    node_by_id = {node.id: node for node in inputs.network.nodes}
    by_node: dict[str, list[Balance]] = defaultdict(list)
    by_district: dict[str, list[ServiceRow]] = defaultdict(list)
    for row in balances:
        by_node[row.node_id].append(row)
    for row in service:
        by_district[row.district_id].append(row)

    # The original active topology expresses exposure; a scenario's temporary
    # closure does not erase the route's downstream dependency.
    incoming: dict[str, list] = defaultdict(list)
    for edge in inputs.network.edges:
        if edge.active and node_by_id[edge.source].active and node_by_id[edge.target].active:
            incoming[edge.target].append(edge)
    affected_nodes = set(inputs.affected_nodes)
    affected_edges = set(inputs.affected_edges)
    risks = []
    for node in sorted(inputs.network.nodes, key=lambda node: node.id):
        if node.kind != "district":
            continue
        rows = sorted(by_node[node.id], key=lambda row: row.day)
        services = sorted(by_district[node.id], key=lambda row: (row.day, row.group))
        if len(rows) != horizon:
            raise ValueError(f"District {node.id} does not have a complete checked balance series.")
        demand = fsum(row.demand for row in services)
        served = fsum(row.served for row in services)
        unmet = fsum(row.unmet for row in services)
        daily_demand = demand / horizon
        projected = [(row.day, days_of_cover(row.closing, daily_demand)) for row in rows]
        computable = [value for _, value in projected if value is not None]
        minimum_cover = min(computable) if computable else None
        first_low = next(
            (
                day
                for day, value in projected
                if value is not None and value < inputs.scenario.cover_threshold
            ),
            None,
        )
        unmet_by_day: dict[int, list[float]] = defaultdict(list)
        for row in services:
            unmet_by_day[row.day].append(row.unmet)
        first_unmet = next(
            (day for day in sorted(unmet_by_day) if fsum(unmet_by_day[day]) > tolerance),
            None,
        )
        if unmet > tolerance:
            risk = "High"
        elif minimum_cover is None:
            risk = "Not computable"
        elif first_low is not None:
            risk = "Watch"
        else:
            risk = "Stable"

        upstream = {node.id}
        pending = [node.id]
        routes = set()
        while pending:
            current = pending.pop()
            for edge in incoming[current]:
                if edge.id in affected_edges:
                    routes.add(edge.id)
                if edge.source not in upstream:
                    upstream.add(edge.source)
                    pending.append(edge.source)
        risks.append(
            DistrictRisk(
                district_id=node.id,
                name=node.name,
                opening_stock=rows[0].opening,
                daily_demand=daily_demand,
                inbound=fsum(row.arrivals for row in rows),
                closing_stock=rows[-1].closing,
                snapshot_cover=days_of_cover(rows[0].opening, daily_demand),
                minimum_cover=minimum_cover,
                first_low_day=first_low,
                first_unmet_day=first_unmet,
                unmet=unmet,
                fulfilled_fraction=served / demand if demand > 0 else None,
                risk=risk,
                affected=bool(upstream & affected_nodes or routes),
                affected_routes=sorted(routes),
            )
        )
    return risks


def compute_metrics(
    inputs: ModelInputs,
    shipments: list[Shipment],
    balances: list[Balance],
    service: list[ServiceRow],
    districts: list[DistrictRisk] | None = None,
) -> Metrics:
    """Aggregate a checked plan without interpreting unknown distance as zero.

    Shipment quantity is not net consumption: multi-hop cargo appears on each
    route. System conservation is initial + Q = served + final stock + in-transit.
    Per-route peaks are available through :func:`route_peak_utilisation` and are
    also included in the allocation plan's final logistics-stage metadata.
    """
    if districts is None:
        districts = district_risks(inputs, balances, service)
    groups = sorted({group for tier in inputs.policy.tiers for group in tier})
    group_demand = {
        group: fsum(row.demand for row in service if row.group == group) for group in groups
    }
    group_served = {
        group: fsum(row.served for row in service if row.group == group) for group in groups
    }
    group_unmet = {
        group: fsum(row.unmet for row in service if row.group == group) for group in groups
    }
    total_demand = fsum(row.demand for row in service)
    total_served = fsum(row.served for row in service)
    total_supply = fsum(row.supply for row in balances)
    initial_stock = fsum(row.opening for row in balances if row.day == 1)
    covers = [row.minimum_cover for row in districts if row.minimum_cover is not None]
    known_distances = all(edge.distance_km is not None for edge in inputs.network.edges)
    peaks = route_peak_utilisation(shipments)
    return Metrics(
        total_supply=total_supply,
        initial_stock=initial_stock,
        total_available=initial_stock + total_supply,
        total_demand=total_demand,
        total_served=total_served,
        total_unmet=fsum(row.unmet for row in service),
        fulfilment=total_served / total_demand if total_demand > 0 else None,
        group_fulfilment={
            group: group_served[group] / group_demand[group] if group_demand[group] > 0 else None
            for group in groups
        },
        group_served=group_served,
        group_unmet=group_unmet,
        elevated_districts=sum(row.risk in ("High", "Watch") for row in districts),
        lowest_cover=min(covers) if covers else None,
        distance_kg_km=(
            fsum(row.quantity * row.distance_km for row in shipments) if known_distances else None
        ),
        in_transit=fsum(
            row.quantity for row in shipments if row.arrival_day > inputs.scenario.horizon_days
        ),
        peak_route_utilisation=max(
            (value for value in peaks.values() if value is not None), default=0
        ),
    )
