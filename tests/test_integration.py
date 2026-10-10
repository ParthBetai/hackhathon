import json
from io import BytesIO
from zipfile import ZipFile

import pytest

from commonroot.contracts import ModelError
from commonroot.data import DEMO_DIR, demo_scenarios, generate_network, load_policy
from commonroot.export import bundle_json, bundle_zip
from commonroot.service import record_review, run_simulation
from commonroot.store import list_runs, load_run, save_run


@pytest.fixture(scope="module")
def default_bundle():
    return run_simulation(demo_scenarios()["import_shock"])


def test_cli_run_and_replay(tmp_path, monkeypatch, capsys):
    from commonroot.cli import main

    monkeypatch.setenv("COMMONROOT_OUTPUT_DIR", str(tmp_path / "history"))
    monkeypatch.setattr("sys.argv", ["commonroot", "run", "--out", str(tmp_path / "demo")])
    assert main() == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["status"] == "success"
    monkeypatch.setattr("sys.argv", ["commonroot", "replay", receipt["run_id"]])
    assert main() == 0
    assert json.loads(capsys.readouterr().out)["same_output_hash"] is True
    exported = json.loads((tmp_path / "demo" / "run.json").read_text(encoding="utf-8"))
    assert exported["manifest"]["run_id"] == receipt["run_id"]


def test_repeat_changes_identity_not_numeric_results(default_bundle):
    repeated = run_simulation(default_bundle.scenario)
    assert repeated.manifest["run_id"] != default_bundle.manifest["run_id"]
    assert repeated.manifest["input_hash"] == default_bundle.manifest["input_hash"]
    assert repeated.manifest["output_hash"] == default_bundle.manifest["output_hash"]


@pytest.mark.parametrize("preset", ["normal", "route_closure", "route_delay", "facility_outage"])
def test_different_events_produce_different_checked_outputs(preset, default_bundle):
    run = run_simulation(demo_scenarios()[preset])
    assert run.manifest["status"] == "success"
    assert run.candidate.metrics.total_unmet != pytest.approx(default_bundle.candidate.metrics.total_unmet)
    assert run.candidate.checks.passed and run.baseline.checks.passed


@pytest.mark.parametrize("change", [{"demand_multiplier": 1.3}, {"extra_lead_days": 1}, {"reduction_fraction": 0.8}])
def test_input_changes_flow_results(default_bundle, change):
    scenario = default_bundle.scenario.model_copy(update=change)
    run = run_simulation(scenario)
    assert run.manifest["status"] == "success"
    assert run.candidate.metrics.total_unmet != pytest.approx(default_bundle.candidate.metrics.total_unmet)


def test_no_credentials_and_no_network(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    def forbidden(*args, **kwargs):
        raise AssertionError("Deterministic run tried a network request")
    monkeypatch.setattr("requests.post", forbidden)
    run = run_simulation(demo_scenarios()["import_shock"])
    assert run.manifest["status"] == "success"
    assert run.evidence == []


def test_atomic_history_review_and_hashes(tmp_path, default_bundle):
    path = save_run(default_bundle, tmp_path)
    loaded = load_run(default_bundle.manifest["run_id"], tmp_path)
    assert loaded == default_bundle
    reviewed = record_review(loaded, "Synthetic plan inspected; no dispatch.", True)
    assert reviewed.manifest == loaded.manifest
    assert loaded.review.status == "not_reviewed"
    save_run(reviewed, tmp_path)
    assert load_run(reviewed.manifest["run_id"], tmp_path).review.status == "reviewed_simulation_only"
    assert list_runs(tmp_path)[0]["review_status"] == "reviewed_simulation_only"
    assert path.exists() and not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("identifier", ["../../secrets", "anything", "", "../run.json"])
def test_history_path_traversal_rejected(tmp_path, identifier):
    with pytest.raises(ModelError, match="UUID"):
        load_run(identifier, tmp_path)


def test_tampered_run_rejected(tmp_path, default_bundle):
    path = save_run(default_bundle, tmp_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["scenario"]["reduction_fraction"] = 0.8
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ModelError, match="hashes"):
        load_run(default_bundle.manifest["run_id"], tmp_path)
    assert list_runs(tmp_path) == []


def test_review_blocked_without_ack_or_feasibility(default_bundle):
    with pytest.raises(ModelError, match="Acknowledge"):
        record_review(default_bundle, "", False)
    failed = run_simulation(default_bundle.scenario, policy=load_policy(DEMO_DIR / "policy_infeasible.json"))
    assert failed.candidate.status == "SOLVER_INFEASIBLE"
    assert failed.candidate.metrics is None
    with pytest.raises(ModelError, match="Failed"):
        record_review(failed, "", True)


def test_export_is_current_run_not_latest_fixture(default_bundle):
    reviewed = record_review(default_bundle, "Reviewed for demonstration.", True)
    raw = json.loads(bundle_json(reviewed))
    with ZipFile(BytesIO(bundle_zip(reviewed))) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        exported = json.loads(archive.read("run.json"))
    assert manifest["run_id"] == reviewed.manifest["run_id"]
    assert raw == exported == reviewed.model_dump(mode="json")


def test_missing_stock_is_not_zero():
    network = generate_network()
    network.nodes[-1].initial_stock = None
    with pytest.raises(ModelError, match="unknown is not zero"):
        run_simulation(demo_scenarios()["import_shock"], network)
