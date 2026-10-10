"""A denser inspection of a flagged window, retaining the full-clip cutoff."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import struct
import zlib

import numpy as np

from .decoder import sampled_rgb_frames
from .metrics import compute_frame_metrics
from .pipeline import DEFAULT_VIDEO_DIR, PROJECT_ROOT, _sha256
from .reporting import write_frame_csv, write_summary, write_timeline


def png_bytes(frame: np.ndarray) -> bytes:
    """Portable RGB PNG with stored DEFLATE blocks (no encoder-version drift)."""
    if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("expected uint8 RGB")
    height, width, _ = frame.shape
    raw = b"".join(b"\0" + row.tobytes() for row in frame)
    blocks = []
    for pos in range(0, len(raw), 65535):
        block = raw[pos:pos + 65535]
        blocks.append(bytes([int(pos + len(block) == len(raw))])
                      + struct.pack("<HH", len(block), len(block) ^ 65535) + block)
    compressed = b"\x78\x01" + b"".join(blocks) + struct.pack(">I", zlib.adler32(raw))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", compressed) + chunk(b"IEND", b""))


def review_window(video: Path, reference: Path, output: Path,
                  start_s: float = 18.0, end_s: float = 23.0,
                  sample_hz: float = 10.0) -> dict:
    if not all(math.isfinite(v) for v in (start_s, end_s, sample_hz)):
        raise ValueError("window and rate must be finite")
    if not 0 <= start_s < end_s or sample_hz <= 0:
        raise ValueError("require 0 <= start < end and positive sample_hz")
    baseline = json.loads(reference.read_text(encoding="utf-8"))
    if baseline["sample_hz"] != 1.0 or baseline["method"] != "1 Hz decoded RGB audit at 180 px width":
        raise ValueError("reference must be the 1 Hz / 180 px full-clip audit")
    clip = next((c for c in baseline["clips"] if c["clip"] == video.name), None)
    if clip is None or clip["sha256"] != _sha256(video):
        raise ValueError("reference and video SHA-256 do not match")
    if end_s > clip["source_duration_s"]:
        raise ValueError("window extends beyond source duration")
    cutoff = float(clip["low_sharpness_cutoff"])
    if not math.isfinite(cutoff) or cutoff < 0:
        raise ValueError("invalid reference cutoff")

    _, stream = sampled_rgb_frames(video, sample_hz=sample_hz)
    rows, frames = [], []
    previous_luma = None
    try:
        for index, timestamp, frame in stream:
            if timestamp >= end_s:
                break
            if timestamp < start_s:
                continue
            row, previous_luma = compute_frame_metrics(
                video.name, index, timestamp, frame, previous_luma)
            rows.append(row)
            frames.append(frame.copy())
    finally:
        stream.close()
    if not rows:
        raise ValueError("no decoded samples in requested window")

    output.mkdir(parents=True, exist_ok=True)
    selected = np.linspace(0, len(rows) - 1, min(6, len(rows)), dtype=int)
    snapshots = []
    h, w, _ = frames[0].shape
    sheet = np.full((2 * h + 36, 3 * w + 48, 3), 255, dtype=np.uint8)
    for slot, index in enumerate(selected):
        filename = f"frame_{rows[index].timestamp_s:06.2f}s.png"
        (output / filename).write_bytes(png_bytes(frames[index]))
        y, x = 12 + (slot // 3) * (h + 12), 12 + (slot % 3) * (w + 12)
        sheet[y:y + h, x:x + w] = frames[index]
        snapshots.append({"timestamp_s": rows[index].timestamp_s, "file": filename})
    (output / "contact_sheet.png").write_bytes(png_bytes(sheet))
    low = [r.timestamp_s for r in rows if r.sharpness_laplacian_var < cutoff]
    summary = {
        "clip": video.name, "source_sha256": clip["sha256"],
        "reference_sha256": _sha256(reference),
        "source_hashes": {p.name: _sha256(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
        "window_s": [start_s, end_s], "end_exclusive": True,
        "sample_hz": sample_hz, "output_width_px": 180,
        "timestamp_basis": "ffmpeg fps-filter output grid from full-clip decode, not original frame PTS",
        "sample_count": len(rows), "frozen_low_sharpness_cutoff": cutoff,
        "low_sharpness_samples": len(low), "low_sharpness_times_s": low,
        "min_sharpness": min(r.sharpness_laplacian_var for r in rows),
        "max_mean_luma": max(r.mean_luma for r in rows),
        "temporal_delta_interval_s": 1 / sample_hz,
        "snapshots_row_major": snapshots,
    }
    write_frame_csv(rows, output / "frame_metrics.csv")
    write_summary(summary, output / "summary.json")
    write_timeline(rows, output / "timeline.svg", start_s=start_s)
    caption = ", ".join(f"{s['timestamp_s']:g} s" for s in snapshots)
    lines = ["# Clip B: local inspection", "",
             f"Window [{start_s:g}, {end_s:g}) s, {sample_hz:g} Hz, {len(rows)} decoded samples at 180 px width.", "",
             f"{len(low)} samples fall below the frozen full-clip cutoff ({cutoff:.3f}); minimum sharpness is {summary['min_sharpness']:.3f}.",
             f"Maximum mean luma: {summary['max_mean_luma']:.3f}.", "",
             "![Six uniformly spaced inspection samples](contact_sheet.png)", "",
             f"Left to right, top to bottom: {caption}.", "",
             "The cutoff comes from the original 1 Hz full-clip audit; it is not refitted to this short window. "
             "Low-sharpness counts describe sampled frames, not independently detected defect events. "
             "Timestamps are the fps-filter output grid, not original camera timestamps.", "",
             f"Temporal luma differences here span {1 / sample_hz:g} s (first sample has no predecessor); "
             "they must not be compared directly with the 1 s differences in the original audit. "
             "Sharpness remains a texture- and scale-dependent proxy, not a blur diagnosis.", "",
             "Run `python -m videoaudit.review`. Source hashes, the frozen reference hash and exact sample times are in `summary.json` and `frame_metrics.csv`.", ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, default=DEFAULT_VIDEO_DIR / "uav_field_test_clip_b.mp4")
    parser.add_argument("--reference", type=Path, default=PROJECT_ROOT / "results" / "summary.json")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "results" / "clip-b-review")
    parser.add_argument("--start", type=float, default=18.0)
    parser.add_argument("--end", type=float, default=23.0)
    parser.add_argument("--sample-hz", type=float, default=10.0)
    args = parser.parse_args()
    result = review_window(args.video, args.reference, args.output, args.start, args.end, args.sample_hz)
    print(f"Reviewed {result['sample_count']} samples; {result['low_sharpness_samples']} below frozen cutoff")


if __name__ == "__main__":
    main()
