"""Read-only report views over one exact RunBundle, plus explicit review/export actions."""

from collections.abc import Callable
from math import fsum

import pandas as pd
import streamlit as st

from app.evidence_view import render_evidence
from app.visuals import day_label, ledger, network_svg, number, percent, safe
from commonroot.schemas import PlanResult, Policy
from commonroot.service import RunBundle, record_review


def plan_valid(plan: PlanResult) -> bool:
    return plan.status == "OPTIMAL" and plan.checks.passed and plan.metrics is not None


def empty_state(message: str, detail: str | None = None) -> None:
    """Render a quiet, scannable state for views with no rows to show."""
    detail_markup = f'<span>{safe(detail)}</span>' if detail else ""
    st.html(
        f'<div class="cr-empty-state" role="status">'
        f'<span class="cr-empty-mark" aria-hidden="true">—</span>'
        f'<div><strong>{safe(message)}</strong>{detail_markup}</div></div>'
    )


def status_rail(bundle: RunBundle) -> None:
    """Show the recorded run state without turning it into an operational control."""
    manifest_status = str(bundle.manifest.get("status", "unknown"))
    candidate_ok = plan_valid(bundle.candidate)
    checks_ok = bool(getattr(bundle.candidate.checks, "passed", False))
    review_status = str(bundle.review.status).replace("_", " ")
    synthetic_share = bundle.manifest.get("synthetic_record_share")
    if synthetic_share is None:
        data_label, data_detail, data_tone = "Input provenance", "See Network & inputs", "neutral"
    elif synthetic_share == 1:
        data_label, data_detail, data_tone = "Data mode", "Synthetic record set", "neutral"
    else:
        data_label, data_detail, data_tone = "Data mode", f"{synthetic_share:.0%} synthetic", "neutral"

    items = [
        (
            "Run health",
            "Recorded success" if manifest_status == "success" else manifest_status.replace("_", " "),
            "Solver output is preserved in this snapshot" if manifest_status == "success" else "Diagnostics are available below",
            "good" if manifest_status == "success" else "attention",
        ),
        (
            "Candidate plan",
            "Checked optimal" if candidate_ok else bundle.candidate.status.replace("_", " "),
            "Risk metrics are available" if candidate_ok else "No partial allocation is presented",
            "good" if candidate_ok else "attention",
        ),
        (
            "Independent checks",
            "Passed" if checks_ok else "Needs review",
            "Balance residuals are within tolerance" if checks_ok else "Open the feasibility record",
            "good" if checks_ok else "attention",
        ),
        (data_label, data_detail, review_status.title(), data_tone),
    ]
    cells = "".join(
        f'<div class="cr-status-item cr-status-{tone}">'
        '<span class="cr-status-mark" aria-hidden="true"></span>'
        '<div class="cr-status-copy">'
        f'<span class="cr-status-label">{safe(label)}</span>'
        f'<strong>{safe(value)}</strong>'
        f'<span>{safe(detail)}</span>'
        "</div></div>"
        for label, value, detail, tone in items
    )
    st.html(f'<div class="cr-status-rail" aria-label="Recorded run status">{cells}</div>')


def table(rows: list[dict] | pd.DataFrame, *, height: int | str = "auto") -> None:
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    if frame.empty:
        empty_state("No rows in this run.", "This recorded result has no entries for the selected view.")
        return
    columns = {}
    for column in frame.columns:
        if pd.api.types.is_numeric_dtype(frame[column]) and not pd.api.types.is_bool_dtype(
            frame[column]
        ):
            unit = str(column).lower()
            precision = "%.2f" if any(word in unit for word in ("kg", "cover", "%", "error")) else None
            if "tolerance" in unit or "error" in unit:
                precision = "%.7f"
            if precision:
                columns[column] = st.column_config.NumberColumn(format=precision)
    st.dataframe(frame, hide_index=True, width="stretch", height=height, column_config=columns)


