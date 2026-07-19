from __future__ import annotations

import unittest

import numpy as np

from videoaudit.metrics import compute_frame_metrics, laplacian_variance, rgb_to_luma, summarize_clip


class VideoMetricTests(unittest.TestCase):
    def test_uniform_frame_has_zero_sharpness(self) -> None:
        frame = np.full((12, 12, 3), 128, dtype=np.uint8)
        self.assertAlmostEqual(laplacian_variance(rgb_to_luma(frame)), 0.0, places=6)

    def test_edge_frame_is_sharper_than_uniform_frame(self) -> None:
        uniform = np.full((20, 20, 3), 128, dtype=np.uint8)
        edge = uniform.copy()
        edge[:, 10:, :] = 255
        self.assertGreater(
            laplacian_variance(rgb_to_luma(edge)),
            laplacian_variance(rgb_to_luma(uniform)),
        )

    def test_exposure_and_temporal_metrics(self) -> None:
        dark = np.zeros((10, 10, 3), dtype=np.uint8)
        bright = np.full((10, 10, 3), 255, dtype=np.uint8)
        first, first_luma = compute_frame_metrics("clip.mp4", 0, 0.0, dark, None)
        second, _ = compute_frame_metrics("clip.mp4", 1, 1.0, bright, first_luma)
        self.assertEqual(first.dark_fraction, 1.0)
        self.assertEqual(second.clipped_fraction, 1.0)
        self.assertAlmostEqual(second.temporal_luma_delta or 0.0, 255.0, places=5)
        summary = summarize_clip([first, second])
        self.assertEqual(summary["sample_count"], 2)


if __name__ == "__main__":
    unittest.main()
