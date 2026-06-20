from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image

from .contracts import ModelContract


class PreprocessError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResizeMetadata:
    mode: str
    target_width: int
    target_height: int
    resized_width: int
    resized_height: int
    pad_left: int
    pad_top: int
    pad_right: int
    pad_bottom: int


@dataclass(frozen=True)
class PreprocessResult:
    source_width: int
    source_height: int
    display_ready_image: np.ndarray
    model_ready_image: np.ndarray
    input_tensor: np.ndarray
    tensor_dtype: str
    resize: ResizeMetadata
    input_color_space: str
    output_color_space: str
    input_layout: str
    output_layout: str


def load_image_rgb(path: str | Path) -> np.ndarray:
    source = Path(path)
    try:
        with Image.open(source) as image:
            return np.asarray(image.convert("RGB"), dtype=np.uint8)
    except OSError as exc:
        raise PreprocessError(f"failed to read image: {source}") from exc


def _convert_color(image: np.ndarray, source: str, target: str) -> np.ndarray:
    if source == target:
        return image.copy()

    if source == "RGB" and target == "BGR":
        return image[..., ::-1].copy()
    if source == "BGR" and target == "RGB":
        return image[..., ::-1].copy()

    if target == "GRAY":
        if source == "BGR":
            rgb_image = image[..., ::-1]
        else:
            rgb_image = image
        gray = np.round(
            0.299 * rgb_image[..., 0] + 0.587 * rgb_image[..., 1] + 0.114 * rgb_image[..., 2]
        ).astype(np.uint8)
        return gray

    if source == "GRAY" and target in {"RGB", "BGR"}:
        rgb = np.repeat(image[..., None], 3, axis=2)
        if target == "BGR":
            return rgb[..., ::-1].copy()
        return rgb

    raise PreprocessError(f"unsupported color conversion: {source} -> {target}")


def _to_pil(image: np.ndarray, color_space: str) -> Image.Image:
    if color_space == "GRAY":
        if image.ndim == 3:
            image = image[..., 0]
        return Image.fromarray(image.astype(np.uint8), mode="L")

    if color_space == "BGR":
        image = image[..., ::-1]

    return Image.fromarray(image.astype(np.uint8), mode="RGB")


def _from_pil(image: Image.Image, color_space: str) -> np.ndarray:
    if color_space == "GRAY":
        return np.asarray(image.convert("L"), dtype=np.uint8)

    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    if color_space == "BGR":
        return rgb[..., ::-1].copy()
    return rgb


def _normalize_pad_value(pad_value: int | list[int], channels: int, color_space: str) -> np.ndarray:
    if isinstance(pad_value, int):
        if color_space == "GRAY" or channels == 1:
            return np.asarray(pad_value, dtype=np.uint8)
        return np.full((channels,), pad_value, dtype=np.uint8)

    values = np.asarray(pad_value, dtype=np.uint8)
    if values.size == 1:
        if color_space == "GRAY" or channels == 1:
            return values[0]
        return np.full((channels,), int(values[0]), dtype=np.uint8)

    if channels == 1 and values.size >= 1:
        return values[0]
    if values.size != channels:
        raise PreprocessError(f"pad_value length {values.size} does not match channel count {channels}")
    return values


def _resize_and_pad(
    image: np.ndarray,
    target_width: int,
    target_height: int,
    mode: Literal["stretch", "letterbox", "keep_ratio"],
    interpolation: Literal["nearest", "bilinear", "area", "bicubic"],
    keep_aspect_ratio: bool,
    pad_value: int | list[int],
    color_space: str,
) -> tuple[np.ndarray, ResizeMetadata]:
    resample_map = {
        "nearest": Image.Resampling.NEAREST,
        "bilinear": Image.Resampling.BILINEAR,
        "area": Image.Resampling.BOX,
        "bicubic": Image.Resampling.BICUBIC,
    }
    pil_image = _to_pil(image, color_space)
    source_width, source_height = pil_image.size

    if mode == "stretch" or not keep_aspect_ratio:
        resized = pil_image.resize((target_width, target_height), resample=resample_map[interpolation])
        result = _from_pil(resized, color_space)
        return result, ResizeMetadata(
            mode=mode,
            target_width=target_width,
            target_height=target_height,
            resized_width=target_width,
            resized_height=target_height,
            pad_left=0,
            pad_top=0,
            pad_right=0,
            pad_bottom=0,
        )

    scale = min(target_width / source_width, target_height / source_height)
    resized_width = max(1, int(round(source_width * scale)))
    resized_height = max(1, int(round(source_height * scale)))
    resized = pil_image.resize((resized_width, resized_height), resample=resample_map[interpolation])
    resized_array = _from_pil(resized, color_space)

    if mode == "keep_ratio":
        return resized_array, ResizeMetadata(
            mode=mode,
            target_width=target_width,
            target_height=target_height,
            resized_width=resized_width,
            resized_height=resized_height,
            pad_left=0,
            pad_top=0,
            pad_right=0,
            pad_bottom=0,
        )

    channels = 1 if resized_array.ndim == 2 else resized_array.shape[2]
    fill = _normalize_pad_value(pad_value, channels, color_space)
    if resized_array.ndim == 2:
        canvas = np.full((target_height, target_width), fill, dtype=np.uint8)
    else:
        canvas = np.full((target_height, target_width, channels), fill, dtype=np.uint8)

    pad_left = (target_width - resized_width) // 2
    pad_top = (target_height - resized_height) // 2
    pad_right = target_width - resized_width - pad_left
    pad_bottom = target_height - resized_height - pad_top
    canvas[pad_top : pad_top + resized_height, pad_left : pad_left + resized_width, ...] = resized_array

    return canvas, ResizeMetadata(
        mode=mode,
        target_width=target_width,
        target_height=target_height,
        resized_width=resized_width,
        resized_height=resized_height,
        pad_left=pad_left,
        pad_top=pad_top,
        pad_right=pad_right,
        pad_bottom=pad_bottom,
    )


