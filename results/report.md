# UAV Field-Test Video Quality Audit

Analyzed **224 frames** sampled at **1.0 Hz** from 2 original MP4 clips.

| Clip | Duration | Samples | Mean luma | Luma p05-p95 | Median sharpness | Low-sharpness samples | Max dark | Max clipped |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `uav_field_test_clip_a.mp4` | 91.33 s | 91 | 128.62 | 119.03–140.97 | 254.5 | 0 | 4.41% | 0.55% |
| `uav_field_test_clip_b.mp4` | 132.90 s | 133 | 133.41 | 126.55–143.38 | 216.7 | 2 | 1.94% | 1.09% |

## Interpretation

This audit measures properties of the released evidence videos, not autonomy or perception accuracy. Luma and clipping metrics identify exposure failures; Laplacian variance is a resolution-dependent sharpness proxy; temporal luma change highlights large visual transitions. The low-sharpness cutoff is a robust within-clip outlier rule (Q1 - 1.5*IQR, with a floor of 20).

Every input video is tied to its byte size and SHA-256 hash in `summary.json`. Re-run `python -m videoaudit` to regenerate this report, the per-frame CSV and the SVG timeline.
