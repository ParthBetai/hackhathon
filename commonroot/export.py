"""Lossless run JSON and reproducible, spreadsheet-safe audit exports.

Export operates only on the supplied run: it never recomputes a simulation,
reads credentials, logs source text or contacts a provider.
"""

from __future__ import annotations

import csv
import io
import json
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from commonroot.contracts import ModelError

if TYPE_CHECKING:
    from commonroot.schemas import PlanResult
    from commonroot.service import RunBundle


_RISK_COLUMNS = (
    ("district_id", "district_id"),
    ("name", "district_name"),
    ("opening_stock", "opening_stock_kg_LPG"),
    ("daily_demand", "daily_demand_kg_LPG_per_day"),
    ("inbound", "inbound_kg_LPG"),
    ("closing_stock", "closing_stock_kg_LPG"),
    ("snapshot_cover", "snapshot_cover_days"),
    ("minimum_cover", "minimum_cover_days"),
    ("first_low_day", "first_low_day"),
    ("first_unmet_day", "first_unmet_day"),
    ("unmet", "unmet_kg_LPG"),
    ("fulfilled_fraction", "fulfilled_fraction"),
    ("risk", "risk"),
    ("affected", "affected"),
    ("affected_routes", "affected_routes"),
)
_SHIPMENT_COLUMNS = (
    ("edge_id", "edge_id"), ("source", "source"), ("target", "target"),
    ("day", "dispatch_day"), ("arrival_day", "arrival_day"),
    ("quantity", "quantity_kg_LPG"), ("capacity", "capacity_kg_LPG"),
    ("distance_km", "distance_km"),
)
_BALANCE_COLUMNS = (
    ("node_id", "node_id"), ("day", "day"),
    *[(name, f"{name}_kg_LPG") for name in (
        "opening", "supply", "arrivals", "departures", "served", "closing"
    )],
)
_SERVICE_COLUMNS = (
    ("district_id", "district_id"), ("group", "group"), ("day", "day"),
    ("demand", "demand_kg_LPG"), ("served", "served_kg_LPG"), ("unmet", "unmet_kg_LPG"),
)


def _canonical(value) -> str:
    # Deferred import avoids the service -> evidence/export -> service cycle.
    from commonroot.service import canonical_json

    return canonical_json(value)


def bundle_json(bundle: RunBundle) -> str:
    """Full, exact RunBundle as canonical JSON, including review and evidence."""
    return _canonical(bundle.model_dump(mode="json"))


def _csv_cell(value):
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if not isinstance(value, str):
        # csv writes numbers directly and null as an empty cell, without rounding
        # or converting negative numeric values to escaped text.
        return value
    start = 0
    while start < len(value) and (
        value[start].isspace() or ord(value[start]) < 32 or value[start] in "\ufeff\u200b"
    ):
        start += 1
    probe = value[start:]
    if value.startswith(("\t", "\r", "\n")) or probe.startswith(
        ("=", "+", "-", "@", "＝", "＋", "－", "＠")
    ):
        return "'" + value
    return value


def _valid(plan: PlanResult) -> bool:
    return plan.status == "OPTIMAL" and plan.checks.passed


def _table(plan: PlanResult, collection: str, columns) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["plan", "plan_status", "feasibility_passed", *[label for _, label in columns]])
    if _valid(plan):
        for row in getattr(plan, collection):
            values = [plan.plan_type, plan.status, plan.checks.passed]
            values.extend(getattr(row, field) for field, _ in columns)
            writer.writerow([_csv_cell(value) for value in values])
    return stream.getvalue()


def risk_csv(bundle: RunBundle, plan: str = "candidate") -> str:
    """Risk rows in kg_LPG, days and fractions; failed plans have headers only.

    Text that could be interpreted as a spreadsheet formula is apostrophe
    prefixed. The canonical unescaped strings remain available in run.json.
    """
    if plan not in ("baseline", "candidate"):
        raise ModelError("INPUT_VALIDATION", "Export plan must be baseline or candidate.")
    return _table(getattr(bundle, plan), "districts", _RISK_COLUMNS)