def section(title: str, caption: str | None = None) -> None:
    st.html('<div class="cr-section-rule" aria-hidden="true"></div>')
    st.subheader(title)
    if caption:
        st.caption(caption)


def render_policy(policy: Policy, *, compact: bool = False) -> None:
    st.text(policy.name)
    st.caption(f"{policy.id} · version {policy.version}")
    if policy.illustrative:
        st.caption("Illustrative engineering assumption. This is not an official allocation order.")
    if policy.id == "synthetic_infeasible_floor_v1":
        st.warning(
            "Infeasibility stress-test fixture. Its 100% hard floors and verification flag "
            "are test settings, not verification of any real-world law or authority."
        )
    rows = [
        {
            "Tier": rank,
            "Group": group,
            "Minimum": percent(policy.minimum_fractions[group])
            if group in policy.minimum_fractions else "Not configured",
            "Hard floor": policy.enforce_minimums and policy.minimums_verified
            and group in policy.minimum_fractions,
            "Cap": percent(policy.caps[group]) if group in policy.caps else "Demand bound only",
        }
        for rank, tier in enumerate(policy.tiers, start=1)
        for group in tier
    ]
    table(rows)
    st.caption(
        "Floors and caps apply per district, group and day. Tier order and group names are "
        "input assumptions. Groups sharing a tier have the same priority."
    )
    if not compact:
        st.text(policy.description)
        st.json(policy.model_dump(mode="json"), expanded=False)


def render_checks(bundle: RunBundle) -> None:
    section("Feasibility & objective record", "Solver status and independent checks from this run.")
    table([
        {
            "Plan": label,
            "Solver status": plan.status,
            "Checks passed": plan.checks.passed,
            "Maximum balance error kg": plan.checks.max_balance_error,
            "Tolerance kg": plan.checks.tolerance,
            "Violation count": len(plan.checks.violations),
            "Solver": f"{plan.solver} {plan.solver_version}",
        }
        for label, plan in (("Baseline", bundle.baseline), ("Candidate", bundle.candidate))
    ])
    st.caption("Tolerance and residuals below are shown at their recorded precision.")
    for label, plan in (("Baseline", bundle.baseline), ("Candidate", bundle.candidate)):
        with st.expander(f"{label} · staged objectives, checks and binding labels"):
            st.json(plan.checks.model_dump(mode="json"), expanded=True)
            if plan.stages:
                table([
                    {
                        "Order": stage.get("order"),
                        "Stage": stage.get("name"),
                        "Sense": stage.get("sense"),
                        "Status": stage.get("status"),
                        "Objective value": stage.get("objective_value"),
                        "Locked": stage.get("locked"),
                    }
                    for stage in plan.stages
                ])
                st.caption(
                    "Objectives are solved in the recorded order; locked objectives constrain "
                    "later stages. Values use each stage's own objective definition."
                )
                st.json(plan.stages, expanded=False)
            else:
                st.caption("No objective stages were returned.")
            if plan.binding_constraints:
                st.caption(
                    "Binding labels are tight primal bounds, including zero-capacity bounds. "
                    "They are not causal sensitivities or a minimal conflicting set."
                )
                table([{"Binding constraint": label} for label in plan.binding_constraints], height=240)
            else:
                st.caption("No binding labels were returned for this plan.")
            for diagnostic in plan.diagnostics:
                st.text(diagnostic)


def invalid_plan_message(plan: PlanResult, name: str = "Candidate") -> None:
    st.html(
        f'<div class="cr-error-state"><span class="cr-error-kicker">CHECKED RESULT UNAVAILABLE</span>'
        f'<strong>{safe(name)} plan requires attention</strong>'
        '<span>Diagnostics are retained; no partial allocation is presented as a valid plan.</span></div>'
    )
    st.error(
        f"{name} status: {plan.status}. A checked optimal result is required for risk metrics "
        "and allocation charts. No partial allocation is presented as a valid plan."
    )
    for diagnostic in plan.diagnostics:
        st.text(diagnostic)


