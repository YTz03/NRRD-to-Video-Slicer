"""Unit tests for VideoExporter normalization, centered padding, and MP4 encoding (SRS FR-7..FR-9; SDD §2.5; STP TC-10, TC-11)."""

from __future__ import annotations

from pathlib import Path
import cv2
import numpy as np

from src.video_exporter import VideoExporter


def test_normalize_frame_uint8_unchanged() -> None:
    """uint8 frames are kept as-is without rescaling (FR-8)."""
    frame = np.array([[0, 50, 200]], dtype=np.uint8)
    norm = VideoExporter.normalize_frame(frame, vmax=200)
    assert norm.dtype == np.uint8
    np.testing.assert_array_equal(norm, frame)


def test_normalize_frame_uint16_and_uint32_global_vmax() -> None:
    """uint16 and uint32 frames scale by round(v * 255 / vmax), and all-zero volumes stay 0 (FR-8)."""
    frame16 = np.array([[0, 500, 1000]], dtype=np.uint16)
    norm16 = VideoExporter.normalize_frame(frame16, vmax=1000)
    np.testing.assert_array_equal(norm16, np.array([[0, 128, 255]], dtype=np.uint8))

    frame32 = np.array([[0, 50000, 100000]], dtype=np.uint32)
    norm32 = VideoExporter.normalize_frame(frame32, vmax=100000)
    np.testing.assert_array_equal(norm32, np.array([[0, 128, 255]], dtype=np.uint8))

    zero_norm = VideoExporter.normalize_frame(np.zeros((4, 4), dtype=np.uint16), vmax=0)
    assert np.all(zero_norm == 0)


def test_pad_frame_centers_with_black_border() -> None:
    """Smaller frames are centered on the (H_max, W_max) canvas with 0 (black) padding (FR-7)."""
    small = np.full((2, 4), 255, dtype=np.uint8)
    padded = VideoExporter.pad_frame(small, canvas_height=6, canvas_width=8)

    assert padded.shape == (6, 8)
    # Centered at rows 2..3, cols 2..5
    np.testing.assert_array_equal(padded[2:4, 2:6], 255)
    assert padded[0, 0] == 0
    assert padded[5, 7] == 0
    assert int(np.sum(padded == 255)) == 8


def test_video_exporter_writes_readable_mp4_stream(tmp_path: Path) -> None:
    """Verify VideoExporter writes a valid MP4 at 30 FPS with exact frame count and resolution (FR-9)."""
    mp4_path = tmp_path / "out.mp4"
    f1 = np.full((20, 30), 500, dtype=np.uint16)
    f2 = np.full((40, 50), 1000, dtype=np.uint16)

    with VideoExporter(mp4_path, canvas_height=40, canvas_width=50, vmax=1000) as exporter:
        assert exporter.canvas_shape == (40, 50)
        exporter.write_frame(f1)
        exporter.write_frame(f2)
        assert exporter.frames_written == 2

    assert mp4_path.is_file()
    assert mp4_path.stat().st_size > 0

    cap = cv2.VideoCapture(str(mp4_path))
    try:
        assert cap.isOpened()
        assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 2
        assert int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) == 40
        assert int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) == 50
        assert abs(cap.get(cv2.CAP_PROP_FPS) - 30.0) < 0.5
    finally:
        cap.release()
