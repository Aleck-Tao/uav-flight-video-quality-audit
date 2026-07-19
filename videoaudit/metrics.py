from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class FrameMetrics:
    clip: str
    sample_index: int
    timestamp_s: float
    mean_luma: float
    dark_fraction: float
    clipped_fraction: float
    sharpness_laplacian_var: float
    temporal_luma_delta: float | None

    def to_dict(self) -> dict[str, float | int | str | None]:
        return asdict(self)


def rgb_to_luma(frame: np.ndarray) -> np.ndarray:
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("Expected an HxWx3 RGB frame")
    return (
        0.2126 * frame[:, :, 0].astype(np.float32)
        + 0.7152 * frame[:, :, 1].astype(np.float32)
        + 0.0722 * frame[:, :, 2].astype(np.float32)
    )


def laplacian_variance(luma: np.ndarray) -> float:
    if min(luma.shape) < 3:
        raise ValueError("Frame is too small for a Laplacian sharpness estimate")
    center = luma[1:-1, 1:-1]
    laplacian = (
        luma[:-2, 1:-1]
        + luma[2:, 1:-1]
        + luma[1:-1, :-2]
        + luma[1:-1, 2:]
        - 4.0 * center
    )
    return float(np.var(laplacian))


def compute_frame_metrics(
    clip: str,
    sample_index: int,
    timestamp_s: float,
    frame: np.ndarray,
    previous_luma: np.ndarray | None,
) -> tuple[FrameMetrics, np.ndarray]:
    luma = rgb_to_luma(frame)
    temporal_delta = None
    if previous_luma is not None:
        temporal_delta = float(np.mean(np.abs(luma - previous_luma)))
    result = FrameMetrics(
        clip=clip,
        sample_index=sample_index,
        timestamp_s=timestamp_s,
        mean_luma=float(np.mean(luma)),
        dark_fraction=float(np.mean(luma < 16.0)),
        clipped_fraction=float(np.mean(luma > 240.0)),
        sharpness_laplacian_var=laplacian_variance(luma),
        temporal_luma_delta=temporal_delta,
    )
    return result, luma


def summarize_clip(rows: list[FrameMetrics]) -> dict[str, float | int | str]:
    if not rows:
        raise ValueError("Cannot summarize an empty clip")
    brightness = np.asarray([row.mean_luma for row in rows])
    sharpness = np.asarray([row.sharpness_laplacian_var for row in rows])
    dark = np.asarray([row.dark_fraction for row in rows])
    clipped = np.asarray([row.clipped_fraction for row in rows])
    temporal = np.asarray([row.temporal_luma_delta for row in rows if row.temporal_luma_delta is not None])
    q1, q3 = np.percentile(sharpness, [25, 75])
    low_sharpness_cutoff = max(20.0, float(q1 - 1.5 * (q3 - q1)))
    return {
        "clip": rows[0].clip,
        "sample_count": len(rows),
        "sampled_duration_s": rows[-1].timestamp_s,
        "mean_luma": float(np.mean(brightness)),
        "luma_p05": float(np.percentile(brightness, 5)),
        "luma_p95": float(np.percentile(brightness, 95)),
        "median_sharpness": float(np.median(sharpness)),
        "sharpness_p05": float(np.percentile(sharpness, 5)),
        "low_sharpness_cutoff": low_sharpness_cutoff,
        "low_sharpness_samples": int(np.sum(sharpness < low_sharpness_cutoff)),
        "max_dark_fraction": float(np.max(dark)),
        "max_clipped_fraction": float(np.max(clipped)),
        "mean_temporal_luma_delta": float(np.mean(temporal)) if len(temporal) else 0.0,
    }