def daily_service(plan: PlanResult, district_id: str | None = None) -> pd.DataFrame:
    rows = [row.model_dump() for row in plan.service if district_id is None
            or row.district_id == district_id]
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).groupby("day", as_index=False)[["demand", "served", "unmet"]].sum().rename(
        columns={"day": "Day", "demand": "Demand kg", "served": "Served kg", "unmet": "Unmet kg"}
    )


def render_overview(bundle: RunBundle) -> None:
    plan = bundle.candidate
    status_rail(bundle)
    if bundle.manifest.get("status") != "success" or not plan_valid(plan):
        empty_state(
            "A checked candidate plan is not available",
            "Use the feasibility record below to understand the recorded solver outcome.",
        )
        st.error("This run failed or is infeasible. Review the solver and constraint record below.")
        if not plan_valid(plan):
            invalid_plan_message(plan)
        else:
            st.info("The candidate is checked, but the full run did not succeed. Review the baseline diagnostics.")
        render_checks(bundle)
        return
    metrics = plan.metrics
    first_low = min((row.first_low_day for row in plan.districts if row.first_low_day is not None),
                    default=None)
    first_low_text = day_label(first_low) if any(row.minimum_cover is not None for row in plan.districts) else "Not computable"
    st.html(
        '<div class="cr-panel-kicker"><span>RUN AT A GLANCE</span>'
        '<strong>What this recorded plan says at a glance</strong>'
        '<small>Mass, service and cover signals are calculated from the displayed snapshot.</small></div>'
    )
    st.html(ledger([
        ("Available mass", number(metrics.total_available), "kg LPG · opening stock + external supply"),
        ("Horizon demand", number(metrics.total_demand), f"kg LPG · {bundle.scenario.horizon_days} days"),
        ("Demand fulfilled", percent(metrics.fulfilment), f"{number(metrics.total_served)} kg served"),
        ("Unmet demand", number(metrics.total_unmet), "kg LPG · demand not served within its day"),
        ("Elevated districts", str(metrics.elevated_districts), "High or Watch · candidate plan"),
        ("First low cover", first_low_text, f"Closing cover < {bundle.scenario.cover_threshold:g} days"),
    ]))
    st.caption(
        f"Candidate plan. Available mass = {number(metrics.initial_stock)} kg opening stock + "
        f"{number(metrics.total_supply)} kg external supply (Q). Shipments across multiple hops "
        "are not added as new supply. First low cover comes from the computed district trajectories."
    )
    section("The supply corridor", "A topology sketch of this run's network — layout coordinates, not a map.")
    st.html(network_svg(bundle.network, bundle.affected_nodes, bundle.affected_edges,
                        id_prefix="cr-overview"))
    st.caption(
        "Exposed paths show possible downstream dependencies in the originally active network. "
        "They do not establish actual shipments or a confirmed shortage. Inspect assets in Network & inputs."
    )
    st.divider()
    section("Service through the horizon", "All districts and groups · kg LPG per day · candidate plan")
    st.html('<div class="cr-chart-label"><span>DAILY SERVICE</span><small>Served and unmet quantities, stacked by day</small></div>')
    daily = daily_service(plan)
    if not daily.empty:
        st.bar_chart(daily, x="Day", y=["Served kg", "Unmet kg"],
                     color=["#164B50", "#8A3F4C"], stack=True, height=270)
        with st.expander("Daily service table"):
            table(daily)
    final_stock = fsum(row.closing for row in plan.balances
                       if row.day == bundle.scenario.horizon_days)
    with st.expander("Mass-balance reconciliation"):
        table([
            {"Balance term": "Opening stock", "kg LPG": metrics.initial_stock},
            {"Balance term": "External supply Q", "kg LPG": metrics.total_supply},
            {"Balance term": "Available (opening + Q)", "kg LPG": metrics.total_available},
            {"Balance term": "Served", "kg LPG": metrics.total_served},
            {"Balance term": "Closing stock, all nodes", "kg LPG": final_stock},
            {"Balance term": "In transit beyond horizon", "kg LPG": metrics.in_transit},
        ])
        st.caption("Opening stock + Q = served + final stock + in-transit mass. Unmet demand is not stock.")
    st.info(bundle.comparison.get("explanation", "No comparison explanation was returned."))


