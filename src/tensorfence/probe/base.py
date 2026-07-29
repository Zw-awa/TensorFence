from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class ProbeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProbeArtifacts:
    model_facts_json: Path
    ops_summary_json: Path
    graph_summary_md: Path | None
    warnings: list[str]
