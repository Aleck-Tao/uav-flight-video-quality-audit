from __future__ import annotations

import math
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
from imageio_ffmpeg import read_frames


def sampled_rgb_frames(
    path: Path,
    sample_hz: float = 1.0,
    output_width: int = 180,
) -> tuple[dict[str, Any], Iterator[tuple[int, float, np.ndarray]]]:
    if not math.isfinite(sample_hz) or sample_hz <= 0:
        raise ValueError("sample_hz must be finite and positive")
    generator = read_frames(
        str(path),
        pix_fmt="rgb24",
        output_params=["-vf", f"fps={sample_hz:g},scale={output_width}:-2"],
    )
    metadata = next(generator)
    width, height = metadata["size"]

    def iterator() -> Iterator[tuple[int, float, np.ndarray]]:
        try:
            for index, payload in enumerate(generator):
                frame = np.frombuffer(payload, dtype=np.uint8).reshape((height, width, 3))
                yield index, index / sample_hz, frame
        finally:
            generator.close()

    return metadata, iterator()