def render_districts(bundle: RunBundle) -> None:
    plan = bundle.candidate
    if not plan_valid(plan):
        invalid_plan_message(plan)
        return
    section("District risk register", "Candidate plan · search names or IDs; column headers also support sorting.")
    search_col, sort_col = st.columns([2, 1])
    with search_col:
        query = st.text_input("Find a district", key="district_search", placeholder="Name or district ID")
    with sort_col:
        sort = st.selectbox("Order districts", ["Risk, then unmet", "Unmet demand", "First low day", "Name"],
                            key="district_sort")
    risks = [row for row in plan.districts if query.casefold() in f"{row.name} {row.district_id}".casefold()]
    risk_rank = {"High": 0, "Watch": 1, "Stable": 2, "Not computable": 3}
    keys = {
        "Risk, then unmet": lambda row: (risk_rank[row.risk], -row.unmet, row.name),
        "Unmet demand": lambda row: (-row.unmet, row.name),
        "First low day": lambda row: (row.first_low_day if row.first_low_day is not None else 999, row.name),
        "Name": lambda row: row.name,
    }
    risks.sort(key=keys[sort])
    if not risks:
        empty_state(
            "No districts match this search",
            "Clear the search to see every district in the recorded candidate register.",
        )
        st.info("No districts match this search. Clear the search to see this run's register.")
        return
    table([
        {
            "District": row.name, "District ID": row.district_id, "Risk": row.risk,
            "Unmet kg": row.unmet,
            "Fulfilment %": None if row.fulfilled_fraction is None else row.fulfilled_fraction * 100,
            "Snapshot cover d": row.snapshot_cover, "Minimum closing cover d": row.minimum_cover,
            "First low day": row.first_low_day, "First unmet day": row.first_unmet_day,
            "Opening kg": row.opening_stock, "Daily demand kg": row.daily_demand,
            "Inbound kg": row.inbound, "Closing kg": row.closing_stock,
            "Exposed dependency": row.affected,
        }
        for row in risks
    ])
    st.caption(
        "High: unmet demand above the recorded numerical tolerance. Watch: closing cover below "
        "the selected threshold with no unmet demand. Stable: computable cover with neither condition. "
        "Zero or unknown demand gives Not computable cover. Blank days mean no first event was returned; "
        "check cover computability before interpreting first-low day."
    )
    selected = st.selectbox("Inspect district", [row.district_id for row in risks],
                            format_func=lambda value: next(row.name for row in risks if row.district_id == value),
                            key=f"district_detail_{bundle.manifest['run_id']}")
    district = next(row for row in risks if row.district_id == selected)
    st.divider()
    section(district.name, f"{district.risk} · {district.district_id}")
    risk_class = safe(district.risk).lower().replace(" ", "-")
    st.html(
        f'<div class="cr-detail-ribbon cr-detail-{risk_class}">'
        f'<span>SELECTED DISTRICT</span><strong>{safe(district.name)}</strong>'
        f'<small>{safe(district.risk)} · {safe(district.district_id)}</small></div>'
    )
    st.html(ledger([
        ("Opening snapshot cover", number(district.snapshot_cover, 2), "opening stock ÷ average daily demand"),
        ("Minimum closing cover", number(district.minimum_cover, 2), "lowest daily closing stock ÷ daily demand"),
        ("First low day", day_label(district.first_low_day) if district.minimum_cover is not None else "Not computable",
         "first projected close below the risk threshold"),
    ]))
    balance_rows = [row for row in plan.balances if row.node_id == selected]
    balances = pd.DataFrame([row.model_dump() for row in balance_rows]).sort_values("day")
    daily = daily_service(plan, selected)
    cover = pd.DataFrame({
        "Day": balances["day"],
        "Closing cover (days)": [row.closing / district.daily_demand
                                 if district.daily_demand > 0 else None for row in sorted(balance_rows, key=lambda r: r.day)],
        "Risk threshold (days)": bundle.scenario.cover_threshold,
    })
    if district.daily_demand > 0:
        st.html('<div class="cr-chart-label"><span>COVER TRAJECTORY</span><small>Closing cover against the selected threshold</small></div>')
        st.line_chart(cover, x="Day", y=["Closing cover (days)", "Risk threshold (days)"],
                      color=["#164B50", "#AD762C"], height=250)
    else:
        st.info("Cover cannot be computed because this district's scenario-adjusted daily demand is zero.")
    with st.expander("Daily cover table"):
        table(cover)
    st.caption(
        f"Snapshot cover is {number(district.opening_stock, 2)} ÷ "
        f"{number(district.daily_demand, 2)}. It is not a predicted shortage date. "
        f"First low tests each closing cover against {bundle.scenario.cover_threshold:g} days; "
        f"first unmet demand is {day_label(district.first_unmet_day).lower()}."
    )
    st.html('<div class="cr-chart-label"><span>DISTRICT SERVICE</span><small>Daily served and unmet demand for the selected district</small></div>')
    st.bar_chart(daily, x="Day", y=["Served kg", "Unmet kg"], color=["#164B50", "#8A3F4C"],
                 stack=True, height=220)
    with st.expander("Daily service and balance tables", expanded=True):
        table(daily)
        table(balances.drop(columns="node_id").rename(columns={
            "day": "Day", "opening": "Opening kg", "supply": "External supply kg",
            "arrivals": "Arrivals kg", "departures": "Departures kg", "served": "Served kg", "closing": "Closing kg",
        }))
        st.caption("Closing = opening + external supply + arrivals − departures − served. Arrivals must occur within the horizon.")
    section("Affected upstream routes")
    if district.affected_routes:
        route_table(bundle, district.affected_routes)
    else:
        st.caption("No affected upstream routes were recorded for this district.")
    for path in bundle.affected_paths:
        if path.get("district_id") == selected:
            st.text(path.get("explanation", ""))
            st.json(path, expanded=False)


