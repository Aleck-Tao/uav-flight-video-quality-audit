# Methodology and Interpretation

## Sampling

Each MP4 is decoded with the pinned `imageio-ffmpeg` distribution. Frames are sampled at 1 Hz and scaled to 180 pixels wide while preserving aspect ratio. Sampling makes the audit fast and deterministic while covering the full duration of each clip.

## Frame metrics

RGB pixels are converted to Rec. 709 luma. The audit records mean luma, the fraction below 16, and the fraction above 240. These values expose black frames, severe underexposure, and highlight clipping.

Sharpness is the variance of a four-neighbour discrete Laplacian. It is resolution dependent and is therefore interpreted within a clip, not as an absolute camera benchmark. A low-sharpness outlier is below Q1 - 1.5*IQR, with a minimum cutoff of 20.

Temporal luma delta is the mean absolute difference between consecutive one-second luma samples. It can reveal abrupt visual transitions but does not separate camera motion, scene motion, and exposure change.

## Provenance

The pipeline records input byte sizes, codec metadata, duration, resolution, frame rate, and SHA-256. Reports can therefore be traced to the exact public media files.

## Limitations

The audit does not estimate pose, optical flow, object detections, or autonomy performance. A 1 Hz sample can miss short defects. Laplacian variance is affected by texture and scale as well as focus and motion blur. The outputs should be used to select segments for deeper analysis, not as a flight-safety certificate.
