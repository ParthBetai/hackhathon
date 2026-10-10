from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from commonroot.export import bundle_json
from commonroot.store import load_run

APP = Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py"


@pytest.fixture
def desk(tmp_path, monkeypatch):
    monkeypatch.setenv("COMMONROOT_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GEMINI_MODEL", "")
    at = AppTest.from_file(str(APP), default_timeout=20).run()
    assert not at.exception
    return at


def button(desk, label):
    return next(item for item in desk.button if item.label == label)


def test_default_has_computed_metrics_exports_and_persisted_history(desk):
    run = desk.session_state["current_bundle"]
    assert run.manifest["status"] == "success"
    assert [tab.label for tab in desk.tabs] == ["Overview", "District risk", "Compare plans", "Network & inputs", "Review & export", "Source review"]
    assert run.candidate.metrics.total_served > 0
    assert load_run(run.manifest["run_id"]) == run
    assert len(desk.dataframe) > 10
    assert any("Gemini is not configured" in item.value for item in desk.info)


def test_draft_is_not_applied_until_run(desk):
    original = desk.session_state["current_bundle"]
    desk.number_input(key="draft_demand_multiplier").set_value(1.3).run()
    assert not desk.exception
    assert desk.session_state["current_bundle"].manifest["run_id"] == original.manifest["run_id"]
    assert any("Draft not applied" in item.value for item in desk.warning)
    button(desk, "Run simulation").click().run()
    result = desk.session_state["current_bundle"]
    assert result.manifest["run_id"] != original.manifest["run_id"]
    assert result.candidate.metrics.total_unmet > original.candidate.metrics.total_unmet
    assert result.scenario.demand_multiplier == 1.3
    assert not desk.exception


def test_invalid_input_preserves_recorded_run(desk):
    run_id = desk.session_state["current_bundle"].manifest["run_id"]
    desk.number_input(key="draft_horizon_days").set_value(3).run()
    button(desk, "Run simulation").click().run()
    assert desk.session_state["current_bundle"].manifest["run_id"] == run_id
    assert any("Impact window" in item.value for item in desk.error)
    assert not desk.exception


def test_failed_plan_no_review_or_fabricated_risk(desk):
    desk.selectbox(key="draft_policy_choice").select("stress").run()
    button(desk, "Run simulation").click().run()
    run = desk.session_state["current_bundle"]
    assert run.candidate.status == "SOLVER_INFEASIBLE"
    assert run.candidate.metrics is None and run.candidate.districts == []
    assert button(desk, "Record review").disabled
    assert not desk.exception


def test_review_and_exact_history_reopen(desk):
    original = desk.session_state["current_bundle"]
    run_id = original.manifest["run_id"]
    desk.text_area(key=f"review_note_{run_id}").set_value("Synthetic case checked.").run()
    desk.checkbox(key=f"review_ack_{run_id}").check().run()
    button(desk, "Record review").click().run()
    assert load_run(run_id).review.status == "reviewed_simulation_only"
    reviewed_json = bundle_json(desk.session_state["current_bundle"])
    desk.selectbox(key="draft_preset").select("normal").run()
    button(desk, "Run simulation").click().run()
    assert desk.session_state["current_bundle"].manifest["run_id"] != run_id
    desk.selectbox(key="history_selected").select(run_id).run()
    button(desk, "Reopen selected run").click().run()
    assert bundle_json(desk.session_state["current_bundle"]) == reviewed_json
    assert not desk.exception


def test_district_search_empty_and_selected_inputs(desk):
    desk.text_input(key="district_search").input("no such district").run()
    assert any("No districts match" in item.value for item in desk.info)
    desk.text_input(key="district_search").input("North").run()
    assert any(item.value == "North Hills" for item in desk.subheader)
    assert not desk.exception


def test_route_and_facility_presets_recompute(desk):
    original = desk.session_state["current_bundle"]
    for preset in ("route_closure", "route_delay", "facility_outage"):
        desk.selectbox(key="draft_preset").select(preset).run()
        button(desk, "Run simulation").click().run()
        run = desk.session_state["current_bundle"]
        assert run.manifest["status"] == "success"
        assert run.manifest["input_hash"] != original.manifest["input_hash"]
        assert not desk.exception


def test_zero_demand_does_not_invent_cover(desk):
    desk.number_input(key="draft_demand_multiplier").set_value(0.0).run()
    button(desk, "Run simulation").click().run()
    run = desk.session_state["current_bundle"]
    assert run.candidate.metrics.total_demand == 0
    assert all(row.risk == "Not computable" for row in run.candidate.districts)
    assert not desk.exception
