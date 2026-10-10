r"""Launch with: .venv\Scripts\python.exe -m streamlit run app/streamlit_app.py.

Widgets edit a draft. Only initialization, Run simulation, or explicit reopening
may replace current_bundle. Every report reads that bundle, never live controls.
"""

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from app.views import render_policy, render_tabs  # noqa: E402
from app.visuals import report_header  # noqa: E402
from commonroot.contracts import ModelError  # noqa: E402
from commonroot.data import (  # noqa: E402
    DEMO_DIR,
    MAX_FILE_BYTES,
    demo_scenarios,
    generate_network,
    load_network,
    load_policy,
)
from commonroot.scenario import FACILITY_KINDS, SOURCE_KINDS, apply_scenario  # noqa: E402
from commonroot.schemas import NetworkData, Policy, Scenario  # noqa: E402
from commonroot.service import RunBundle, content_hash, run_simulation  # noqa: E402

PRESET_LABELS = {
    "normal": "Normal supply",
    "import_shock": "Import shock",
    "route_closure": "Route closure",
    "route_delay": "Route delay",
    "facility_outage": "Facility outage",
}
POLICY_LABELS = {
    "regular": "Illustrative regular policy",
    "stress": "Infeasibility stress test",
    "stored": "Stored policy snapshot",
}
NETWORK_LABELS = {
    "generated": "Generated synthetic network",
    "upload": "Upload network JSON",
    "stored": "Reopened network snapshot",
}


