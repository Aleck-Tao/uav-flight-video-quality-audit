from __future__ import annotations

import csv
import json
from pathlib import Path
from xml.sax.saxutils import escape

from .metrics import FrameMetrics


def write_frame_csv(rows: list[FrameMetrics], path: Path) -> None:
    fieldnames = list(rows[0].to_dict())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())


def write_summary(summary: dict[str, object], path: Path) -> None:
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_report(summary: dict[str, object], path: Path) -> None:
    clips = summary["clips"]
    lines = [
        "# UAV Field-Test Video Quality Audit",
        "",
        f"Analyzed **{summary['total_samples']} frames** sampled at **{summary['sample_hz']:.1f} Hz** from {len(clips)} original MP4 clips.",
        "",
        "| Clip | Duration | Samples | Mean luma | Luma p05-p95 | Median sharpness | Low-sharpness samples | Max dark | Max clipped |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for clip in clips:
        lines.append(
            f"| `{clip['clip']}` | {clip['source_duration_s']:.2f} s | {clip['sample_count']} | "
            f"{clip['mean_luma']:.2f} | {clip['luma_p05']:.2f}–{clip['luma_p95']:.2f} | "
            f"{clip['median_sharpness']:.1f} | {clip['low_sharpness_samples']} | "
            f"{clip['max_dark_fraction'] * 100:.2f}% | {clip['max_clipped_fraction'] * 100:.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This audit measures properties of the released evidence videos, not autonomy or perception accuracy. Luma and clipping metrics identify exposure failures; Laplacian variance is a resolution-dependent sharpness proxy; temporal luma change highlights large visual transitions. The low-sharpness cutoff is a robust within-clip outlier rule (Q1 - 1.5*IQR, with a floor of 20).",
            "",
            "Every input video is tied to its byte size and SHA-256 hash in `summary.json`. Re-run `python -m videoaudit` to regenerate this report, the per-frame CSV and the SVG timeline.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_timeline(rows: list[FrameMetrics], path: Path) -> None:
    clips = sorted({row.clip for row in rows})
    width, panel_height = 1000, 250
    height = 70 + panel_height * len(clips)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#0f172a"/>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#e2e8f0}.small{font-size:12px;fill:#94a3b8}</style>',
        '<text x="35" y="35" font-size="22" font-weight="700">UAV video evidence quality timeline</text>',
        '<text x="35" y="57" class="small">Blue: mean luma (0–255). Amber: sharpness normalized within each clip.</text>',
    ]
    for panel, clip in enumerate(clips):
        subset = [row for row in rows if row.clip == clip]
        left, top, chart_width, chart_height = 70, 95 + panel * panel_height, 880, 165
        max_time = max(row.timestamp_s for row in subset) or 1.0
        max_sharpness = max(row.sharpness_laplacian_var for row in subset) or 1.0
        luma_points = " ".join(
            f"{left + row.timestamp_s / max_time * chart_width:.1f},{top + chart_height - row.mean_luma / 255.0 * chart_height:.1f}"
            for row in subset
        )
        sharpness_points = " ".join(
            f"{left + row.timestamp_s / max_time * chart_width:.1f},{top + chart_height - row.sharpness_laplacian_var / max_sharpness * chart_height:.1f}"
            for row in subset
        )
        svg.extend(
            [
                f'<text x="{left}" y="{top - 14}" font-size="14">{escape(clip)}</text>',
                f'<rect x="{left}" y="{top}" width="{chart_width}" height="{chart_height}" fill="#111c33" stroke="#334155"/>',
                f'<polyline points="{luma_points}" fill="none" stroke="#38bdf8" stroke-width="2"/>',
                f'<polyline points="{sharpness_points}" fill="none" stroke="#f59e0b" stroke-width="1.5" opacity="0.85"/>',
                f'<text x="{left}" y="{top + chart_height + 20}" class="small">0 s</text>',
                f'<text x="{left + chart_width}" y="{top + chart_height + 20}" text-anchor="end" class="small">{max_time:.0f} s</text>',
            ]
        )
    svg.append("</svg>")
    path.write_text("\n".join(svg), encoding="utf-8")
