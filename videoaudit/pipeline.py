from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from .decoder import sampled_rgb_frames
from .metrics import FrameMetrics, compute_frame_metrics, summarize_clip
from .reporting import write_frame_csv, write_report, write_summary, write_timeline


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VIDEO_DIR = PROJECT_ROOT / "data" / "videos"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_videos(video_dir: Path, output_dir: Path, sample_hz: float = 1.0) -> dict[str, object]:
    videos = sorted(video_dir.glob("*.mp4"))
    if not videos:
        raise FileNotFoundError(f"No MP4 files found in {video_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[FrameMetrics] = []
    clip_summaries: list[dict[str, object]] = []

    for video in videos:
        metadata, frames = sampled_rgb_frames(video, sample_hz=sample_hz)
        rows: list[FrameMetrics] = []
        previous_luma = None
        for index, timestamp, frame in frames:
            metrics, previous_luma = compute_frame_metrics(
                video.name, index, timestamp, frame, previous_luma
            )
            rows.append(metrics)
        clip_summary: dict[str, object] = summarize_clip(rows)
        clip_summary.update(
            {
                "source_duration_s": float(metadata["duration"]),
                "source_fps": float(metadata["fps"]),
                "source_size": list(metadata["source_size"]),
                "codec": str(metadata["codec"]),
                "file_bytes": video.stat().st_size,
                "sha256": _sha256(video),
            }
        )
        clip_summaries.append(clip_summary)
        all_rows.extend(rows)

    summary: dict[str, object] = {
        "tool": "videoaudit 1.0.0",
        "method": "1 Hz decoded RGB audit at 180 px width",
        "sample_hz": sample_hz,
        "total_samples": len(all_rows),
        "clips": clip_summaries,
    }
    write_frame_csv(all_rows, output_dir / "frame_metrics.csv")
    write_summary(summary, output_dir / "summary.json")
    write_report(summary, output_dir / "report.md")
    write_timeline(all_rows, output_dir / "timeline.svg")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit exposure and sharpness of UAV field-test videos")
    parser.add_argument("video_dir", type=Path, nargs="?", default=DEFAULT_VIDEO_DIR)
    parser.add_argument("output_dir", type=Path, nargs="?", default=PROJECT_ROOT / "results")
    parser.add_argument("--sample-hz", type=float, default=1.0)
    args = parser.parse_args(argv)
    summary = audit_videos(args.video_dir, args.output_dir, args.sample_hz)
    print(f"Analyzed {summary['total_samples']} sampled frames from {len(summary['clips'])} clips")
    return 0
