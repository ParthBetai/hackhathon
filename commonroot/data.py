"""Strict local fixtures and reproducible, entirely fictional LPG engineering data.

Masses are kg_LPG; daily supply, demand and capacities are kg_LPG/day.
Synthetic row provenance inherits the network seed/version and repeats them in
its note so an exported row remains understandable on its own.
"""

import json
import math
import random
from pathlib import Path
from typing import Any

import networkx as nx
from pydantic import ValidationError

from commonroot.contracts import ModelError
from commonroot.schemas import Demand, Edge, NetworkData, Node, Policy, Provenance, Scenario

MAX_FILE_BYTES = 5_000_000
GENERATOR_VERSION = "1.0"
DATA_VERSION = "synthetic_corridor_v1"
CONVERSION_VERSION = "mass_conversion_v1"
GROUPS = ("essential", "household", "business")
DEMO_DIR = Path(__file__).resolve().parent.parent / "data" / "demo"


def _missing(field: str, record_id: str) -> None:
    raise ModelError("DATA_INCOMPLETE", f"{field} is required for {record_id}; unknown is not zero.")


def _schema_error(exc: ValidationError, raw: dict[str, Any], label: str) -> ModelError:
    messages = []
    incomplete = False
    for error in exc.errors(include_url=False, include_input=False):
        loc = error["loc"]
        record_id = label
        if len(loc) > 1 and isinstance(loc[1], int):
            rows = raw.get(loc[0], [])
            if isinstance(rows, list) and loc[1] < len(rows) and isinstance(rows[loc[1]], dict):
                row = rows[loc[1]]
                record_id = str(row.get("id", row.get("district_id", record_id)))
                if loc[0] == "demands":
                    record_id += f"/{row.get('group', '?')}"
        incomplete |= error["type"] == "missing"
        field = ".".join(map(str, loc)) or label
        messages.append(f"{record_id}: {field}: {error['msg']}")
    return ModelError("DATA_INCOMPLETE" if incomplete else "INPUT_VALIDATION", "; ".join(messages))


