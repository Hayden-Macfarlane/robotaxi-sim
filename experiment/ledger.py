"""Persist experiment checkpoints to disk."""

from __future__ import annotations

import json
from pathlib import Path

from core_data.models import ExperimentRun

MAX_RUNS = 50
DEFAULT_DIR = Path(".local/experiments")


class ExperimentLedger:
    """Append-only store of experiment run checkpoints."""

    def __init__(self, directory: Path | None = None) -> None:
        self._dir = directory or DEFAULT_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._file = self._dir / "runs.json"

    def list_runs(self) -> list[ExperimentRun]:
        """Return all saved runs, newest last."""
        if not self._file.exists():
            return []
        raw = json.loads(self._file.read_text(encoding="utf-8"))
        return [ExperimentRun.model_validate(row) for row in raw]

    def save_run(self, run: ExperimentRun) -> ExperimentRun:
        """Append a checkpoint and trim to ``MAX_RUNS``."""
        runs = self.list_runs()
        runs.append(run)
        if len(runs) > MAX_RUNS:
            runs = runs[-MAX_RUNS:]
        self._file.write_text(
            json.dumps([r.model_dump() for r in runs], indent=2),
            encoding="utf-8",
        )
        return run

    def delete_run(self, run_id: str) -> bool:
        """Remove a run by id."""
        runs = [r for r in self.list_runs() if r.id != run_id]
        if len(runs) == len(self.list_runs()):
            return False
        self._file.write_text(
            json.dumps([r.model_dump() for r in runs], indent=2),
            encoding="utf-8",
        )
        return True