def error_text(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(
            f"{'.'.join(map(str, row['loc'])) or 'Scenario'}: {row['msg']}"
            for row in exc.errors(include_url=False, include_input=False)
        )
    return f"{getattr(exc, 'code', type(exc).__name__)} — {exc}"


def put_scenario(scenario: Scenario) -> None:
    for field, value in scenario.model_dump(mode="python").items():
        st.session_state[f"draft_{field}"] = value


def preset_changed() -> None:
    put_scenario(demo_scenarios()[st.session_state["draft_preset"]])
    st.session_state.pop("run_error", None)


def accept_bundle(bundle: RunBundle) -> None:
    st.session_state["current_bundle"] = bundle
    st.session_state["session_runs"][bundle.manifest["run_id"]] = bundle


def save_bundle(bundle: RunBundle) -> None:
    run_id = bundle.manifest["run_id"]
    try:
        from commonroot.store import save_run

        path = save_run(bundle)
    except Exception as exc:
        st.session_state["store_receipts"][run_id] = {"saved": False, "error": error_text(exc)}
    else:
        st.session_state["store_receipts"][run_id] = {"saved": True, "path": str(path)}


def accept_review(bundle: RunBundle) -> None:
    # The view records and saves the review before calling this function.
    accept_bundle(bundle)
    st.session_state["store_receipts"][bundle.manifest["run_id"]] = {"saved": True}
    st.session_state["review_notice"] = bundle.manifest["run_id"]


def initialize() -> None:
    if "draft_preset" not in st.session_state:
        st.session_state["draft_preset"] = "import_shock"
        st.session_state["draft_policy_choice"] = "regular"
        st.session_state["draft_network_mode"] = "generated"
        st.session_state["session_runs"] = {}
        st.session_state["store_receipts"] = {}
        put_scenario(demo_scenarios()["import_shock"])
    if not st.session_state.get("default_attempted"):
        st.session_state["default_attempted"] = True
        try:
            with st.spinner("Computing the default synthetic run…"):
                scenario = demo_scenarios()["import_shock"]
                network, policy = generate_network(scenario.seed), load_policy()
                apply_scenario(network, scenario, policy)
                bundle = run_simulation(scenario, network=network, policy=policy)
        except Exception as exc:
            st.session_state["run_error"] = error_text(exc)
        else:
            accept_bundle(bundle)
            save_bundle(bundle)


@st.cache_data(show_spinner=False, max_entries=4)
def uploaded_network(payload: bytes) -> NetworkData:
    """Use the core's full file validator, including metadata and duplicate keys."""
    if len(payload) > MAX_FILE_BYTES:
        raise ModelError("INPUT_VALIDATION", "Network JSON exceeds the 5,000,000-byte limit.")
    with TemporaryDirectory(prefix="commonroot-upload-") as directory:
        path = Path(directory) / "network.json"
        path.write_bytes(payload)
        return load_network(path)


def draft_network() -> tuple[NetworkData | None, str | None]:
    mode = st.session_state["draft_network_mode"]
    try:
        if mode == "stored":
            return st.session_state["pinned_network"].model_copy(deep=True), None
        if mode == "upload":
            file = st.session_state.get("network_upload")
            if file is None:
                return None, "Choose a network JSON file, or select the generated synthetic network."
            if file.size > MAX_FILE_BYTES:
                raise ModelError("INPUT_VALIDATION", "Network JSON exceeds the 5,000,000-byte limit.")
            return uploaded_network(file.getvalue()), None
        return generate_network(int(st.session_state["draft_seed"])), None
    except Exception as exc:
        return None, error_text(exc)


def selected_policy() -> Policy:
    selected = st.session_state["draft_policy_choice"]
    if selected == "stored":
        return st.session_state["pinned_policy"].model_copy(deep=True)
    return load_policy(DEMO_DIR / "policy_infeasible.json" if selected == "stress" else None)


def asset_choices(network: NetworkData | None, event_type: str) -> tuple[str, dict[str, str]]:
    if event_type == "none":
        return "Affected asset", {"": "No disruption asset"}
    if event_type in {"route_closure", "route_delay"}:
        if network is None:
            return "Affected route", {}
        names = {node.id: node.name for node in network.nodes}
        return "Affected route", {
            edge.id: f"{names[edge.source]} → {names[edge.target]} [{edge.id}]"
            + (" · inactive" if not edge.active else "") for edge in network.edges
        }
    source = event_type == "supply_reduction"
    kinds = SOURCE_KINDS if source else FACILITY_KINDS
    return "Affected source" if source else "Affected facility", {
        node.id: f"{node.name} · {node.kind} [{node.id}]" + (" · inactive" if not node.active else "")
        for node in network.nodes if node.kind in kinds
    } if network is not None else {}


def draft_values() -> dict:
    return {field: st.session_state[f"draft_{field}"] for field in Scenario.model_fields}


def signature(scenario: Scenario, network: NetworkData, policy: Policy) -> str:
    return content_hash({
        "scenario": scenario.model_dump(mode="json"),
        "network": network.model_dump(mode="json"),
        "policy": policy.model_dump(mode="json"),
    })


def reopen_run(run_id: str) -> None:
    try:
        if run_id in st.session_state.get("persisted_run_ids", []):
            from commonroot.store import load_run

            bundle = load_run(run_id)
        else:
            bundle = st.session_state["session_runs"][run_id].model_copy(deep=True)
        # No call to run_simulation: this is the exact saved result and original ID.
        accept_bundle(bundle)
        st.session_state["pinned_network"] = bundle.network.model_copy(deep=True)
        st.session_state["pinned_policy"] = bundle.policy.model_copy(deep=True)
        st.session_state["draft_network_mode"] = "stored"
        st.session_state["draft_policy_choice"] = "stored"
        preset = next(key for key, value in demo_scenarios().items()
                      if value.event_type == bundle.scenario.event_type)
        st.session_state["draft_preset"] = preset
        put_scenario(bundle.scenario)
        st.session_state["confirmed_evidence"] = bundle.evidence
        st.session_state.pop("run_error", None)
        st.session_state.pop("history_error", None)
    except Exception as exc:
        st.session_state["history_error"] = f"Run was not reopened: {error_text(exc)}"


def render_history() -> None:
    with st.expander("Run history", expanded=False):
        records = {}
        try:
            from commonroot.store import list_runs

            stored = list_runs()
            records = {row["run_id"]: row for row in stored}
            st.session_state["persisted_run_ids"] = list(records)
        except Exception as exc:
            st.session_state["persisted_run_ids"] = []
            st.caption(f"Stored history unavailable: {error_text(exc)}")
        for run_id, bundle in st.session_state["session_runs"].items():
            records[run_id] = {
                **bundle.manifest, "scenario_name": bundle.scenario.name,
                "review_status": bundle.review.status,
            }
        if not records:
            st.caption("No completed runs are available yet.")
            return
        ordered = sorted(records, key=lambda run_id: str(records[run_id].get("created_at", "")), reverse=True)
        persisted_ids = set(st.session_state["persisted_run_ids"])

        def label(run_id: str) -> str:
            record = records[run_id]
            name = record.get("scenario_name", record.get("name", "Saved simulation"))
            location = "stored" if run_id in persisted_ids else "session only"
            return f"{name} · {run_id[:8]} · {record.get('status', 'unknown')} · {location}"

        selected = st.selectbox("Saved or session run", ordered, format_func=label, key="history_selected")
        record = records[selected]
        st.caption(f"{record.get('created_at', 'Time unavailable')} · {record.get('review_status', 'not_reviewed')}")
        st.caption(f"Exact run ID: {selected}")
        st.button("Reopen selected run", on_click=reopen_run, args=(selected,), width="stretch")
        st.caption("Reopens recorded inputs and outputs with the original run ID. No new solver run.")
        if st.session_state.get("history_error"):
            st.error(st.session_state["history_error"])


def render_sidebar() -> tuple[dict, NetworkData | None, Policy | None, str | None, bool]:
    with st.sidebar:
        st.html('<div class="cr-sidebar-brand">CommonRoot</div><div class="cr-sidebar-label">SCENARIO DESK</div>')
        st.link_button("Back to introduction", os.environ.get("COMMONROOT_LANDING_URL", "http://localhost:5173"), icon=":material/arrow_back:")
        st.selectbox("Scenario preset", list(PRESET_LABELS), format_func=PRESET_LABELS.get,
                     key="draft_preset", on_change=preset_changed)
        st.text_input("Scenario title", key="draft_name", max_chars=120)
        st.caption("Presets populate a draft. The displayed report changes only when you run it.")
        with st.expander("Network source & seed", expanded=False):
            options = ["generated", "upload"] + (["stored"] if "pinned_network" in st.session_state else [])
            st.selectbox("Network input", options, format_func=NETWORK_LABELS.get, key="draft_network_mode")
            st.number_input("Seed", min_value=0, max_value=999999, step=1, key="draft_seed",
                            help="Only the generated network varies with seed. Uploaded or reopened inputs remain unchanged.")
            if st.session_state["draft_network_mode"] == "upload":
                st.file_uploader("Network JSON (up to 5 MB)", type=["json"], key="network_upload")
                st.caption("Requires the complete NetworkData schema, explicit provenance, kg_LPG units and valid references.")
            elif st.session_state["draft_network_mode"] == "stored":
                st.caption("Exact network from the reopened run. Change the source to generate a different input.")
        network, input_error = draft_network()
        event = st.session_state["draft_event_type"]
        label, choices = asset_choices(network, event)
        if event == "none":
            # No-event scenarios ignore affected_id; preserve an exact reopened
            # snapshot even if it retained an otherwise unused asset identifier.
            choices = {st.session_state["draft_affected_id"]: "No disruption asset (reference scenario)"}
        if st.session_state["draft_affected_id"] not in choices:
            st.session_state["draft_affected_id"] = next(iter(choices), "")
        st.selectbox(label, list(choices) or [""],
                     format_func=lambda value: choices.get(value, "No eligible asset in validated input"),
                     key="draft_affected_id", disabled=event == "none" or not choices)
        st.slider("Supply / dispatch reduction", 0.0, 1.0, step=0.05, format="%.2f",
                  key="draft_reduction_fraction", disabled=event not in {"supply_reduction", "facility_outage"},
                  help="Fraction: 0 = no reduction; 1 = full interruption. Route closures set selected route capacity to zero.")
        if event in {"supply_reduction", "facility_outage"}:
            st.caption(f"{st.session_state['draft_reduction_fraction']:.0%} reduction during the impact window.")
        elif event == "route_closure":
            st.caption("The selected route's capacity is zero during the impact window.")
        st.number_input("Event delay (days)", min_value=0, max_value=14, step=1,
                        key="draft_delay_days", disabled=event != "route_delay")
        with st.expander("Timing & demand", expanded=True):
            st.number_input("Planning horizon (days)", min_value=1, max_value=14, step=1, key="draft_horizon_days")
            time_columns = st.columns(2)
            with time_columns[0]:
                st.number_input("Start day", min_value=1, max_value=14, step=1,
                                key="draft_start_day", disabled=event == "none")
            with time_columns[1]:
                st.number_input("Duration (days)", min_value=1, max_value=14, step=1,
                                key="draft_duration_days", disabled=event == "none")
            st.number_input("Demand multiplier", min_value=0.0, max_value=3.0, step=0.05,
                            key="draft_demand_multiplier", help="Applies to every district/group/day.")
        with st.expander("Lead times & risk threshold", expanded=False):
            st.number_input("Extra lead on all active routes (days)", min_value=0, max_value=7, step=1,
                            key="draft_extra_lead_days")
            st.number_input("Low-cover threshold (days)", min_value=0.01, max_value=14.0, step=0.25,
                            key="draft_cover_threshold")
            st.text_area("Scenario notes", max_chars=2000, key="draft_notes", height=100)
            st.caption("Route delay applies to dispatches within the event window; global extra lead applies throughout.")
        policy_options = ["regular", "stress"] + (["stored"] if "pinned_policy" in st.session_state else [])
        st.selectbox("Policy assumption", policy_options, format_func=POLICY_LABELS.get, key="draft_policy_choice")
        try:
            policy = selected_policy()
        except Exception as exc:
            policy = None
            input_error = error_text(exc)
        if policy is not None:
            with st.expander("Inspect draft tiers, floors & caps"):
                render_policy(policy, compact=True)
        run_clicked = st.button("Run simulation", type="primary", width="stretch")
        st.caption("Computes baseline and candidate plans locally. No credentials are needed for manual scenarios.")
        render_history()
    return draft_values(), network, policy, input_error, run_clicked


def applied_summary(bundle: RunBundle) -> str:
    scenario = bundle.scenario
    if scenario.event_type == "none":
        impact = "No disruption event"
    else:
        end = scenario.start_day + scenario.duration_days - 1
        impact = f"{scenario.event_type.replace('_', ' ')} · {scenario.affected_id} · days {scenario.start_day}–{end}"
        if scenario.event_type in {"supply_reduction", "facility_outage"}:
            impact += f" · {scenario.reduction_fraction:.1%} reduction"
        if scenario.event_type == "route_delay":
            impact += f" · +{scenario.delay_days} days on affected dispatches"
    return (f"Applied: {impact}. Demand ×{scenario.demand_multiplier:g}; "
            f"all-active-route lead +{scenario.extra_lead_days} days; "
            f"low cover < {scenario.cover_threshold:g} days.")


def main() -> None:
    load_dotenv(ROOT / ".env", override=False)
    st.set_page_config(page_title="CommonRoot · Supply planning desk", page_icon=":material/hub:", layout="wide",
                       initial_sidebar_state="expanded")
    st.html(Path(__file__).with_name("style.css"))
    initialize()
    values, network, policy, input_error, run_clicked = render_sidebar()
    scenario = None
    validation_error = input_error
    if validation_error is None:
        try:
            scenario = Scenario.model_validate(values, strict=True)
            apply_scenario(network, scenario, policy)
        except Exception as exc:
            validation_error = error_text(exc)
    if run_clicked:
        if validation_error:
            st.session_state["run_error"] = validation_error
        else:
            try:
                with st.spinner("Computing both plans against the same validated snapshot…"):
                    bundle = run_simulation(scenario, network=network, policy=policy,
                                            evidence=st.session_state.get("confirmed_evidence", []))
            except Exception as exc:
                st.session_state["run_error"] = error_text(exc)
            else:
                accept_bundle(bundle)
                save_bundle(bundle)
                st.session_state.pop("run_error", None)
                st.rerun()
    bundle = st.session_state.get("current_bundle")
    if bundle is None:
        st.title("Supply planning desk")
        st.error("No simulation result is available yet. Correct the input or service error, then select Run simulation.")
        if st.session_state.get("run_error"):
            st.error(st.session_state["run_error"])
        elif validation_error:
            st.error(validation_error)
        return
    st.html(report_header(bundle))
    st.caption(applied_summary(bundle))
    if validation_error:
        st.warning(
            f"Draft not applied — validation failed. Still displaying recorded run {bundle.manifest['run_id']}."
        )
        st.error(validation_error)
    else:
        changed = signature(scenario, network, policy) != signature(bundle.scenario, bundle.network, bundle.policy)
        if changed:
            st.warning(
                f"Draft not applied. Controls differ from displayed run {bundle.manifest['run_id']}. "
                "Select Run simulation to compute and display the new scenario."
            )
        else:
            st.caption("Scenario desk matches the displayed run. All report values come from this recorded snapshot.")
    if st.session_state.get("run_error") and st.session_state["run_error"] != validation_error:
        st.error(
            f"The last run attempt failed: {st.session_state['run_error']}. "
            f"Recorded run {bundle.manifest['run_id']} remains displayed."
        )
    if st.session_state.pop("review_notice", None) == bundle.manifest["run_id"]:
        st.success("Review recorded and saved. No operational action was taken.")
    receipt = st.session_state["store_receipts"].get(bundle.manifest["run_id"], {})
    if receipt.get("saved") is False:
        st.warning(f"This run is available in this session, but local saving failed: {receipt['error']}")
        if st.button("Retry saving displayed run"):
            save_bundle(bundle)
            st.rerun()
    render_tabs(bundle, accept_review)


if __name__ == "__main__":
    main()