def _readme(bundle: RunBundle) -> str:
    plan_status = "\n".join(
        f"{name}: status={plan.status}; feasibility_passed={str(plan.checks.passed).lower()}; "
        f"CSV data rows={'included' if _valid(plan) else 'suppressed (headers only)'}"
        for name, plan in (("baseline", bundle.baseline), ("candidate", bundle.candidate))
    )
    return f"""CommonRoot simulation audit bundle
Run status: {bundle.manifest.get('status', 'unknown')}
{plan_status}

Simulation decision support only. No operational action or writeback is performed.
A reference-evidence review does not verify source truth or authorise model changes.
Scenario parameters are explicit manual assumptions, separate from source evidence.

run.json is the full, exact canonical RunBundle, including all provenance, solver
diagnostics, evidence, review, affected node/edge IDs and original numeric values.
The other JSON files are exact projections of its identically named fields:
comparison_metrics.json contains comparison; affected_paths.json contains affected_paths.
The original manifest is preserved in manifest.json, including run/solver status.

risk_by_district.csv contains candidate risk; risk_baseline.csv contains baseline risk.
plan_baseline.csv and plan_candidate.csv contain daily route shipments.
balances_<plan>.csv contain daily node stock-flow balances.
service_<plan>.csv contain daily district/group demand, service and unmet demand.
Only OPTIMAL plans with passed feasibility checks contribute CSV data rows.
Failed or unchecked plans retain their diagnostics in run.json and have header-only CSVs.

Units: all mass columns are kg_LPG; daily demand is kg_LPG/day; distance is km;
cover is days; fulfilled_fraction is a fraction, not a percentage. Days are 1-based.
Shipment capacity is the scenario-adjusted quantity limit for that dispatch day.
Shipment quantities on successive routes count the same cargo again, not consumption.
Snapshot cover uses opening stock. Minimum cover uses projected closing stock.
Nulls are JSON null and empty CSV cells, never substituted with zero.
Numbers are exported without display rounding. Text cells that could be spreadsheet
formulas are prefixed with an apostrophe; exact original text remains in run.json.

Evidence retains only explicitly reviewed source excerpts, literal extracted phrases,
exact quotes, the caller-supplied URL and extraction metadata. Excerpts are included
in run.json: review their contents before sharing this archive. Raw provider payloads
and environment configuration are not added. No export contains an executable plan.
"""


def bundle_zip(bundle: RunBundle) -> bytes:
    """In-memory audit archive; the same bundle produces the same ZIP bytes."""
    data = bundle.model_dump(mode="json")
    files = {"run.json": _canonical(data)}
    for name in ("manifest", "scenario", "network", "adjusted_inputs", "policy"):
        files[f"{name}.json"] = _canonical(data[name])
    files["risk_by_district.csv"] = risk_csv(bundle)
    files["risk_baseline.csv"] = risk_csv(bundle, "baseline")
    for name in ("baseline", "candidate"):
        plan = getattr(bundle, name)
        files[f"plan_{name}.csv"] = _table(plan, "shipments", _SHIPMENT_COLUMNS)
        files[f"balances_{name}.csv"] = _table(plan, "balances", _BALANCE_COLUMNS)
        files[f"service_{name}.csv"] = _table(plan, "service", _SERVICE_COLUMNS)
    files["comparison_metrics.json"] = _canonical(data["comparison"])
    files["affected_paths.json"] = _canonical(data["affected_paths"])
    files["warnings.json"] = _canonical(data["warnings"])
    files["README.txt"] = _readme(bundle)
    stream = io.BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for filename, text in files.items():
            info = ZipInfo(filename, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, text.encode("utf-8"), compresslevel=9)
    return stream.getvalue()
