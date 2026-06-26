"""Save and load operator policy + routing presets."""

from __future__ import annotations

import json
import re
from pathlib import Path

from core_data.models import OperatorPreset

DEFAULT_DIR = Path(".local/presets")


def _safe_filename(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip().lower()).strip("-")
    return slug or "preset"


class PresetStore:
    """JSON file store for named operator presets."""

    def __init__(self, directory: Path | None = None) -> None:
        self._dir = directory or DEFAULT_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def list_presets(self) -> list[str]:
        """Return preset names (filename stems)."""
        return sorted(p.stem for p in self._dir.glob("*.json"))

    def save(self, preset: OperatorPreset) -> str:
        """Write preset to disk; returns filename stem."""
        stem = _safe_filename(preset.name)
        path = self._dir / f"{stem}.json"
        path.write_text(preset.model_dump_json(indent=2), encoding="utf-8")
        return stem

    def load(self, name: str) -> OperatorPreset:
        """Load preset by name or filename stem."""
        stem = _safe_filename(name)
        path = self._dir / f"{stem}.json"
        if not path.exists():
            raise FileNotFoundError(f"Preset '{name}' not found.")
        return OperatorPreset.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def delete(self, name: str) -> bool:
        """Delete a preset file."""
        stem = _safe_filename(name)
        path = self._dir / f"{stem}.json"
        if not path.exists():
            return False
        path.unlink()
        return True
