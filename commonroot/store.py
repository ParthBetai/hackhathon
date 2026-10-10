"""Atomic local run history. No database, accounts or operational connections."""

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID

from commonroot.contracts import ModelError
from commonroot.service import RunBundle, content_hash

DEFAULT_DIRECTORY = Path(__file__).resolve().parent.parent / "outputs" / "runs"
MAX_RUN_BYTES = 15_000_000


def _directory(directory: str | Path | None) -> Path:
    return Path(directory or os.environ.get("COMMONROOT_OUTPUT_DIR") or DEFAULT_DIRECTORY)


def _identifier(run_id: str) -> str:
    try:
        if str(UUID(run_id)) != run_id:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise ModelError("INPUT_VALIDATION", "Run ID must be a canonical UUID, not a path.") from None
    return run_id


def validate_integrity(bundle: RunBundle) -> None:
    inputs = {
        "network": bundle.network.model_dump(mode="json"),
        "scenario": bundle.scenario.model_dump(mode="json"),
        "policy": bundle.policy.model_dump(mode="json"),
        "adjusted": bundle.adjusted_inputs,
    }
    outputs = {"baseline": bundle.baseline.model_dump(mode="json"), "candidate": bundle.candidate.model_dump(mode="json")}
    if bundle.manifest.get("input_hash") != content_hash(inputs) or bundle.manifest.get("output_hash") != content_hash(outputs):
        raise ModelError("RUN_INTEGRITY", "Run inputs or outputs do not match their recorded hashes.")


def save_run(bundle: RunBundle, directory: str | Path | None = None) -> Path:
    run_id = _identifier(bundle.manifest["run_id"])
    validate_integrity(bundle)
    payload = bundle.model_dump_json(indent=2).encode("utf-8")
    if len(payload) > MAX_RUN_BYTES:
        raise ModelError("EXPORT_ERROR", "Run exceeds the 15 MB local history limit.")
    folder = _directory(directory)
    temporary = None
    try:
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{run_id}.json"
        if target.exists():
            previous = load_run(run_id, folder)
            if previous.manifest["input_hash"] != bundle.manifest["input_hash"] or previous.manifest["output_hash"] != bundle.manifest["output_hash"]:
                raise ModelError("RUN_INTEGRITY", "A run ID cannot be reused for different computation results.")
        with NamedTemporaryFile(dir=folder, prefix=f".{run_id}-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        return target
    except OSError as exc:
        raise ModelError("EXPORT_ERROR", f"Cannot save run to {folder}: {exc.strerror}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_run(run_id: str, directory: str | Path | None = None) -> RunBundle:
    path = _directory(directory) / f"{_identifier(run_id)}.json"
    try:
        if path.stat().st_size > MAX_RUN_BYTES:
            raise ModelError("RUN_INTEGRITY", "Stored run exceeds the size limit.")
        bundle = RunBundle.model_validate_json(path.read_bytes())
        if bundle.manifest.get("run_id") != run_id:
            raise ModelError("RUN_INTEGRITY", "Stored run ID does not match its filename.")
        validate_integrity(bundle)
        return bundle
    except (OSError, ValueError) as exc:
        if isinstance(exc, ModelError):
            raise
        raise ModelError("RUN_READ_ERROR", f"Cannot read checked run {run_id}: {type(exc).__name__}") from exc


def list_runs(directory: str | Path | None = None) -> list[dict]:
    folder = _directory(directory)
    if not folder.exists():
        return []
    records = []
    for path in folder.glob("*.json"):
        try:
            bundle = load_run(path.stem, folder)
        except ModelError:
            continue  # Corrupt or unrelated files never become valid history rows.
        records.append({**bundle.manifest, "scenario_name": bundle.scenario.name, "review_status": bundle.review.status})
    return sorted(records, key=lambda row: row["created_at"], reverse=True)
