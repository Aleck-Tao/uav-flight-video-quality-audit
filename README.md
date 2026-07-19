# UAV Flight-Video Quality Audit

[![CI](https://github.com/Aleck-Tao/uav-flight-video-quality-audit/actions/workflows/ci.yml/badge.svg)](https://github.com/Aleck-Tao/uav-flight-video-quality-audit/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/code%20license-MIT-green.svg)](LICENSE)

A reproducible computer-vision data audit over two original outdoor UAV field-test videos. The pipeline decodes the actual MP4 files at 1 Hz and measures exposure, dark/highlight clipping, Laplacian sharpness, and frame-to-frame luminance change.

The research motivation is simple: before field footage is used for perception experiments, its visual quality and provenance should be measured rather than assumed.

![Video quality timeline](results/timeline.svg)

## Released-video result

| Clip | Duration | Samples | Mean luma | Median sharpness | Low-sharpness samples | Max dark | Max clipped |
|---|---:|---:|---:|---:|---:|---:|---:|
| Clip A | 91.33 s | 91 | 128.62 | 254.5 | 0 | 4.41% | 0.55% |
| Clip B | 132.90 s | 133 | 133.41 | 216.7 | 2 | 1.94% | 1.09% |

The committed audit covers **224 decoded frames**. Clip B contains two within-clip low-sharpness outliers under the robust rule. Neither clip shows widespread black-frame or highlight-clipping failure at the sampled instants.

These are properties of the released evidence videos. They are not claims about autonomous flight, obstacle avoidance, or localization accuracy.

## Reproduce

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
videoaudit
```

The default command reads `data/videos/*.mp4` and writes:

- `results/frame_metrics.csv`: one row per decoded sample;
- `results/summary.json`: container metadata, aggregate metrics, file sizes, and SHA-256 hashes;
- `results/report.md`: a reviewer-readable result table and interpretation;
- `results/timeline.svg`: brightness and normalized sharpness across both clips.

The CI workflow reruns the tests and complete video audit, then verifies that every committed result is reproducible.

## Metrics

- **Mean luma:** Rec. 709 weighted RGB brightness on a 0-255 scale.
- **Dark fraction:** decoded pixels with luma below 16.
- **Clipped fraction:** decoded pixels with luma above 240.
- **Sharpness:** variance of a four-neighbour discrete Laplacian, used as a within-resolution blur proxy.
- **Temporal luma delta:** mean absolute luma difference from the preceding one-second sample.
- **Low-sharpness sample:** below Q1 - 1.5*IQR for that clip, with a floor of 20.

See [`docs/methodology.md`](docs/methodology.md) for assumptions and interpretation.

## Repository layout

```text
videoaudit/    decoder, frame metrics, provenance, and reporting
data/videos/  two original field-test MP4 files
results/      committed frame CSV, summary JSON, report, and timeline
tests/        numerical metric tests
docs/         methodology and evidence boundaries
```

## Evidence integrity

The raw videos retain their original bytes. `data/videos/MEDIA_MANIFEST.md` records sizes and SHA-256 hashes. The audit summary repeats these hashes, tying every reported metric to a specific input file.

Code is MIT licensed. The original video media remain copyright Yuanyuan Tao and are included for academic/research review; see [`MEDIA_NOTICE.md`](MEDIA_NOTICE.md).

Related repositories: [research portfolio](https://github.com/Aleck-Tao/computer-vision-autonomous-systems-portfolio), [multi-sensor diagnostics](https://github.com/Aleck-Tao/uav-multisensor-diagnostics), and [safety-constrained mission interface](https://github.com/Aleck-Tao/safety-constrained-uav-mission-interface).
