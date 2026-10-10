"""Reproducible offline model entry points, independent of Streamlit."""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from commonroot.contracts import ModelError
from commonroot.data import demo_scenarios, generate_network, load_network, load_policy
from commonroot.export import bundle_json, bundle_zip
from commonroot.schemas import Scenario
from commonroot.service import run_simulation
from commonroot.store import load_run, save_run


def main() -> int:
    load_dotenv(override=False)
    parser = argparse.ArgumentParser(description="CommonRoot synthetic LPG decision support")
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="Write a reproducible synthetic network JSON")
    generate.add_argument("--seed", type=int, default=42)
    generate.add_argument("--out", type=Path, default=Path("outputs/network.json"))
    run = commands.add_parser("run", help="Compute baseline + GLOP candidate and export one run")
    run.add_argument("--scenario", type=Path)
    run.add_argument("--preset", choices=list(demo_scenarios()), default="import_shock")
    run.add_argument("--network", type=Path)
    run.add_argument("--policy", type=Path)
    run.add_argument("--out", type=Path, default=Path("outputs/demo"))
    commands.add_parser("evaluate", help="Run all five synthetic regression fixtures")
    replay = commands.add_parser("replay", help="Recompute a saved run and compare output hashes")
    replay.add_argument("run_id")
    args = parser.parse_args()
    try:
        if args.command == "generate":
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(generate_network(args.seed).model_dump_json(indent=2), encoding="utf-8")
            print(f"Synthetic network written: {args.out}")
            return 0
        if args.command == "replay":
            original = load_run(args.run_id)
            repeated = run_simulation(original.scenario, original.network, original.policy, original.evidence)
            same = repeated.manifest["output_hash"] == original.manifest["output_hash"]
            print(json.dumps({"original_run_id": args.run_id, "same_output_hash": same, "new_status": repeated.manifest["status"]}, indent=2))
            return 0 if same else 1
        if args.command == "evaluate":
            rows = []
            for name, scenario in demo_scenarios().items():
                bundle = run_simulation(scenario)
                save_run(bundle)
                rows.append({"fixture": name, "status": bundle.manifest["status"], "input_hash": bundle.manifest["input_hash"], "baseline_unmet_kg": bundle.baseline.metrics.total_unmet if bundle.baseline.metrics else None, "candidate_unmet_kg": bundle.candidate.metrics.total_unmet if bundle.candidate.metrics else None, "seconds": bundle.manifest["elapsed_seconds"]})
            print(json.dumps(rows, indent=2))
            return 0 if all(row["status"] == "success" for row in rows) else 1
        scenario = Scenario.model_validate_json(args.scenario.read_bytes()) if args.scenario else demo_scenarios()[args.preset]
        bundle = run_simulation(scenario, load_network(args.network) if args.network else None, load_policy(args.policy))
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "run.json").write_text(bundle_json(bundle), encoding="utf-8")
        (args.out / "audit.zip").write_bytes(bundle_zip(bundle))
        saved = save_run(bundle)
        print(json.dumps({"run_id": bundle.manifest["run_id"], "status": bundle.manifest["status"], "elapsed_seconds": bundle.manifest["elapsed_seconds"], "baseline": bundle.baseline.status, "candidate": bundle.candidate.status, "comparison": bundle.comparison, "saved": str(saved), "export": str(args.out)}, indent=2))
        return 0 if bundle.manifest["status"] == "success" else 2
    except (ModelError, ValueError, OSError) as exc:
        print(json.dumps({"error": getattr(exc, "code", "INPUT_VALIDATION"), "message": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
