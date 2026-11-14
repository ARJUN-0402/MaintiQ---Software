"""Local JSON-based model registry for trained artefacts.

The registry persists per-model version records to a single JSON file under the
configured model directory. All artefact paths are constrained to that directory,
and SHA-256 checksums are recorded and verified before an artefact is loaded.

Local model artefacts are treated as trusted application data only. Joblib/pickle
loading never happens from an untrusted source.

Concurrency: a threading lock serialises same-process writes. Cross-process
locking is not implemented and is not claimed.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import threading
from typing import Any

import joblib
import numpy as np
import pandas as pd

from maintiq.core.exceptions import (
    ModelError,
    ModelHashMismatchError,
    RegistryError,
)

SCHEMA_VERSION = "1.0"
REGISTRY_FILENAME = "registry.json"

REQUIRED_VERSION_FIELDS = (
    "record_id",
    "version",
    "artifact_path",
    "created_at",
    "sha256",
    "metrics",
    "parameters",
)

PRIMITIVE_TYPES = (str, int, float, bool, type(None))


def _is_json_primitive(value: Any) -> bool:
    return isinstance(value, PRIMITIVE_TYPES)


def json_safe(value: Any) -> Any:
    """Convert ``value`` to a JSON-safe primitive or raise ``RegistryError``.

    Supported conversions: numpy scalars, bytes/Path/Enum/Timestamp, dicts,
    lists/tuples/sets, and dataclasses exposing ``to_dict``. Arbitrary model
    objects, functions, classes and modules are rejected rather than silently
    stringified.
    """
    if _is_json_primitive(value):
        return value
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, np.ndarray):
        return [json_safe(v) for v in value.tolist()]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            return json_safe(value.to_dict())
        except Exception as exc:
            raise RegistryError(f"Cannot serialise {type(value).__name__} to JSON: {exc}") from exc
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [json_safe(v) for v in value]

    raise RegistryError(
        f"Unsupported JSON value of type {type(value).__name__}; cannot safely "
        f"serialise arbitrary model object."
    )


def compute_sha256(path: str | Path) -> str:
    """Return the SHA-256 hex digest of the file at ``path``."""
    digest = sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_under_root(model_dir: Path, artifact_path: str | Path) -> tuple[Path, Path]:
    """Resolve ``artifact_path`` and constrain it to ``model_dir``.

    Returns ``(resolved_absolute_path, path_relative_to_model_dir)``.
    Raises ``RegistryError`` for traversal, outside-directory, or symlink escapes.
    """
    root = model_dir.resolve()
    candidate = Path(artifact_path)

    if candidate.is_absolute():
        resolved = candidate.resolve()
    else:
        resolved = (root / candidate).resolve()

    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RegistryError(
            f"Artefact path escapes model directory '{root}': {artifact_path}"
        ) from exc

    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:  # pragma: no cover - guarded above
        raise RegistryError(str(exc)) from exc

    return resolved, relative


class ModelRegistry:
    """JSON-backed model registry with per-model monotonic versioning.

    Parameters
    ----------
    registry_path:
        Path to the JSON registry file. A missing file creates empty state.
    model_dir:
        Directory that constrains all artefact paths. Defaults to the registry
        file's parent.
    """

    def __init__(self, registry_path: str | Path, model_dir: str | Path | None = None) -> None:
        self.registry_path = Path(registry_path)
        self.model_dir = Path(model_dir) if model_dir is not None else self.registry_path.parent
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "models": {},
        }
        self._loaded = False
        self.reload()

    # ------------------------------------------------------------------ load/save

    def reload(self) -> None:
        """Load the registry from disk, replacing in-memory state.

        Raises ``RegistryError`` on malformed JSON, unsupported schema versions,
        or invalid record shapes.
        """
        with self._lock:
            self._data = {
                "schema_version": SCHEMA_VERSION,
                "models": {},
            }
            if not self.registry_path.exists():
                self._loaded = True
                return
            try:
                with open(self.registry_path, encoding="utf-8") as handle:
                    raw = json.load(handle)
            except (OSError, json.JSONDecodeError) as exc:
                raise RegistryError(
                    f"Malformed registry JSON at {self.registry_path}: {exc}"
                ) from exc
            self._validate_shape(raw)
            self._data = raw
            self._loaded = True

    def _persist(self) -> None:
        """Atomically write in-memory state to disk via a sibling temp file."""
        tmp_path = self.registry_path.with_name(self.registry_path.name + ".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(self._data, handle, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(tmp_path, self.registry_path)
        except BaseException:
            try:
                tmp_path.unlink(missing_ok=True)  # type: ignore[attr-defined]
            except OSError:  # pragma: no cover - best effort cleanup
                pass
            raise

    def _validate_shape(self, raw: Any) -> None:
        if not isinstance(raw, dict):
            raise RegistryError("Registry root must be a JSON object.")
        if raw.get("schema_version") != SCHEMA_VERSION:
            raise RegistryError(
                f"Unsupported schema version: {raw.get('schema_version')!r}; "
                f"expected {SCHEMA_VERSION!r}."
            )
        models = raw.get("models")
        if not isinstance(models, dict):
            raise RegistryError("Registry 'models' must be an object.")
        for model_name, model_entry in models.items():
            if not isinstance(model_entry, dict):
                raise RegistryError(f"Model record for {model_name!r} must be an object.")
            if "versions" not in model_entry:
                raise RegistryError(f"Model record for {model_name!r} is missing 'versions'.")
            versions = model_entry["versions"]
            if not isinstance(versions, list):
                raise RegistryError(f"Model 'versions' for {model_name!r} must be a list.")
            for version_record in versions:
                if not isinstance(version_record, dict):
                    raise RegistryError(f"Version record in {model_name!r} must be an object.")
                missing = [
                    field for field in REQUIRED_VERSION_FIELDS if field not in version_record
                ]
                if missing:
                    raise RegistryError(
                        f"Version record in {model_name!r} missing fields: {missing}."
                    )

    # ------------------------------------------------------------------ helpers

    def _normalize_metadata(
        self,
        *,
        model_name: str,
        display_name: str | None,
        artifact_path: str | Path,
        metrics: Any,
        parameters: Any,
        split_settings: Any,
        dataset_fingerprint: str | None,
        feature_columns: list[str] | None,
        target_column: str | None,
        library_versions: dict[str, str] | None,
        threshold: float | None,
        random_seed: int | None,
        record_id: str | None,
    ) -> dict[str, Any]:
        try:
            _resolved, relative = _resolve_under_root(self.model_dir, artifact_path)
        except RegistryError:
            raise
        except Exception as exc:
            raise RegistryError(f"Cannot resolve artefact path {artifact_path!r}: {exc}") from exc

        metrics_dict: Any = metrics
        if metrics_dict is not None and not isinstance(metrics_dict, dict):
            if hasattr(metrics_dict, "to_dict") and callable(metrics_dict.to_dict):
                metrics_dict = metrics_dict.to_dict()  # type: ignore[assignment]
            else:
                metrics_dict = asdict(metrics_dict)  # type: ignore[arg-type]

        split_dict: Any = split_settings
        if split_dict is not None and not isinstance(split_dict, dict):
            if hasattr(split_dict, "to_dict") and callable(split_dict.to_dict):
                split_dict = split_dict.to_dict()  # type: ignore[assignment]
            else:
                split_dict = asdict(split_dict)  # type: ignore[arg-type]

        return {
            "record_id": record_id or f"{model_name}-v{self._next_version(model_name) + 1}",
            "artifact_path": str(relative),
            "created_at": _utc_now_iso(),
            "sha256": compute_sha256(_resolved),
            "metrics": json_safe(metrics_dict) if metrics_dict is not None else None,
            "parameters": json_safe(parameters) if parameters is not None else None,
            "split_settings": json_safe(split_dict) if split_dict is not None else None,
            "dataset_fingerprint": dataset_fingerprint,
            "feature_columns": json_safe(feature_columns) if feature_columns is not None else None,
            "target_column": target_column,
            "library_versions": json_safe(library_versions)
            if library_versions is not None
            else None,
            "threshold": float(threshold) if threshold is not None else None,
            "random_seed": int(random_seed) if random_seed is not None else None,
        }

    def _next_version(self, model_name: str) -> int:
        models = self._data["models"]
        if model_name not in models:
            return 0
        versions = models[model_name].get("versions", [])
        if not versions:
            return 0
        max_version = 0
        for record in versions:
            version_label = str(record.get("version", "v0"))
            if version_label.startswith("v"):
                try:
                    number = int(version_label[1:])
                except ValueError:
                    continue
            else:
                try:
                    number = int(version_label)
                except ValueError:
                    continue
            if number > max_version:
                max_version = number
        return max_version

    def _find_version(self, model_name: str, version: str) -> dict[str, Any] | None:
        models = self._data["models"]
        if model_name not in models:
            return None
        for record in models[model_name].get("versions", []):
            if str(record.get("version")) == version:
                return record
        return None

    # ------------------------------------------------------------------ public API

    def register(
        self,
        *,
        model_name: str,
        artifact_path: str | Path,
        metrics: Any = None,
        parameters: Any = None,
        split_settings: Any = None,
        dataset_fingerprint: str | None = None,
        feature_columns: list[str] | None = None,
        target_column: str | None = None,
        library_versions: dict[str, str] | None = None,
        threshold: float | None = None,
        random_seed: int | None = None,
        display_name: str | None = None,
        record_id: str | None = None,
    ) -> str:
        """Register a trained artefact and return its version label (e.g. ``v1``).

        The artefact must already exist on disk; otherwise ``RegistryError`` is
        raised before any mutation occurs.
        """
        resolved = Path(artifact_path)
        if not resolved.is_absolute():
            resolved = self.model_dir / resolved
        if not resolved.exists() or not resolved.is_file():
            raise RegistryError(f"Cannot register missing artefact: {resolved}")

        metadata = self._normalize_metadata(
            model_name=model_name,
            display_name=display_name,
            artifact_path=resolved,
            metrics=metrics,
            parameters=parameters,
            split_settings=split_settings,
            dataset_fingerprint=dataset_fingerprint,
            feature_columns=feature_columns,
            target_column=target_column,
            library_versions=library_versions,
            threshold=threshold,
            random_seed=random_seed,
            record_id=record_id,
        )

        next_number = self._next_version(model_name) + 1
        version_label = f"v{next_number}"
        metadata["version"] = version_label
        metadata["record_id"] = f"{model_name}-{version_label}"
        metadata["model_name"] = model_name

        with self._lock:
            models = self._data["models"]
            if model_name not in models:
                models[model_name] = {
                    "display_name": display_name,
                    "versions": [],
                }
            models[model_name]["versions"].append(metadata)
            if display_name is not None:
                models[model_name]["display_name"] = display_name
            self._persist()

        return version_label

    def list_models(self) -> list[str]:
        """Return defensive copy of registered model names."""
        with self._lock:
            return sorted(self._data["models"].keys())

    def list_versions(self, model_name: str) -> list[str]:
        """Return defensive copy of version labels for ``model_name``."""
        with self._lock:
            model_entry = self._data["models"].get(model_name)
            if not model_entry:
                return []
            return [str(record["version"]) for record in model_entry["versions"]]

    def model_exists(self, model_name: str) -> bool:
        with self._lock:
            return model_name in self._data["models"]

    def version_exists(self, model_name: str, version: str) -> bool:
        with self._lock:
            return self._find_version(model_name, version) is not None

    def count_models(self) -> int:
        with self._lock:
            return len(self._data["models"])

    def count_records(self) -> int:
        """Total number of version records across all models."""
        with self._lock:
            return sum(
                len(model_entry.get("versions", []))
                for model_entry in self._data["models"].values()
            )

    def get_version(self, model_name: str, version: str) -> dict[str, Any]:
        """Return a defensive copy of a single version record."""
        with self._lock:
            record = self._find_version(model_name, version)
            if record is None:
                raise RegistryError(f"Model {model_name!r} version {version!r} not found.")
            return json.loads(json.dumps(record))

    def get_latest(self, model_name: str) -> dict[str, Any]:
        """Return a defensive copy of the latest version record for a model."""
        with self._lock:
            model_entry = self._data["models"].get(model_name)
            if not model_entry or not model_entry.get("versions"):
                raise RegistryError(f"No versions registered for model {model_name!r}.")
            versions = model_entry["versions"]
            latest = versions[-1]
            return json.loads(json.dumps(latest))

    def delete_version(self, model_name: str, version: str) -> None:
        """Remove a single version record for ``model_name``.

        Raises ``RegistryError`` if the model or version does not exist. The
        artefact file on disk is left intact (callers may remove it separately).
        """
        with self._lock:
            record = self._find_version(model_name, version)
            if record is None:
                raise RegistryError(f"Model {model_name!r} version {version!r} not found.")
            model_entry = self._data["models"].get(model_name)
            if not model_entry:
                raise RegistryError(f"Model {model_name!r} not found.")
            model_entry["versions"] = [
                r for r in model_entry.get("versions", []) if str(r.get("version")) != version
            ]
            if not model_entry.get("versions"):
                self._data["models"].pop(model_name, None)
            self._persist()

    def delete_model(self, model_name: str) -> int:
        """Remove all version records for ``model_name``.

        Returns the number of version records removed. Raises ``RegistryError``
        if the model does not exist. Artefact files on disk are left intact.
        """
        with self._lock:
            if model_name not in self._data["models"]:
                raise RegistryError(f"Model {model_name!r} not found.")
            removed = len(self._data["models"][model_name].get("versions", []))
            del self._data["models"][model_name]
            self._persist()
            return removed

    def get_artifact_path(self, model_name: str, version: str) -> Path:
        """Resolve and return the absolute artefact path for a version."""
        record = self.get_version(model_name, version)
        return (self.model_dir / record["artifact_path"]).resolve()

    def load_artifact(self, model_name: str, version: str, *, trusted: bool = True) -> Any:
        """Load a joblib artefact after verifying its SHA-256 checksum.

        ``trusted`` documents that local model artefacts are trusted application
        data only; unpickling is never performed for untrusted sources.
        """
        if not trusted:
            raise RegistryError("Loading untrusted joblib artefacts is not permitted.")

        record = self.get_version(model_name, version)
        artifact_path = self.get_artifact_path(model_name, version)
        if not artifact_path.exists() or not artifact_path.is_file():
            raise ModelError(f"Artefact not found on disk: {artifact_path}")
        actual_hash = compute_sha256(artifact_path)
        expected_hash = record.get("sha256")
        if expected_hash is None or actual_hash != expected_hash:
            raise ModelHashMismatchError(
                f"SHA-256 mismatch for {model_name!r} version {version!r}: "
                f"expected {expected_hash}, got {actual_hash}."
            )
        return joblib.load(str(artifact_path))

    def clear(self, model_name: str | None = None) -> None:
        """Clear all records, or only those for ``model_name``."""
        with self._lock:
            if model_name is None:
                self._data["models"] = {}
            else:
                self._data["models"].pop(model_name, None)
            self._persist()
