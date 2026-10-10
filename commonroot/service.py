"""Single service entry point shared by CLI and Streamlit. Never executes a plan."""

import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from importlib.metadata import version
from uuid import uuid4

from pydantic import Field

from commonroot import __version__
from commonroot.allocation import run_baseline, run_optimizer
from commonroot.contracts import ModelError, ModelInputs
from commonroot.data import generate_network, load_policy
from commonroot.scenario import apply_scenario
from commonroot.schemas import Contract, NetworkData, PlanResult, Policy, Scenario


class Review(Contract):
    status: str = "not_reviewed"
    reviewed_at: str | None = None
    note: str = ""
    operational_action: str = "none"


class RunBundle(Contract):
    manifest: dict
    scenario: Scenario
    network: NetworkData
    policy: Policy
    adjusted_inputs: dict
    baseline: PlanResult
    candidate: PlanResult
    comparison: dict
    affected_nodes: list[str]
    affected_edges: list[str]
    affected_paths: list[dict]
    warnings: list[str]
    evidence: list[dict] = Field(default_factory=list)
    review: Review = Field(default_factory=Review)


def canonical_json(value: dict | list) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_hash(value: dict | list) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def snapshot(inputs: ModelInputs) -> dict:
    """JSON-friendly exact adjusted schedules, not lossy repr of tuple-key dictionaries."""
    tables = {}
    for field in ("supply", "edge_capacity", "dispatch_capacity", "arrival_day", "demand"):
        tables[field] = [{"key": list(key), "value": value} for key, value in sorted(getattr(inputs, field).items())]
    return tables


def compare_plans(baseline: PlanResult, candidate: PlanResult) -> dict:
    if any(plan.status != "OPTIMAL" or not plan.checks.passed for plan in (baseline, candidate)):
        return {"available": False, "explanation": "A failed or infeasible plan cannot be compared as a valid recommendation."}
    before, after = baseline.metrics, candidate.metrics
    difference = before.total_unmet - after.total_unmet
    if abs(difference) <= 1e-5:
        difference = 0.0
    percent = difference / before.total_unmet * 100 if before.total_unmet > 1e-5 else None
    explanation = (
        "Both plans leave the same total unmet demand within 0.00001 kg. Inspect district/group distribution and logistics; no total-demand improvement is claimed."
        if difference == 0 else
        f"Candidate leaves {abs(difference):,.2f} kg {'less' if difference > 0 else 'more'} unmet demand than the baseline. Priorities and group outcomes must be reviewed separately."
    )
    return {
        "available": True,
        "unmet_reduction_kg": difference,
        "unmet_reduction_percent": percent,
        "explanation": explanation,
        "baseline_method": "Pooled supply/stock proportional targets by priority tier; minimise absolute deviations, then maximise remaining tier service, then logistics.",
        "candidate_method": "Maximise and lock each tier's service; minimise within-tier proportional deviations at achieved totals; minimise logistics last.",
        "objective_scope": "Fairness is district/group aggregate over the horizon. Earlier daily service is not an additional objective.",
        "distance_unit": "kg_LPG km",
        "cost": None,
        "emissions": None,
        "proxy_warning": "Distance is synthetic shipment-mass × route-distance, not vehicle kilometres. No cost or emissions factors supplied.",
    }


def run_simulation(
    scenario: Scenario,
    network: NetworkData | None = None,
    policy: Policy | None = None,
    evidence: list[dict] | None = None,
) -> RunBundle:
    """Run both strategies against one validated snapshot, with no remote LLM calls."""
    from commonroot.evidence import validate_saved_evidence

    start = time.perf_counter()
    checked_evidence = validate_saved_evidence(evidence or [])
    inputs = apply_scenario(network or generate_network(scenario.seed), scenario, policy or load_policy())
    adjusted = snapshot(inputs)
    identity = {
        "network": inputs.network.model_dump(mode="json"),
        "scenario": inputs.scenario.model_dump(mode="json"),
        "policy": inputs.policy.model_dump(mode="json"),
        "adjusted": adjusted,
    }
    baseline, candidate = run_baseline(inputs), run_optimizer(inputs)
    status = "success" if all(p.status == "OPTIMAL" and p.checks.passed for p in (baseline, candidate)) else "failed"
    records = [*inputs.network.nodes, *inputs.network.edges, *inputs.network.demands]
    synthetic = sum(row.provenance.kind == "synthetic" for row in records) / len(records)
    manifest = {
        "schema_version": "1.1",
        "run_id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "input_hash": content_hash(identity),
        "output_hash": content_hash({"baseline": baseline.model_dump(mode="json"), "candidate": candidate.model_dump(mode="json")}),
        "seed": inputs.network.seed,
        "data_version": inputs.network.data_version,
        "generator_version": inputs.network.generator_version,
        "app_version": __version__,
        "model_version": "daily-flow-1.1",
        "policy_version": inputs.policy.version,
        "horizon_days": scenario.horizon_days,
        "unit": "kg_LPG",
        "timezone": inputs.network.timezone,
        "synthetic_record_share": synthetic,
        "provenance_measure": "Share of node, edge and demand records tagged synthetic; not a field-weighted estimate.",
        "solver": candidate.solver,
        "solver_version": candidate.solver_version,
        "solver_status": {"baseline": baseline.status, "candidate": candidate.status},
        "solver_settings": {"threads": 1, "random_seed": 0, "feasibility_tolerance_kg": 1e-5},
        "dependency_versions": {name: version(name) for name in ("ortools", "pandas", "networkx", "pydantic")},
        "python_version": platform.python_version(),
        "elapsed_seconds": time.perf_counter() - start,
        "review_required": True,
        "operational_writeback": False,
    }
    return RunBundle(
        manifest=manifest, scenario=inputs.scenario, network=inputs.network, policy=inputs.policy,
        adjusted_inputs=adjusted, baseline=baseline, candidate=candidate,
        comparison=compare_plans(baseline, candidate),
        affected_nodes=inputs.affected_nodes, affected_edges=inputs.affected_edges,
        affected_paths=inputs.affected_paths,
        warnings=list(dict.fromkeys(inputs.warnings + baseline.diagnostics + candidate.diagnostics)),
        evidence=checked_evidence,
    )


def record_review(bundle: RunBundle, note: str, acknowledged: bool) -> RunBundle:
    if not acknowledged:
        raise ModelError("REVIEW_REQUIRED", "Acknowledge the simulation-only boundary before recording review.")
    if bundle.manifest["status"] != "success" or not bundle.candidate.checks.passed:
        raise ModelError("REVIEW_BLOCKED", "Failed or infeasible plans cannot be marked reviewed.")
    if len(note) > 2000:
        raise ModelError("INPUT_VALIDATION", "Review note must be at most 2,000 characters.")
    reviewed = bundle.model_copy(deep=True)
    reviewed.review = Review(status="reviewed_simulation_only", reviewed_at=datetime.now(timezone.utc).isoformat(), note=note)
    return reviewed