def comparison_quantities(bundle: RunBundle, group_by: list[str]) -> pd.DataFrame:
    frames = []
    for label, plan in (("Baseline", bundle.baseline), ("Candidate", bundle.candidate)):
        frame = pd.DataFrame([row.model_dump() for row in plan.service])
        grouped = frame.groupby(group_by)[["demand", "served", "unmet"]].sum()
        grouped.columns = [f"{label} {column} kg" for column in grouped.columns]
        frames.append(grouped)
    result = frames[0].join(frames[1], how="outer").reset_index()
    for label in ("Baseline", "Candidate"):
        denominator = result[f"{label} demand kg"].replace(0, float("nan"))
        result[f"{label} fulfilment %"] = result[f"{label} served kg"] / denominator * 100
    result["Candidate − baseline served kg"] = result["Candidate served kg"] - result["Baseline served kg"]
    names = {node.id: node.name for node in bundle.network.nodes}
    if "district_id" in result:
        result.insert(0, "District", result["district_id"].map(names))
    return result.rename(columns={"district_id": "District ID", "group": "Group"})


def render_comparison(bundle: RunBundle) -> None:
    section("Two computed plans, one input snapshot")
    st.html(
        '<div class="cr-comparison-intro"><span class="cr-panel-kicker">COMPARISON LENS</span>'
        '<strong>Read the candidate against the same physical inputs</strong>'
        '<small>Differences below come from the recorded planning methods, not a second network.</small></div>'
    )
    st.info(bundle.comparison.get("explanation", "No comparison explanation was returned."))
    if not bundle.comparison.get("available") or not all(
        plan_valid(plan) for plan in (bundle.baseline, bundle.candidate)
    ):
        render_checks(bundle)
        return
    for field, title in (("baseline_method", "Baseline"), ("candidate_method", "Candidate"),
                         ("objective_scope", "Objective scope")):
        if bundle.comparison.get(field):
            st.markdown(f"**{title}**")
            st.text(bundle.comparison[field])
    baseline, candidate = bundle.baseline.metrics, bundle.candidate.metrics
    table([
        {"Measure": "Served (kg LPG)", "Baseline": number(baseline.total_served, 2), "Candidate": number(candidate.total_served, 2)},
        {"Measure": "Unmet (kg LPG)", "Baseline": number(baseline.total_unmet, 2), "Candidate": number(candidate.total_unmet, 2)},
        {"Measure": "Fulfilment", "Baseline": percent(baseline.fulfilment), "Candidate": percent(candidate.fulfilment)},
        {"Measure": "Distance proxy (kg·km)", "Baseline": number(baseline.distance_kg_km, 2), "Candidate": number(candidate.distance_kg_km, 2)},
        {"Measure": "In transit beyond horizon (kg LPG)", "Baseline": number(baseline.in_transit, 2), "Candidate": number(candidate.in_transit, 2)},
        {"Measure": "Cost", "Baseline": "Unavailable", "Candidate": "Unavailable"},
        {"Measure": "Emissions", "Baseline": "Unavailable", "Candidate": "Unavailable"},
    ])
    st.caption(bundle.comparison.get("proxy_warning", "No cost or emissions factors supplied."))
    st.divider()
    section("Service by priority group", "Both plans' demand, served and unmet quantities; kg LPG over the horizon.")
    table(comparison_quantities(bundle, ["group"]))
    section("Service by district")
    table(comparison_quantities(bundle, ["district_id"]))
    section("District coverage & exposure")
    base_districts = {row.district_id: row for row in bundle.baseline.districts}
    table([
        {"District": row.name,
         "Baseline risk": base_districts[row.district_id].risk,
         "Candidate risk": row.risk,
         "Baseline min cover d": base_districts[row.district_id].minimum_cover,
         "Candidate min cover d": row.minimum_cover,
         "Baseline first unmet day": base_districts[row.district_id].first_unmet_day,
         "Candidate first unmet day": row.first_unmet_day}
        for row in bundle.candidate.districts
    ])
    with st.expander("District × group quantity breakdown"):
        table(comparison_quantities(bundle, ["district_id", "group"]))
    render_checks(bundle)


