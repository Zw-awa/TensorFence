from __future__ import annotations

from pathlib import Path


def add_out_argument(parser, help_text: str = "output directory or file path") -> None:
    parser.add_argument("--out", type=Path, required=True, help=help_text)

