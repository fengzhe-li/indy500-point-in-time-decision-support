"""Read-only adapter for the active project's frozen R3C1 performance core."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


@dataclass(frozen=True)
class FrozenAsset:
    asset: str
    path: str
    sha256: str
    role: str
    phase: str


class R3C1ReadOnlyAdapter:
    """Verify and read only assets listed by the R3C1 freeze manifest."""

    DEFAULT_MANIFEST = "weather/output/final_results_freeze_manifest_v1.csv"

    def __init__(self, project_root: str | Path, manifest_path: str | Path | None = None):
        self.project_root = Path(project_root).resolve()
        requested = Path(manifest_path or self.DEFAULT_MANIFEST)
        self.manifest_path = requested if requested.is_absolute() else self.project_root / requested
        self._assets = self._read_manifest()

    def _read_manifest(self) -> dict[str, FrozenAsset]:
        with self.manifest_path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        return {row["asset"]: FrozenAsset(**row) for row in rows}

    def assets(self) -> tuple[FrozenAsset, ...]:
        return tuple(self._assets[name] for name in sorted(self._assets))

    def _resolve(self, asset_name: str) -> Path:
        try:
            asset = self._assets[asset_name]
        except KeyError as exc:
            raise KeyError(f"{asset_name!r} is not listed in the R3C1 freeze manifest") from exc
        path = (self.project_root / asset.path).resolve()
        if path != self.project_root and self.project_root not in path.parents:
            raise ValueError(f"R3C1 asset escapes project root: {asset.path}")
        return path

    def verify(self) -> dict[str, bool]:
        return {
            asset.asset: self._resolve(asset.asset).is_file() and _sha256(self._resolve(asset.asset)) == asset.sha256
            for asset in self.assets()
        }

    def assert_verified(self) -> None:
        failed = [name for name, valid in self.verify().items() if not valid]
        if failed:
            raise RuntimeError("R3C1 read-only input hash verification failed: " + ", ".join(failed))

    def read_csv(self, asset_name: str) -> tuple[dict[str, str], ...]:
        path = self._resolve(asset_name)
        if path.suffix.lower() != ".csv":
            raise ValueError(f"{asset_name} is not a CSV asset")
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return tuple(dict(row) for row in csv.DictReader(f))

    def read_json(self, asset_name: str) -> Any:
        path = self._resolve(asset_name)
        if path.suffix.lower() != ".json":
            raise ValueError(f"{asset_name} is not a JSON asset")
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