def route_table(bundle: RunBundle, edge_ids: list[str] | None = None) -> None:
    names = {node.id: node.name for node in bundle.network.nodes}
    table([
        {
            "Route ID": edge.id, "From": names[edge.source], "To": names[edge.target],
            "Nominal capacity kg/day": edge.capacity, "Nominal lead days": edge.lead_days,
            "Distance km": edge.distance_km, "Originally active": edge.active,
            "Exposed dependency": edge.id in bundle.affected_edges,
        }
        for edge in bundle.network.edges if edge_ids is None or edge.id in edge_ids
    ])


def schedule(bundle: RunBundle, field: str, asset_id: str) -> dict[int, float]:
    return {
        row["key"][-1]: row["value"]
        for row in bundle.adjusted_inputs.get(field, []) if row["key"][0] == asset_id
    }


def render_network(bundle: RunBundle) -> None:
    section("Network & exact inputs", "The network, policy and adjusted schedules attached to the displayed run.")
    st.html(
        '<div class="cr-input-note"><span>INPUT SNAPSHOT</span>'
        '<strong>Inspect the exact assets behind this run</strong>'
        '<small>Select a node or route to move from topology to its adjusted schedule.</small></div>'
    )
    names = {node.id: node.name for node in bundle.network.nodes}
    labels = {f"node:{node.id}": f"{node.kind.title()} · {node.name} [{node.id}]" for node in bundle.network.nodes}
    labels.update({f"edge:{edge.id}": f"Route · {names[edge.source]} → {names[edge.target]} [{edge.id}]"
                   for edge in bundle.network.edges})
    selected = st.selectbox("Inspect network asset", list(labels), format_func=labels.get,
                            key=f"network_asset_{bundle.manifest['run_id']}")
    st.html(network_svg(bundle.network, bundle.affected_nodes, bundle.affected_edges, selected))
    st.caption(
        "All positions come from input x/y coordinates; they are not geolocation. "
        "The ochre exposure trace uses original topology, including temporarily disrupted routes. "
        "Scheduled capacity and actual checked shipments appear below."
    )
    asset_type, asset_id = selected.split(":", 1)
    if asset_type == "edge":
        edge = next(edge for edge in bundle.network.edges if edge.id == asset_id)
        route_table(bundle, [asset_id])
        cap, arrival = schedule(bundle, "edge_capacity", asset_id), schedule(bundle, "arrival_day", asset_id)
        actual = {row.day: row for row in bundle.candidate.shipments if row.edge_id == asset_id}
        table([
            {
                "Dispatch day": day, "Adjusted capacity kg": cap.get(day),
                "Arrival day": arrival.get(day),
                "Beyond horizon": arrival.get(day, day) > bundle.scenario.horizon_days,
                "Candidate dispatched kg": actual[day].quantity
                if plan_valid(bundle.candidate) and day in actual else None,
            }
            for day in range(1, bundle.scenario.horizon_days + 1)
        ])
        st.caption("Dispatch-day schedule. Capacity is a limit, not a shipment. Blank dispatched quantities are unavailable.")
        st.json(edge.model_dump(mode="json"), expanded=False)
    else:
        node = next(node for node in bundle.network.nodes if node.id == asset_id)
        supply = schedule(bundle, "supply", asset_id)
        dispatch = schedule(bundle, "dispatch_capacity", asset_id)
        table([{"Node": node.name, "Kind": node.kind, "Initial stock kg": node.initial_stock,
                "Nominal supply kg/day": node.daily_supply, "Nominal dispatch kg/day": node.dispatch_capacity,
                "Originally active": node.active}])
        with st.expander("Adjusted supply and dispatch schedule"):
            table([{"Day": day, "External supply kg": supply.get(day), "Dispatch limit kg": dispatch.get(day)}
                   for day in range(1, bundle.scenario.horizon_days + 1)])
        if plan_valid(bundle.candidate):
            table([row.model_dump() for row in bundle.candidate.balances if row.node_id == asset_id])
            st.caption("Candidate daily balance: closing = opening + supply + arrivals − departures − served; all mass is kg LPG.")
        else:
            st.caption("A checked candidate balance series is unavailable for this failed run.")
        st.json(node.model_dump(mode="json"), expanded=False)
    st.divider()
    with st.expander("All route inputs"):
        route_table(bundle)
    with st.expander("All node and demand inputs"):
        table([node.model_dump(exclude={"provenance"}) for node in bundle.network.nodes])
        table([row.model_dump(exclude={"provenance"}) for row in bundle.network.demands])
    with st.expander("Policy tiers, floors and caps", expanded=False):
        render_policy(bundle.policy)
    with st.expander("Applied scenario and exact adjusted schedules"):
        st.json(bundle.scenario.model_dump(mode="json"), expanded=True)
        st.json(bundle.adjusted_inputs, expanded=False)
    with st.expander("Provenance, assumptions & model limitations"):
        st.caption(bundle.manifest.get("provenance_measure", "Record-level provenance is in the network JSON."))
        for warning in bundle.warnings:
            st.text(warning)
        st.json(bundle.network.model_dump(mode="json"), expanded=False)


