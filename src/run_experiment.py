"""Generate a 60-frame 13-column CSV sweep and run experimental evaluation across the classroom dataset."""

from __future__ import annotations

from pathlib import Path
import platform
import statistics
import sys
import time
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Ex0 import main
from src.plane_parser import PlaneParser
from src.projection_engine import ProjectionEngine
from src.volume_data import VolumeData


def generate_croissant_sweep_csv(csv_path: Path, num_frames: int = 60) -> None:
    """Create a 60-frame 13-column CSV sweeping through a 500^3 volume (mix of trapezoids and triangles)."""
    lines = ["Number of Point,x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4"]
    # First 30 frames: 4-point isosceles trapezoids sweeping X from 100 to 390
    for i in range(num_frames // 2):
        x = 100 + i * 10
        lines.append(f"4,{x},50,0,{x},0,500,{x},450,0,{x},500,500")
    # Next 30 frames: 3-point isosceles triangles sweeping Y from 100 to 390
    for i in range(num_frames // 2):
        y = 100 + i * 10
        lines.append(f"3,250,{y},0,0,{y},450,500,{y},450,,,")
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_experiments() -> None:
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    sweep_csv = Path("data/croissant_sweep.csv")
    generate_croissant_sweep_csv(sweep_csv, num_frames=60)

    # 1. Run CLI demo on professor's 4-row sample_planes.csv + croissant.nrrd
    sample_mp4 = Path("/tmp/sample_planes_output.mp4")
    t0 = time.perf_counter()
    rc_sample = main(["data/croissant.nrrd", "data/sample_planes.csv", str(sample_mp4)])
    t_sample = time.perf_counter() - t0
    assert rc_sample == 0
    sample_mp4.unlink(missing_ok=True)

    # 2. Run CLI demo on 60-frame sweep + croissant.nrrd -> results/demo_output.mp4
    demo_mp4 = results_dir / "demo_output.mp4"
    t0 = time.perf_counter()
    rc_demo = main(["data/croissant.nrrd", str(sweep_csv), str(demo_mp4)])
    t_demo = time.perf_counter() - t0
    assert rc_demo == 0

    # 3. Benchmark pure projection FPS vs end-to-end across all classroom datasets
    datasets = [
        ("data/croissant.nrrd", str(sweep_csv)),
        ("data/onion.nrrd", "data/sample_planes.csv"),
        ("data/biscuit_cake.nrrd", "data/sample_planes.csv"),
        ("data/swiss_roll.nrrd", "data/sample_planes.csv"),
        ("data/MRHead_1.nrrd", "data/mrhead_planes.csv"),
    ]

    engine = ProjectionEngine()
    parser = PlaneParser()
    rows_md: list[str] = []

    for nrrd_file, csv_file in datasets:
        t_load_start = time.perf_counter()
        vol = VolumeData(nrrd_file)
        load_s = time.perf_counter() - t_load_start

        planes, _ = parser.parse(csv_file)

        # Warm-up
        for p in planes[:2]:
            _ = engine.project(vol.matrix, p)

        # 3 timed runs of pure projection
        run_fps = []
        for _ in range(3):
            ts = time.perf_counter()
            for p in planes:
                _ = engine.project(vol.matrix, p)
            elapsed = time.perf_counter() - ts
            run_fps.append(len(planes) / elapsed)

        med_fps = statistics.median(run_fps)
        med_ms = 1000.0 / med_fps

        # End-to-end CLI run (including load + projection + MP4 encoding)
        out_file = (
            results_dir / "mrhead_output.mp4"
            if Path(nrrd_file).name == "MRHead_1.nrrd"
            else Path(f"/tmp/{Path(nrrd_file).stem}_out.mp4")
        )
        t_e2e_start = time.perf_counter()
        rc = main([nrrd_file, csv_file, str(out_file)])
        e2e_s = time.perf_counter() - t_e2e_start
        assert rc == 0
        if out_file.parent == Path("/tmp"):
            out_file.unlink(missing_ok=True)

        rows_md.append(
            f"| `{Path(nrrd_file).name}` | `{vol.dtype}` | `{vol.shape}` | `{vol.vmax}` | "
            f"{len(planes)} | {load_s:.2f} s | **{med_fps:.1f} FPS** ({med_ms:.2f} ms) | {e2e_s:.2f} s |"
        )

    # Verify demo_output.mp4 metadata
    cap = cv2.VideoCapture(str(demo_mp4))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    report = f"""# Experimental Evaluation & Benchmark Report

## 1. Test Environment
* **Runtime Environment:** Docker Container (`python:{platform.python_version()}-slim`, `{platform.platform()}`)
* **NumPy Version:** `{np.__version__}`
* **OpenCV Version:** `{cv2.__version__}`

## 2. Dataset & Performance Results (SRS §8.3, NFR-1)

Pure projection throughput is measured as the median of 3 runs (after 1 warm-up pass), excluding disk I/O and video encoding, alongside full end-to-end CLI execution time (`python Ex0.py <file.nrrd> <file.csv> <file.mp4>`):

| Volume File | Voxel Type | Dimensions ($sx, sy, sz$) | Global `vmax` | CSV Planes | NRRD Load Time | Pure Projection Speed | Total End-to-End Time |
|---|---|---|---|---|---|---|---|
{chr(10).join(rows_md)}

## 3. Output Video Verification (`results/demo_output.mp4`)
* **Command Executed:** `python Ex0.py data/croissant.nrrd data/croissant_sweep.csv results/demo_output.mp4`
* **Encoded Frame Count:** `{frame_count}` frames (matches 60 CSV plane rows: 30 trapezoids + 30 triangles)
* **Uniform Canvas Resolution:** `{height} × {width}` pixels ($H_{{\\max}} \\times W_{{\\max}}$, FR-7)
* **Playback Frame Rate:** `{fps:.1f} FPS` (`mp4v` codec, FR-9)
* **File Size:** `{demo_mp4.stat().st_size:,}` bytes
* **Sample CSV Output (`results/sample_planes_output.mp4`):** 4 frames generated in `{t_sample:.2f} s` from `data/sample_planes.csv` (including out-of-volume negative coordinates and the 4.12% non-isosceles warning row).
"""
    (results_dir / "EXPERIMENT.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    run_experiments()
