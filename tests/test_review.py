from __future__ import annotations

import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

import numpy as np

from videoaudit.decoder import sampled_rgb_frames
from videoaudit.pipeline import _sha256, audit_videos
from videoaudit.review import png_bytes, review_window


class ReviewTests(unittest.TestCase):
    def test_invalid_sampling_rates_rejected_before_decode(self):
        for value in (0, -1, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                sampled_rgb_frames(Path("missing.mp4"), value)

    def test_png_is_lossless_and_repeatable(self):
        frame = np.arange(27, dtype=np.uint8).reshape(3, 3, 3)
        encoded = png_bytes(frame)
        self.assertEqual(encoded, png_bytes(frame.copy()))
        self.assertEqual(encoded[:8], b"\x89PNG\r\n\x1a\n")
        pos, compressed = 8, b""
        while pos < len(encoded):
            size = struct.unpack(">I", encoded[pos:pos + 4])[0]
            kind, data = encoded[pos + 4:pos + 8], encoded[pos + 8:pos + 8 + size]
            self.assertEqual(zlib.crc32(kind + data), struct.unpack(">I", encoded[pos + 8 + size:pos + 12 + size])[0])
            if kind == b"IDAT":
                compressed += data
            pos += size + 12
        self.assertEqual(zlib.decompress(compressed), b"".join(b"\0" + r.tobytes() for r in frame))

    def fixture(self, root):
        video = root / "clip.mp4"
        video.write_bytes(b"test source")
        reference = root / "reference.json"
        reference.write_text(json.dumps({"sample_hz": 1.0,
            "method": "1 Hz decoded RGB audit at 180 px width",
            "clips": [{"clip": video.name, "sha256": _sha256(video),
                       "source_duration_s": 30, "low_sharpness_cutoff": 73.25}]}))
        return video, reference

    def test_window_preserves_grid_and_frozen_cutoff(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video, reference = self.fixture(root)
            def frames():
                for index in range(240):
                    yield index, index / 10, np.full((6, 6, 3), 127, dtype=np.uint8)
            with patch("videoaudit.review.sampled_rgb_frames", return_value=({}, frames())):
                result = review_window(video, reference, root / "out")
            self.assertEqual(result["sample_count"], 50)
            self.assertEqual(result["frozen_low_sharpness_cutoff"], 73.25)
            self.assertEqual(result["low_sharpness_times_s"], [i / 10 for i in range(180, 230)])
            self.assertEqual(result["snapshots_row_major"][0]["timestamp_s"], 18)
            self.assertEqual(result["snapshots_row_major"][-1]["timestamp_s"], 22.9)

    def test_source_mismatch_and_bad_window_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            video, reference = self.fixture(root)
            for start, end, rate in ((-1, 23, 10), (23, 18, 10), (18, 31, 10), (18, 23, float("nan"))):
                with self.subTest(start=start, end=end, rate=rate), self.assertRaises(ValueError):
                    review_window(video, reference, root / "out", start, end, rate)
            video.write_bytes(b"changed source")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                review_window(video, reference, root / "out")

    def test_nondefault_rate_appears_in_method(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            frames = iter([(i, i / 2, np.full((6, 6, 3), 127, dtype=np.uint8)) for i in range(3)])
            metadata = {"duration": 1.5, "fps": 30, "source_size": [6, 6], "codec": "test"}
            with patch("videoaudit.pipeline.sampled_rgb_frames", return_value=(metadata, frames)):
                result = audit_videos(root, root / "out", 2.0)
            self.assertEqual(result["method"], "2 Hz decoded RGB audit at 180 px width")
            self.assertEqual(result["sample_hz"], 2.0)


if __name__ == "__main__":
    unittest.main()
