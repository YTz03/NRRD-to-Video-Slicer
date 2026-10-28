"""End-to-end CLI demo verification tests for Ex0.py (SRS FR-1..FR-9, NFR-2, NFR-3; STP TC-12..TC-14)."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import cv2

from Ex0 import main


def test_cli_valid_demo_run_end_to_end(
    nrrd_uint8_path: Path,
    sample_csv_path: Path,
    tmp_path: Path,
) -> None:
    """Run `python Ex0.py <file.nrrd> <file.csv> <file.mp4>` and verify MP4 output (STP TC-12)."""
    out_mp4 = tmp_path / "demo.mp4"
    result = subprocess.run(
        [sys.executable, "Ex0.py", str(nrrd_uint8_path), str(sample_csv_path), str(out_mp4)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, f"stderr: {result.stderr}"
    # Row 3 in sample_csv_path has 1% < delta <= 10%, so a warning is printed to stderr
    assert "Warning" in result.stderr
    assert out_mp4.is_file()
    assert out_mp4.stat().st_size > 0

    cap = cv2.VideoCapture(str(out_mp4))
    try:
        assert cap.isOpened()
        assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 4
        assert abs(cap.get(cv2.CAP_PROP_FPS) - 30.0) < 0.5
    finally:
        cap.release()


def test_cli_exit_code_1_on_bad_arguments_or_missing_files(
    nrrd_uint8_path: Path,
    sample_csv_path: Path,
    tmp_path: Path,
) -> None:
    """Verify exit code 1 on wrong argument count, wrong extension, or missing input files (FR-1, NFR-3)."""
    assert main([]) == 1
    assert main([str(nrrd_uint8_path), str(sample_csv_path)]) == 1
    assert main([str(nrrd_uint8_path), str(sample_csv_path), str(tmp_path / "bad.avi")]) == 1
    assert main([str(tmp_path / "missing.nrrd"), str(sample_csv_path), str(tmp_path / "out.mp4")]) == 1


def test_cli_exit_code_2_on_bad_csv_row_creates_no_video(
    nrrd_uint8_path: Path,
    tmp_path: Path,
) -> None:
    """Verify exit code 2 when a CSV row fails validation, leaving no partial .mp4 file on disk (FR-4, NFR-3)."""
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text(
        "Number of Point,x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4\n"
        "3,16,16,0,0,16,20,32,16,20,,,\n"
        "3,0,0,0,100,0,0,0,200,0,,,\n",  # 50% leg mismatch -> abort on row 3
        encoding="utf-8",
    )
    out_mp4 = tmp_path / "should_not_exist.mp4"

    code = main([str(nrrd_uint8_path), str(bad_csv), str(out_mp4)])
    assert code == 2
    assert not out_mp4.exists()