def _read_json(path: str | Path, filename: str) -> dict[str, Any]:
    """Read one bounded JSON object, rejecting duplicate keys and non-JSON numbers."""
    if not isinstance(path, (str, Path)):
        raise ModelError("INPUT_VALIDATION", "fixture path must be a string or pathlib.Path.")
    source = Path(path)
    if source.is_dir():
        source = source / filename
    if source.suffix.lower() != ".json":
        raise ModelError("INPUT_VALIDATION", f"{source}: fixture must be a .json file.")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number {value}")

    try:
        if source.stat().st_size > MAX_FILE_BYTES:
            raise ModelError("INPUT_VALIDATION", f"{source}: exceeds the 5 MB fixture limit.")
        with source.open("rb") as stream:
            payload = stream.read(MAX_FILE_BYTES + 1)
        if len(payload) > MAX_FILE_BYTES:
            raise ModelError("INPUT_VALIDATION", f"{source}: exceeds the 5 MB fixture limit.")
        raw = json.loads(
            payload.decode("utf-8-sig"),
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except ModelError:
        raise
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise ModelError("INPUT_VALIDATION", f"{source}: cannot read valid JSON ({exc}).") from exc
    if not isinstance(raw, dict):
        raise ModelError("INPUT_VALIDATION", f"{source}: fixture root must be a JSON object.")
    return raw


def _require_network_metadata(raw: dict[str, Any]) -> None:
    # Contract defaults are useful for Python construction, but must not silently
    # label an untagged uploaded dataset as synthetic or assume its mass unit.
    for field in ("schema_version", "data_version", "generator_version", "seed", "unit", "timezone"):
        if raw.get(field) is None:
            _missing(field, "network")
    for collection in ("nodes", "edges", "demands"):
        if raw.get(collection) is None:
            _missing(collection, "network")
        if not isinstance(raw[collection], list):
            continue  # Pydantic reports the exact invalid collection type.
        for row in raw[collection]:
            if not isinstance(row, dict):
                continue
            record_id = str(row.get("id", row.get("district_id", collection)))
            provenance = row.get("provenance")
            if not isinstance(provenance, dict):
                _missing("provenance", record_id)
            for field in ("kind", "source_url", "as_of", "note"):
                if field not in provenance or (field != "source_url" and provenance[field] is None):
                    _missing(f"provenance.{field}", record_id)
            if "active" not in row and collection != "demands":
                _missing("active", record_id)
            if collection == "nodes":
                for field in ("x", "y"):
                    if row.get(field) is None:
                        _missing(field, record_id)


def _require_demand_rows(raw: dict[str, Any]) -> None:
    nodes, demands = raw.get("nodes"), raw.get("demands")
    if not isinstance(nodes, list) or not isinstance(demands, list):
        return
    district_ids = {
        node["id"] for node in nodes
        if isinstance(node, dict) and node.get("kind") == "district"
        and isinstance(node.get("id"), str)
    }
    # Let the schema report invalid references/types before diagnosing rows
    # missing as a consequence of that invalid key.
    if any(
        not isinstance(row, dict)
        or not isinstance(row.get("district_id"), str)
        or row["district_id"] not in district_ids
        or not isinstance(row.get("group"), str)
        for row in demands
    ):
        return
    keys = {
        (row.get("district_id"), row.get("group"))
        for row in demands
        if isinstance(row, dict)
        and isinstance(row.get("district_id"), str)
        and isinstance(row.get("group"), str)
    }
    groups = {group for _, group in keys}
    for node in nodes:
        if isinstance(node, dict) and node.get("kind") == "district":
            district = node.get("id")
            if not any(key[0] == district for key in keys):
                _missing("demands", str(district))
            for group in sorted(groups):
                if (district, group) not in keys:
                    _missing("daily_demand", f"{district}/{group}")


def validate_network(network: NetworkData) -> NetworkData:
    """Return a checked copy; mutable nested models/lists cannot bypass validation.

    Unknown distance is permitted and remains None. Stock, supply, dispatch,
    route capacity, lead time, and district/group demand are always explicit.
    Opposite-direction routes are valid, but duplicate directed endpoints and
    originally active zero-lead cycles are rejected.
    """
    raw = network.model_dump(mode="python")
    _require_demand_rows(raw)
    try:
        checked = NetworkData.model_validate(raw, strict=True)
    except ValidationError as exc:
        raise _schema_error(exc, raw, "network") from exc
    if isinstance(checked.seed, bool) or not 0 <= checked.seed <= 999999:
        raise ModelError("INPUT_VALIDATION", "network.seed must be an integer from 0 to 999999.")
    for field in ("data_version", "generator_version"):
        if not getattr(checked, field).strip():
            _missing(field, "network")
    active_nodes = {node.id for node in checked.nodes if node.active}
    for node in checked.nodes:
        for field in ("initial_stock", "daily_supply", "dispatch_capacity"):
            if getattr(node, field) is None:
                _missing(field, node.id)
        if not math.isfinite(node.x) or not math.isfinite(node.y):
            raise ModelError("INPUT_VALIDATION", f"{node.id}: x and y must be finite coordinates.")
    endpoints = set()
    zero_lead = nx.DiGraph()
    zero_lead.add_nodes_from(active_nodes)
    for edge in checked.edges:
        for field in ("capacity", "lead_days"):
            if getattr(edge, field) is None:
                _missing(field, edge.id)
        pair = (edge.source, edge.target)
        if pair in endpoints:
            raise ModelError(
                "INPUT_VALIDATION", f"{edge.id}: duplicate route endpoints {edge.source}->{edge.target}."
            )
        if edge.source == edge.target:
            raise ModelError("INPUT_VALIDATION", f"{edge.id}: a route cannot connect a node to itself.")
        endpoints.add(pair)
        if edge.active and edge.source in active_nodes and edge.target in active_nodes:
            if edge.lead_days == 0:
                zero_lead.add_edge(edge.source, edge.target, id=edge.id)
    if not nx.is_directed_acyclic_graph(zero_lead):
        cycle = nx.find_cycle(zero_lead)
        edge_ids = [zero_lead[source][target]["id"] for source, target in cycle]
        raise ModelError("INPUT_VALIDATION", f"lead_days: zero-lead cycle in routes {edge_ids}.")
    groups = {row.group for row in checked.demands}
    keys = {(row.district_id, row.group) for row in checked.demands}
    for row in checked.demands:
        if row.daily_demand is None:
            _missing("daily_demand", f"{row.district_id}/{row.group}")
    for node in checked.nodes:
        if node.kind == "district":
            for group in sorted(groups):
                if (node.id, group) not in keys:
                    _missing("daily_demand", f"{node.id}/{group}")
    return checked


def load_network(path: str | Path) -> NetworkData:
    """Load a JSON NetworkData fixture or a folder containing network.json."""
    raw = _read_json(path, "network.json")
    _require_network_metadata(raw)
    _require_demand_rows(raw)
    try:
        network = NetworkData.model_validate(raw, strict=True)
    except ValidationError as exc:
        raise _schema_error(exc, raw, "network") from exc
    return validate_network(network)


def load_policy(path: str | Path | None = None) -> Policy:
    """Load an explicit policy JSON, or the bundled illustrative policy by default."""
    raw = _read_json(DEMO_DIR / "policy.json" if path is None else path, "policy.json")
    for field in Policy.model_fields:
        if field not in raw or raw[field] is None:
            _missing(field, "policy")
    try:
        return Policy.model_validate(raw, strict=True)
    except ValidationError as exc:
        raise _schema_error(exc, raw, "policy") from exc


def _nonnegative(value: float, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ModelError("INPUT_VALIDATION", f"{field} must be a finite non-negative number.")
    try:
        valid = math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    if not valid:
        raise ModelError("INPUT_VALIDATION", f"{field} must be a finite non-negative number.")
    return float(value)


def tonnes_to_kg(tonnes: float) -> float:
    """mass_conversion_v1: one metric tonne is exactly 1,000 kg_LPG."""
    return _nonnegative(_nonnegative(tonnes, "tonnes") * 1000, "kg_LPG")


def cylinders_to_kg(count: float, fill_mass: float) -> float:
    """mass_conversion_v1: count/equivalents times explicitly declared kg per cylinder."""
    count = _nonnegative(count, "count")
    fill_mass = _nonnegative(fill_mass, "fill_mass")
    if fill_mass == 0:
        raise ModelError("INPUT_VALIDATION", "fill_mass must be positive kg_LPG per cylinder.")
    return _nonnegative(count * fill_mass, "kg_LPG")


def days_of_cover(stock: float | None, demand: float | None) -> float | None:
    """Snapshot stock / daily demand; an unknown input or zero demand is not computable."""
    if stock is not None:
        stock = _nonnegative(stock, "stock")
    if demand is not None:
        demand = _nonnegative(demand, "demand")
    if stock is None or demand is None or demand == 0:
        return None
    result = stock / demand
    return result if math.isfinite(result) else None


def generate_network(seed: int = 42) -> NetworkData:
    """Generate a repeatable fictional import corridor plus a domestic refinery branch.

    Only district demand varies by seed (+/-4%, rounded to 50 kg increments).
    District stocks are 1.5--2.4 days of that demand. Named upstream buffers
    carry explicit modest stocks; both sources start empty. No pre-horizon
    shipments or real infrastructure, geography, prices or policy are inferred.
    """
    if type(seed) is not int or not 0 <= seed <= 999999:
        raise ModelError("INPUT_VALIDATION", "seed must be an integer from 0 to 999999.")
    rng = random.Random(seed)
    note = (
        f"Synthetic engineering fixture; seed={seed}; generator_version={GENERATOR_VERSION}; "
        f"data_version={DATA_VERSION}. All numerical fields in this record are fictional."
    )

    def provenance() -> Provenance:
        return Provenance(
            kind="synthetic", source_url=None, as_of="2026-10-10T00:00:00+05:30", note=note
        )

    # id, name, kind, opening stock, external daily supply, dispatch limit, SVG x, SVG y
    node_rows = [
        ("import_source", "Import source", "import", 0, 55000, 60000, 60, 130),
        ("terminal_a", "Terminal A", "terminal", 14000, 0, 60000, 215, 130),
        ("storage_a", "Storage A", "storage", 16000, 0, 65000, 375, 130),
        ("refinery_a", "Domestic refinery A", "refinery", 0, 10000, 11000, 375, 355),
        ("bottling_east", "East bottling plant", "bottling", 12000, 0, 37500, 535, 115),
        ("bottling_west", "West bottling plant", "bottling", 10000, 0, 32500, 535, 340),
        ("depot_east", "East depot", "depot", 10000, 0, 37500, 705, 115),
        ("depot_west", "West depot", "depot", 8000, 0, 33000, 705, 340),
    ]
    nodes = [
        Node(
            id=identifier, name=name, kind=kind, initial_stock=stock, daily_supply=supply,
            dispatch_capacity=dispatch, active=True, x=x, y=y, provenance=provenance(),
        )
        for identifier, name, kind, stock, supply, dispatch, x, y in node_rows
    ]
    # Fictional demand mix: 12% essential, 63% household, 25% business.
    district_rows = [
        ("north_hills", "North Hills", 9000, 2.4, 920, 35),
        ("river_bend", "River Bend", 11000, 2.0, 920, 285),
        ("east_metro", "East Metro", 13000, 1.5, 920, 115),
        ("coastal_plain", "Coastal Plain", 10000, 2.2, 920, 195),
        ("central_gate", "Central Gate", 12000, 2.0, 920, 365),
        ("western_fringe", "Western Fringe", 8500, 2.4, 920, 445),
    ]
    demands = []
    for identifier, name, nominal_demand, stock_days, x, y in district_rows:
        daily = int(round(nominal_demand * (100 + rng.randint(-4, 4)) / 5000) * 50)
        essential = int(round(daily * 0.12))
        household = int(round(daily * 0.63))
        nodes.append(Node(
            id=identifier, name=name, kind="district", initial_stock=round(daily * stock_days),
            daily_supply=0, dispatch_capacity=0, active=True, x=x, y=y, provenance=provenance(),
        ))
        for group, quantity in zip(GROUPS, (essential, household, daily - essential - household)):
            demands.append(Demand(
                district_id=identifier, group=group, daily_demand=quantity, provenance=provenance(),
            ))
    # Only explicitly active directed links can carry LPG. The east-to-west link
    # is a constrained alternate, not unlimited rerouting around an outage.
    edge_rows = [
        ("route_import_terminal", "import_source", "terminal_a", 60000, 1, 300, True),
        ("route_terminal_storage", "terminal_a", "storage_a", 60000, 0, 18, True),
        ("route_storage_east", "storage_a", "bottling_east", 37000, 0, 90, True),
        ("route_storage_west", "storage_a", "bottling_west", 28000, 0, 125, True),
        ("route_domestic_west", "refinery_a", "bottling_west", 11000, 0, 120, True),
        ("route_domestic_east", "refinery_a", "bottling_east", 3000, 1, 210, True),
        ("route_bottling_east_depot", "bottling_east", "depot_east", 36000, 1, 45, True),
        ("route_bottling_west_depot", "bottling_west", "depot_west", 32500, 1, 55, True),
        ("route_alternate_west", "bottling_east", "depot_west", 5500, 1, 180, True),
        ("route_north_hills", "depot_east", "north_hills", 11000, 1, 95, True),
        ("route_east_metro", "depot_east", "east_metro", 15500, 0, 20, True),
        ("route_coastal_plain", "depot_east", "coastal_plain", 12500, 1, 85, True),
        ("route_river_bend", "depot_west", "river_bend", 13000, 0, 40, True),
        ("route_central_gate", "depot_west", "central_gate", 14500, 0, 25, True),
        ("route_western_fringe", "depot_west", "western_fringe", 10500, 1, 110, True),
        ("route_reserve_storage_depot", "storage_a", "depot_east", 5000, 1, 70, False),
    ]
    edges = [
        Edge(
            id=identifier, source=source, target=target, capacity=capacity, lead_days=lead,
            distance_km=distance, active=active, provenance=provenance(),
        )
        for identifier, source, target, capacity, lead, distance, active in edge_rows
    ]
    return validate_network(NetworkData(
        schema_version="1.1", data_version=DATA_VERSION, generator_version=GENERATOR_VERSION,
        seed=seed, unit="kg_LPG", timezone="Asia/Kolkata", nodes=nodes, edges=edges, demands=demands,
        assumptions=[
            "All infrastructure, district names, coordinates and numerical inputs are fictional synthetic data; source URLs are null.",
            f"Generator {GENERATOR_VERSION}; data {DATA_VERSION}; seed {seed}. Row provenance applies to every numerical field in that row.",
            "Mass uses kg_LPG; supply, demand and capacities use kg_LPG/day. Daily periods are 1..H in Asia/Kolkata.",
            "Daily demand is constant over the horizon: approximately 12% essential, 63% household and the remainder business, rounded to whole kg; these groups and shares are illustrative.",
            "Source stocks begin at zero. District carry-in stocks are 1.5--2.4 days of demand; upstream buffers are explicit. There are no pre-horizon shipments.",
            "Dispatch on day t arrives on t + lead_days. Zero-lead links permit same-day transfer only through an acyclic network; late arrivals remain in transit.",
            "The domestic refinery branch is independent exogenous supply. An import shock does not reduce domestic production.",
            "The alternate east-to-west depot route is capped at 5500 kg_LPG/day. The reserve storage-to-depot route is explicitly inactive.",
            "Node dispatch is the total outbound mass per day; route capacity is a separate bound. There are no inferred storage ceilings, losses, costs or emissions factors.",
            "SVG coordinates are diagram layout only, not geolocation. Route distances are synthetic logistics proxies, not verified transport distances.",
        ],
    ))


def demo_scenarios() -> dict[str, Scenario]:
    """Fresh scenario objects; fixture keys are stable and match scenarios/*.json."""
    note = (
        "Synthetic engineering stress test; seed=42; generator_version=1.0; "
        "data_version=synthetic_corridor_v1; scenario_version=1.1; source_url=null. "
        "All impact parameters are illustrative assumptions, not a historical reconstruction."
    )
    common = dict(
        horizon_days=14, seed=42, demand_multiplier=1.0, extra_lead_days=0,
        cover_threshold=2.0, notes=note,
    )
    return {
        "normal": Scenario(
            name="Normal supply — synthetic reference", event_type="none", affected_id="",
            start_day=1, duration_days=10, reduction_fraction=0.0, delay_days=0, **common,
        ),
        "import_shock": Scenario(
            name="Import corridor — 50% reduction", event_type="supply_reduction",
            affected_id="import_source", start_day=1, duration_days=10,
            reduction_fraction=0.5, delay_days=2, **common,
        ),
        "route_closure": Scenario(
            name="Western bottling route — six-day closure", event_type="route_closure",
            affected_id="route_bottling_west_depot", start_day=3, duration_days=6,
            reduction_fraction=1.0, delay_days=0, **common,
        ),
        "route_delay": Scenario(
            name="Import route — three-day dispatch-window delay", event_type="route_delay",
            affected_id="route_import_terminal", start_day=2, duration_days=7,
            reduction_fraction=0.0, delay_days=3, **common,
        ),
        "facility_outage": Scenario(
            name="East bottling — five-day dispatch outage", event_type="facility_outage",
            affected_id="bottling_east", start_day=4, duration_days=5,
            reduction_fraction=1.0, delay_days=0, **common,
        ),
    }
