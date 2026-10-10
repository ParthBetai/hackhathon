"""Versioned, strict domain contracts. All model quantities are kg_LPG."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Quantity = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Fraction = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,80}$")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Provenance(Contract):
    kind: Literal["synthetic", "public", "user-provided", "derived"] = "synthetic"
    source_url: str | None = None
    as_of: str = "2026-10-10T00:00:00+05:30"
    note: str = "Synthetic engineering fixture, not real infrastructure or official data."


class Node(Contract):
    id: Identifier
    name: str
    kind: Literal["import", "terminal", "refinery", "storage", "bottling", "depot", "district"]
    initial_stock: Quantity | None
    daily_supply: Quantity | None
    dispatch_capacity: Quantity | None
    active: bool = True
    x: float = 0
    y: float = 0
    provenance: Provenance = Field(default_factory=Provenance)


class Edge(Contract):
    id: Identifier
    source: Identifier
    target: Identifier
    capacity: Quantity | None
    lead_days: Annotated[int, Field(strict=True, ge=0, le=30)] | None
    distance_km: Quantity | None
    active: bool = True
    provenance: Provenance = Field(default_factory=Provenance)


class Demand(Contract):
    district_id: Identifier
    group: Identifier
    daily_demand: Quantity | None
    provenance: Provenance = Field(default_factory=Provenance)


class Policy(Contract):
    id: Identifier = "illustrative_priority_v1"
    name: str = "Essential services, then households"
    version: str = "1.0"
    tiers: list[list[str]] = Field(default_factory=lambda: [["essential"], ["household"], ["business"]])
    minimum_fractions: dict[str, Fraction] = Field(default_factory=dict)
    caps: dict[str, Fraction] = Field(default_factory=dict)
    enforce_minimums: bool = False
    minimums_verified: bool = False
    illustrative: bool = True
    description: str = "Scenario assumption, not an official priority order."

    @model_validator(mode="after")
    def validate_policy(self):
        groups = [group for tier in self.tiers for group in tier]
        if not groups or any(not tier for tier in self.tiers) or len(set(groups)) != len(groups):
            raise ValueError("Policy tiers must contain each eligible group exactly once.")
        if set(self.minimum_fractions) - set(groups) or set(self.caps) - set(groups):
            raise ValueError("Policy floors and caps must reference groups in tiers.")
        if self.enforce_minimums and not self.minimums_verified:
            raise ValueError("Hard minimums require an explicit verification flag; never infer authority.")
        return self


class Shipment(Contract):
    edge_id: str
    source: str
    target: str
    day: int
    arrival_day: int
    quantity: float
    capacity: float
    distance_km: float | None


class Balance(Contract):
    node_id: str
    day: int
    opening: float
    supply: float
    arrivals: float
    departures: float
    served: float
    closing: float


class ServiceRow(Contract):
    district_id: str
    group: str
    day: int
    demand: float
    served: float
    unmet: float


class DistrictRisk(Contract):
    district_id: str
    name: str
    opening_stock: float
    daily_demand: float
    inbound: float
    closing_stock: float
    snapshot_cover: float | None
    minimum_cover: float | None
    first_low_day: int | None
    first_unmet_day: int | None
    unmet: float
    fulfilled_fraction: float | None
    risk: Literal["High", "Watch", "Stable", "Not computable"]
    affected: bool
    affected_routes: list[str] = Field(default_factory=list)


class Feasibility(Contract):
    passed: bool = False
    violations: list[str] = Field(default_factory=list)
    max_balance_error: float = 0
    tolerance: float = 1e-5


class Metrics(Contract):
    total_supply: float = 0
    initial_stock: float = 0
    total_available: float = 0
    total_demand: float = 0
    total_served: float = 0
    total_unmet: float = 0
    fulfilment: float | None = None
    group_fulfilment: dict[str, float | None] = Field(default_factory=dict)
    group_served: dict[str, float] = Field(default_factory=dict)
    group_unmet: dict[str, float] = Field(default_factory=dict)
    elevated_districts: int = 0
    lowest_cover: float | None = None
    distance_kg_km: float | None = None
    in_transit: float = 0
    peak_route_utilisation: float = 0


class PlanResult(Contract):
    plan_type: Literal["baseline", "candidate"]
    status: str
    solver: str = "OR-Tools GLOP"
    solver_version: str = "unavailable"
    shipments: list[Shipment] = Field(default_factory=list)
    balances: list[Balance] = Field(default_factory=list)
    service: list[ServiceRow] = Field(default_factory=list)
    districts: list[DistrictRisk] = Field(default_factory=list)
    metrics: Metrics | None = None
    checks: Feasibility = Field(default_factory=Feasibility)
    stages: list[dict] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    binding_constraints: list[str] = Field(default_factory=list)


class NetworkData(Contract):
    schema_version: Literal["1.1"] = "1.1"
    data_version: str = "synthetic_corridor_v1"
    generator_version: str = "1.0"
    seed: int = 42
    unit: Literal["kg_LPG"] = "kg_LPG"
    timezone: Literal["Asia/Kolkata"] = "Asia/Kolkata"
    nodes: list[Node]
    edges: list[Edge]
    demands: list[Demand]
    assumptions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_references(self):
        ids = [node.id for node in self.nodes]
        edge_ids = [edge.id for edge in self.edges]
        if not ids or len(ids) != len(set(ids)) or len(edge_ids) != len(set(edge_ids)):
            raise ValueError("Node and edge IDs must be non-empty and unique.")
        if any(edge.source not in ids or edge.target not in ids for edge in self.edges):
            raise ValueError("Every route endpoint must reference a known node.")
        district_ids = {node.id for node in self.nodes if node.kind == "district"}
        keys = [(row.district_id, row.group) for row in self.demands]
        if len(keys) != len(set(keys)) or any(row.district_id not in district_ids for row in self.demands):
            raise ValueError("Demand must use unique district/group keys and known district nodes.")
        if district_ids != {row.district_id for row in self.demands}:
            raise ValueError("Every district needs explicit demand rows, even when demand is zero.")
        return self


class Scenario(Contract):
    name: str = Field(default="Import corridor — 50% reduction", min_length=1, max_length=120)
    event_type: Literal["none", "supply_reduction", "route_closure", "route_delay", "facility_outage"] = "supply_reduction"
    affected_id: str = "import_source"
    start_day: Annotated[int, Field(strict=True, ge=1, le=14)] = 1
    duration_days: Annotated[int, Field(strict=True, ge=1, le=14)] = 10
    horizon_days: Annotated[int, Field(strict=True, ge=1, le=14)] = 14
    reduction_fraction: Fraction = 0.5
    delay_days: Annotated[int, Field(strict=True, ge=0, le=14)] = 2
    demand_multiplier: Annotated[float, Field(ge=0, le=3, allow_inf_nan=False)] = 1.0
    extra_lead_days: Annotated[int, Field(strict=True, ge=0, le=7)] = 0
    cover_threshold: Annotated[float, Field(gt=0, le=14, allow_inf_nan=False)] = 2.0
    seed: Annotated[int, Field(strict=True, ge=0, le=999999)] = 42
    notes: str = Field(default="Synthetic stress test; not a reconstruction of a historical event.", max_length=2000)

    @model_validator(mode="after")
    def validate_window(self):
        if self.event_type != "none" and self.start_day + self.duration_days - 1 > self.horizon_days:
            raise ValueError("Impact window must fit inside the planning horizon.")
        if not self.name.strip():
            raise ValueError("Scenario name cannot be blank.")
        return self