def _normalize_image(image: np.ndarray, scale: float | list[float], mean: list[float], std: list[float]) -> np.ndarray:
    values = image.astype(np.float32)

    if isinstance(scale, list):
        scale_values = np.asarray(scale, dtype=np.float32)
        values = values * scale_values
    else:
        values = values * float(scale)

    if mean:
        mean_values = np.asarray(mean, dtype=np.float32)
        values = values - mean_values

    if std:
        std_values = np.asarray(std, dtype=np.float32)
        if np.any(std_values == 0):
            raise PreprocessError("normalize.std cannot contain zero")
        values = values / std_values

    return values


def _to_output_layout(image: np.ndarray, output_layout: str) -> np.ndarray:
    if output_layout == "NHWC":
        if image.ndim == 2:
            return image[np.newaxis, ..., np.newaxis]
        return image[np.newaxis, ...]

    if output_layout == "NCHW":
        if image.ndim == 2:
            return image[np.newaxis, np.newaxis, ...]
        return np.transpose(image, (2, 0, 1))[np.newaxis, ...]

    raise PreprocessError(f"unsupported output layout for image inspection: {output_layout}")


def prepare_image(contract: ModelContract, image_path: str | Path) -> PreprocessResult:
    source_rgb = load_image_rgb(image_path)
    source_height, source_width = source_rgb.shape[:2]

    preprocess = contract.preprocess
    input_view = _convert_color(source_rgb, "RGB", preprocess.input_color_space)
    output_color_space = preprocess.output_color_space or preprocess.input_color_space
    color_aligned = _convert_color(input_view, preprocess.input_color_space, output_color_space)

    target_height, target_width = preprocess.resize.target_size
    resized_image, resize_meta = _resize_and_pad(
        color_aligned,
        target_width=target_width,
        target_height=target_height,
        mode=preprocess.resize.mode,
        interpolation=preprocess.resize.interpolation,
        keep_aspect_ratio=preprocess.resize.keep_aspect_ratio,
        pad_value=preprocess.pad_value,
        color_space=output_color_space,
    )

    normalized = resized_image
    if preprocess.normalize is not None:
        normalized = _normalize_image(
            resized_image,
            scale=preprocess.normalize.scale,
            mean=preprocess.normalize.mean,
            std=preprocess.normalize.std,
        )
    else:
        normalized = resized_image.astype(np.float32)

    tensor = _to_output_layout(normalized, preprocess.output_layout).astype(np.float32)
    if tuple(int(dim) for dim in tensor.shape) != tuple(contract.input.shape):
        raise PreprocessError(
            f"preprocessed tensor shape {list(tensor.shape)} does not match declared input shape {contract.input.shape}"
        )

    display_ready = resized_image
    if output_color_space == "BGR":
        display_ready = resized_image[..., ::-1].copy()
    elif output_color_space == "GRAY" and resized_image.ndim == 2:
        display_ready = np.repeat(resized_image[..., None], 3, axis=2)

    return PreprocessResult(
        source_width=source_width,
        source_height=source_height,
        display_ready_image=display_ready,
        model_ready_image=resized_image,
        input_tensor=tensor,
        tensor_dtype=str(tensor.dtype),
        resize=resize_meta,
        input_color_space=preprocess.input_color_space,
        output_color_space=output_color_space,
        input_layout=preprocess.input_layout,
        output_layout=preprocess.output_layout,
    )


def save_preview_image(path: str | Path, image: np.ndarray) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image.astype(np.uint8), mode="RGB").save(target)
    return target
