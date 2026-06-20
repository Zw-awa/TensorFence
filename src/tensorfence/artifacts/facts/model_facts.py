from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TensorFact:
    name: str
    dtype: str | None
    shape: list[int | str] | None


@dataclass(frozen=True)
class NodeFact:
    name: str
    op_type: str
    domain: str
    inputs: list[str]
    outputs: list[str]
    attribute_names: list[str]


@dataclass(frozen=True)
class ModelFacts:
    format: str
    model_path: str
    ir_version: int | None
    producer_name: str | None
    producer_version: str | None
    opsets: list[dict[str, Any]]
    inputs: list[TensorFact]
    outputs: list[TensorFact]
    value_info: list[TensorFact]
    initializers: list[TensorFact]
    nodes: list[NodeFact]
    operator_histogram: dict[str, int]
    warnings: list[str]


def model_facts_to_dict(model_facts: ModelFacts) -> dict[str, Any]:
    return asdict(model_facts)


def model_facts_from_dict(data: dict[str, Any]) -> ModelFacts:
    try:
        return ModelFacts(
            format=str(data["format"]),
            model_path=str(data["model_path"]),
            ir_version=int(data["ir_version"]) if data.get("ir_version") is not None else None,
            producer_name=data.get("producer_name"),
            producer_version=data.get("producer_version"),
            opsets=list(data.get("opsets", [])),
            inputs=[
                TensorFact(
                    name=str(item["name"]),
                    dtype=item.get("dtype"),
                    shape=list(item["shape"]) if item.get("shape") is not None else None,
                )
                for item in data.get("inputs", [])
            ],
            outputs=[
                TensorFact(
                    name=str(item["name"]),
                    dtype=item.get("dtype"),
                    shape=list(item["shape"]) if item.get("shape") is not None else None,
                )
                for item in data.get("outputs", [])
            ],
            value_info=[
                TensorFact(
                    name=str(item["name"]),
                    dtype=item.get("dtype"),
                    shape=list(item["shape"]) if item.get("shape") is not None else None,
                )
                for item in data.get("value_info", [])
            ],
            initializers=[
                TensorFact(
                    name=str(item["name"]),
                    dtype=item.get("dtype"),
                    shape=list(item["shape"]) if item.get("shape") is not None else None,
                )
                for item in data.get("initializers", [])
            ],
            nodes=[
                NodeFact(
                    name=str(item["name"]),
                    op_type=str(item["op_type"]),
                    domain=str(item.get("domain", "")),
                    inputs=list(item.get("inputs", [])),
                    outputs=list(item.get("outputs", [])),
                    attribute_names=list(item.get("attribute_names", [])),
                )
                for item in data.get("nodes", [])
            ],
            operator_histogram={str(key): int(value) for key, value in data.get("operator_histogram", {}).items()},
            warnings=[str(item) for item in data.get("warnings", [])],
        )
    except KeyError as exc:
        raise ValueError(f"model facts are missing required key: {exc.args[0]}") from exc
    except TypeError as exc:
        raise ValueError("model facts have an invalid structure") from exc


def load_model_facts_json(path: str | Path) -> ModelFacts:
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"model facts root must be an object: {source}")
    return model_facts_from_dict(data)


def write_model_facts_json(model_facts: ModelFacts, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(model_facts_to_dict(model_facts), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return target


def write_ops_summary_json(model_facts: ModelFacts, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "format": model_facts.format,
        "model_path": model_facts.model_path,
        "node_count": len(model_facts.nodes),
        "input_count": len(model_facts.inputs),
        "output_count": len(model_facts.outputs),
        "initializer_count": len(model_facts.initializers),
        "operator_histogram": model_facts.operator_histogram,
    }
    target.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def write_graph_summary_markdown(model_facts: ModelFacts, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Graph Summary: {Path(model_facts.model_path).name}",
        "",
        f"- Format: `{model_facts.format}`",
        f"- IR version: `{model_facts.ir_version}`",
        f"- Producer: `{model_facts.producer_name}` `{model_facts.producer_version}`",
        f"- Inputs: `{len(model_facts.inputs)}`",
        f"- Outputs: `{len(model_facts.outputs)}`",
        f"- Nodes: `{len(model_facts.nodes)}`",
        f"- Initializers: `{len(model_facts.initializers)}`",
        "",
        "## Operator Histogram",
        "",
    ]
    for op_type, count in sorted(model_facts.operator_histogram.items()):
        lines.append(f"- `{op_type}`: {count}")

    if model_facts.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in model_facts.warnings:
            lines.append(f"- {warning}")

    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target
