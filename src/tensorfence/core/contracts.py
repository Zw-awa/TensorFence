from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class ContractError(RuntimeError):
    pass


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResizeSpec(StrictBaseModel):
    mode: Literal["stretch", "letterbox", "keep_ratio"] = "letterbox"
    target_size: list[int] = Field(min_length=2, max_length=2)
    interpolation: Literal["nearest", "bilinear", "area", "bicubic"] = "bilinear"
    keep_aspect_ratio: bool = True

    @model_validator(mode="after")
    def _validate_target_size(self) -> "ResizeSpec":
        if any(size <= 0 for size in self.target_size):
            raise ValueError("resize.target_size values must be positive")
        return self


class NormalizeSpec(StrictBaseModel):
    scale: float | list[float] = 1.0
    mean: list[float] = Field(default_factory=list)
    std: list[float] = Field(default_factory=list)


class PreprocessSpec(StrictBaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    input_color_space: Literal["RGB", "BGR", "GRAY"]
    input_layout: Literal["HWC", "CHW", "NCHW", "NHWC", "HW", "N/A"]
    output_color_space: Literal["RGB", "BGR", "GRAY"] | None = None
    output_layout: Literal["NCHW", "NHWC", "NC", "N/A"] = Field(alias="layout")
    resize: ResizeSpec
    normalize: NormalizeSpec | None = None
    pad_value: int | list[int] = 0


class TensorSpec(StrictBaseModel):
    name: str
    shape: list[int] = Field(min_length=1)
    dtype: str = "float32"
    layout: Literal["NCHW", "NHWC", "NC", "N/A"] | None = None
    semantic: str
    description: str | None = None

    @model_validator(mode="after")
    def _validate_layout_shape(self) -> "TensorSpec":
        if self.layout == "NCHW" and len(self.shape) != 4:
            raise ValueError(f"tensor {self.name} uses NCHW but shape rank is not 4")
        if self.layout == "NHWC" and len(self.shape) != 4:
            raise ValueError(f"tensor {self.name} uses NHWC but shape rank is not 4")
        if self.layout == "NC" and len(self.shape) != 2:
            raise ValueError(f"tensor {self.name} uses NC but shape rank is not 2")
        return self


class DecodeSpec(StrictBaseModel):
    family: Literal["yolo", "ppyoloe", "generic"] = "yolo"
    mode: Literal["anchor_free", "anchor_based"] = "anchor_free"
    num_classes: int
    strides: list[int] = Field(default_factory=list)
    anchors: list[list[float]] | None = None
    head_names: list[str] = Field(default_factory=list)
    reg_max: int | None = None
    score_activation: Literal["sigmoid", "softmax", "none"] = "sigmoid"
    box_activation: Literal["sigmoid", "exp", "none"] = "sigmoid"


class NmsSpec(StrictBaseModel):
    score_threshold: float = 0.25
    iou_threshold: float = 0.45
    class_agnostic: bool = False
    max_detections: int = 300
    method: Literal["nms", "soft-nms"] = "nms"


class QuantizationSpec(StrictBaseModel):
    enabled: bool = False
    calibration_dataset: str | None = None
    calibration_samples: int | None = None
    match_preprocess: bool = True


class ModelContract(StrictBaseModel):
    name: str
    task: Literal["detection", "classification", "segmentation", "pose", "ocr", "custom"] = "detection"
    source_framework: str
    target_runtime: str = "rknn"
    input: TensorSpec
    outputs: list[TensorSpec] = Field(min_length=1)
    preprocess: PreprocessSpec
    decode: DecodeSpec | None = None
    nms: NmsSpec | None = None
    quantization: QuantizationSpec = Field(default_factory=QuantizationSpec)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _normalize_notes(self) -> "ModelContract":
        self.notes = [note.strip() for note in self.notes if note and note.strip()]
        return self


def load_contract(path: str | Path) -> ModelContract:
    source = Path(path)
    try:
        raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContractError(f"failed to read contract file: {source}") from exc
    except yaml.YAMLError as exc:
        raise ContractError(f"failed to parse YAML contract: {source}") from exc

    if raw is None:
        raise ContractError(f"contract file is empty: {source}")
    if not isinstance(raw, dict):
        raise ContractError(f"contract root must be a mapping: {source}")

    try:
        return ModelContract.model_validate(raw)
    except ValidationError as exc:
        raise ContractError(f"contract validation failed: {source}\n{exc}") from exc


def load_contract_from_text(text: str) -> ModelContract:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ContractError("failed to parse YAML contract text") from exc

    if raw is None:
        raise ContractError("contract text is empty")
    if not isinstance(raw, dict):
        raise ContractError("contract root must be a mapping")

    try:
        return ModelContract.model_validate(raw)
    except ValidationError as exc:
        raise ContractError(f"contract validation failed\n{exc}") from exc


def dump_contract(contract: ModelContract) -> str:
    return yaml.safe_dump(
        contract.model_dump(mode="python", exclude_none=True),
        sort_keys=False,
        allow_unicode=True,
    )


def write_contract(path: str | Path, contract: ModelContract) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(dump_contract(contract), encoding="utf-8")
    return target