def render_review(bundle: RunBundle, accept_review: Callable[[RunBundle], None]) -> None:
    section("Review a simulation", "Recording a review saves an audit annotation. It does not execute an allocation or dispatch.")
    st.html(
        '<div class="cr-review-banner"><span>HUMAN CHECKPOINT</span>'
        '<strong>Record what you inspected before sharing the run</strong>'
        '<small>The review is stored with this exact snapshot and cannot change solver output.</small></div>'
    )
    st.caption(f"Review target: {bundle.manifest['run_id']} · {bundle.review.status}")
    if bundle.review.reviewed_at:
        st.caption(f"Reviewed at {bundle.review.reviewed_at} · operational action: {bundle.review.operational_action}")
        if bundle.review.note:
            st.text(bundle.review.note)
    review_allowed = bundle.manifest.get("status") == "success" and plan_valid(bundle.candidate)
    if not review_allowed:
        st.warning("Failed or infeasible plans cannot be marked reviewed. Their diagnostics can still be exported.")
    # Keep drafts in keyed widgets rather than a batched form: a sidebar rerun
    # must not discard an unsubmitted review note or acknowledgement.
    with st.container(border=True):
        note = st.text_area("Review note", value=bundle.review.note, max_chars=2000,
                            placeholder="Record assumptions, constraints and follow-up questions.",
                            key=f"review_note_{bundle.manifest['run_id']}")
        acknowledged = st.checkbox(
            "I acknowledge this is a simulation-only review; no operational action will be taken.",
            key=f"review_ack_{bundle.manifest['run_id']}",
        )
        submitted = st.button("Record review", disabled=not review_allowed)
    if submitted:
        try:
            from commonroot.store import save_run

            reviewed = record_review(bundle, note, acknowledged)
            save_run(reviewed)
        except Exception as exc:
            st.error(f"Review was not saved: {getattr(exc, 'code', type(exc).__name__)} — {exc}")
        else:
            accept_review(reviewed)
            st.rerun()
    st.divider()
    section("Export this exact run", "Each download refers to the displayed run, including its inputs, computed outputs and review state.")
    if not plan_valid(bundle.candidate):
        st.caption("Risk CSV is unavailable without a checked candidate result. JSON and ZIP retain failure diagnostics.")
    export_specs = [
        ("Run bundle JSON", "bundle_json", "json", "application/json"),
        ("Candidate risk CSV", "risk_csv", "csv", "text/csv"),
        ("Audit bundle ZIP", "bundle_zip", "zip", "application/zip"),
    ]
    columns = st.columns(3)
    for column, (label, function, extension, mime) in zip(columns, export_specs):
        with column:
            if function == "risk_csv" and not plan_valid(bundle.candidate):
                st.button(label, disabled=True)
                continue
            try:
                from commonroot import export

                operation = getattr(export, function)
                data = operation(bundle, plan="candidate") if function == "risk_csv" else operation(bundle)
            except Exception as exc:
                st.error(f"{label} unavailable: {getattr(exc, 'code', type(exc).__name__)} — {exc}")
            else:
                st.download_button(label, data=data,
                                   file_name=f"commonroot-{bundle.manifest['run_id']}.{extension}",
                                   mime=mime, on_click="ignore", width="stretch")
    with st.expander("Run manifest and integrity hashes"):
        st.json(bundle.manifest, expanded=True)
    if bundle.evidence:
        with st.expander("Evidence saved with this run"):
            st.json(bundle.evidence, expanded=False)
    st.html(
        '<p class="cr-footnote">CommonRoot · Simulation-only decision support. '
        f'Input snapshot <code>{safe(bundle.manifest.get("input_hash", "Unavailable"))}</code>. '
        'All calculations use the displayed run; changing the scenario desk creates a draft.</p>'
    )


def render_tabs(bundle: RunBundle, accept_review: Callable[[RunBundle], None]) -> None:
    tabs = st.tabs(["Overview", "District risk", "Compare plans", "Network & inputs", "Review & export", "Source review"])
    for tab, renderer in zip(tabs[:4], (render_overview, render_districts, render_comparison, render_network)):
        with tab:
            renderer(bundle)
    with tabs[4]:
        render_review(bundle, accept_review)
    with tabs[5]:
        render_evidence(bundle)
