from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, ValidationError, model_validator

from ..core.contracts import NormalizeSpec, StrictBaseModel


class RuleError(RuntimeError):
    pass


class RuleDefaults(StrictBaseModel):
    name: str = "{model_name}-draft"
    source_framework: str = "onnx"
    target_runtime: str = "rknn"
    task: Literal["detection", "classification", "segmentation", "pose", "ocr", "custom"] = "detection"
    family: Literal["yolo", "ppyoloe", "generic"] = "generic"


class InputSelectionRule(StrictBaseModel):
    strategy: Literal["first", "by_name"] = "first"
    name: str | None = None

    @model_validator(mode="after")
    def _validate_by_name(self) -> "InputSelectionRule":
        if self.strategy == "by_name" and not self.name:
            raise ValueError("selection.input.name is required when strategy=by_name")
        return self


class OutputSelectionRule(StrictBaseModel):
    strategy: Literal["all", "by_name"] = "all"
    names: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_by_name(self) -> "OutputSelectionRule":
        if self.strategy == "by_name" and not self.names:
            raise ValueError("selection.outputs.names is required when strategy=by_name")
        return self


class SelectionRules(StrictBaseModel):
    input: InputSelectionRule = Field(default_factory=InputSelectionRule)
    outputs: OutputSelectionRule = Field(default_factory=OutputSelectionRule)


class InputLayoutRules(StrictBaseModel):
    rank4: Literal["NCHW", "NHWC"] = "NCHW"
    rank2: Literal["NC"] | None = None


class InputMappingRules(StrictBaseModel):
    semantic: str = "model_input"
    layout_from_rank: InputLayoutRules = Field(default_factory=InputLayoutRules)
    dtype_fallback: str = "float32"


class OutputMappingRules(StrictBaseModel):
    semantic: str = "raw_predictions"
    layout: Literal["NCHW", "NHWC", "NC", "N/A"] = "N/A"
    dtype_fallback: str = "float32"


class MappingRules(StrictBaseModel):
    input: InputMappingRules = Field(default_factory=InputMappingRules)
    outputs: OutputMappingRules = Field(default_factory=OutputMappingRules)


class ResizeTemplateSpec(StrictBaseModel):
    mode: Literal["stretch", "letterbox", "keep_ratio"] = "letterbox"
    target_size: list[int] | None = Field(default=None, min_length=2, max_length=2)
    interpolation: Literal["nearest", "bilinear", "area", "bicubic"] = "bilinear"
    keep_aspect_ratio: bool = True


class PreprocessTemplateSpec(StrictBaseModel):
    input_color_space: Literal["RGB", "BGR", "GRAY"] = "BGR"
    output_color_space: Literal["RGB", "BGR", "GRAY"] | None = "RGB"
    input_layout: Literal["HWC", "CHW", "NCHW", "NHWC", "HW", "N/A"] = "HWC"
    output_layout: Literal["NCHW", "NHWC", "NC", "N/A"] = "NCHW"
    resize: ResizeTemplateSpec = Field(default_factory=ResizeTemplateSpec)
    normalize: NormalizeSpec | None = Field(default_factory=NormalizeSpec)
    pad_value: int | list[int] = 114


class DecodeTemplateSpec(StrictBaseModel):
    enabled: bool = False
    family: Literal["yolo", "ppyoloe", "generic"] = "generic"
    mode: Literal["anchor_free", "anchor_based"] = "anchor_free"
    num_classes: int | None = None
    strides: list[int] = Field(default_factory=list)
    anchors: list[list[float]] | None = None
    head_names: list[str] = Field(default_factory=list)
    reg_max: int | None = None
    score_activation: Literal["sigmoid", "softmax", "none"] = "sigmoid"
    box_activation: Literal["sigmoid", "exp", "none"] = "sigmoid"

    @model_validator(mode="after")
    def _validate_enabled_template(self) -> "DecodeTemplateSpec":
        if not self.enabled:
            return self
        if self.num_classes is None or self.num_classes <= 0:
            raise ValueError("templates.decode.num_classes must be positive when decode is enabled")
        if not self.strides:
            raise ValueError("templates.decode.strides must be provided when decode is enabled")
        if self.mode == "anchor_based" and not self.anchors:
            raise ValueError("templates.decode.anchors must be provided for anchor-based decode")
        return self


class NmsTemplateSpec(StrictBaseModel):
    enabled: bool = False
    score_threshold: float = 0.25
    iou_threshold: float = 0.45
    class_agnostic: bool = False
    max_detections: int = 300
    method: Literal["nms", "soft-nms"] = "nms"


class QuantizationTemplateSpec(StrictBaseModel):
    enabled: bool = False
    calibration_dataset: str | None = None
    calibration_samples: int | None = None
    match_preprocess: bool = True

    @model_validator(mode="after")
    def _validate_enabled_template(self) -> "QuantizationTemplateSpec":
        if not self.enabled:
            return self
        if not self.calibration_dataset:
            raise ValueError("templates.quantization.calibration_dataset is required when quantization is enabled")
        if self.calibration_samples is None or self.calibration_samples <= 0:
            raise ValueError("templates.quantization.calibration_samples must be positive when quantization is enabled")
        return self


class TemplateRules(StrictBaseModel):
    preprocess: PreprocessTemplateSpec
    decode: DecodeTemplateSpec = Field(default_factory=DecodeTemplateSpec)
    nms: NmsTemplateSpec = Field(default_factory=NmsTemplateSpec)
    quantization: QuantizationTemplateSpec = Field(default_factory=QuantizationTemplateSpec)


class DraftRuleSet(StrictBaseModel):
    version: Literal[1] = 1
    defaults: RuleDefaults = Field(default_factory=RuleDefaults)
    selection: SelectionRules = Field(default_factory=SelectionRules)
    mapping: MappingRules = Field(default_factory=MappingRules)
    templates: TemplateRules
    notes: list[str] = Field(default_factory=list)


def load_rules(path: str | Path) -> DraftRuleSet:
    source = Path(path)
    try:
        raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuleError(f"failed to read rule file: {source}") from exc
    except yaml.YAMLError as exc:
        raise RuleError(f"failed to parse YAML rules: {source}") from exc

    if raw is None:
        raise RuleError(f"rule file is empty: {source}")
    if not isinstance(raw, dict):
        raise RuleError(f"rule root must be a mapping: {source}")

    try:
        return DraftRuleSet.model_validate(raw)
    except ValidationError as exc:
        raise RuleError(f"rule validation failed: {source}\n{exc}") from exc
