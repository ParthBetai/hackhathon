"""Immutable scenario snapshot shared by both allocation strategies."""

from dataclasses import dataclass, field

from commonroot.schemas import NetworkData, Policy, Scenario


class ModelError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass
class ModelInputs:
    network: NetworkData
    scenario: Scenario
    policy: Policy
    supply: dict[tuple[str, int], float]
    edge_capacity: dict[tuple[str, int], float]
    dispatch_capacity: dict[tuple[str, int], float]
    arrival_day: dict[tuple[str, int], int]
    demand: dict[tuple[str, str, int], float]
    affected_nodes: list[str] = field(default_factory=list)
    affected_edges: list[str] = field(default_factory=list)
    affected_paths: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
