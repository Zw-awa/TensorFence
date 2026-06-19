from __future__ import annotations

from textwrap import dedent

SAMPLE_CONTRACT_NAME = "detection_contract.yaml"

SAMPLE_CONTRACT_YAML = dedent(
    """
    name: tensorfence-demo-yolo
    task: detection
    source_framework: pytorch
    target_runtime: rknn
    input:
      name: images
      shape: [1, 3, 640, 640]
      dtype: float32
      layout: NCHW
      semantic: model_input
    outputs:
      - name: output0
        shape: [1, 8400, 85]
        dtype: float32
        layout: N/A
        semantic: raw_predictions
    preprocess:
      input_color_space: BGR
      output_color_space: RGB
      input_layout: HWC
      output_layout: NCHW
      resize:
        mode: letterbox
        target_size: [640, 640]
        interpolation: bilinear
        keep_aspect_ratio: true
    decode:
      family: yolo
      mode: anchor_free
      num_classes: 80
      strides: [8, 16, 32]
      head_names: [output0]
      score_activation: sigmoid
      box_activation: sigmoid
    nms:
      score_threshold: 0.25
      iou_threshold: 0.45
    quantization:
      enabled: false
    """
).strip() + "\n"

