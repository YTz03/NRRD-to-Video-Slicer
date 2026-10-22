"""Performance benchmark test for 500^3 uint8 volume projection throughput (SRS §8.3, NFR-1)."""

from __future__ import annotations

import statistics
import time
import numpy as np

from src.plane import TrianglePlane
from src.projection_engine import ProjectionEngine


def test_500_cubed_projection_fps_benchmark() -> None:
    """Measure pure projection FPS on a 500^3 uint8 volume with 500x500 planes (NFR-1).

    Protocol (SRS §2.2 NFR-1 & §8.3):
    - 500 x 500 x 500 uint8 volume
    - 500 x 500 slicing planes
    - 1 warm-up pass, followed by >= 3 timed runs
    - Assert median throughput >= 30 FPS (<= 33.3 ms/frame)
    """
    volume = np.ones((500, 500, 500), dtype=np.uint8)
    # Isosceles triangle with height N = 500 and width W = 500 inside the 500^3 volume:
    # Base b -> c has length 500 along X; height along Y/Z so L1 = L2 = 500 -> dy = sqrt(500^2 - 250^2) = 433.0127
    plane = TrianglePlane(
        row_index=1,
        a=(250.0, 30.0, 250.0),
        b=(0.0, 463.01270189, 250.0),
        c=(500.0, 463.01270189, 250.0),
    )
    assert plane.height == 500
    assert plane.width == 500

    engine = ProjectionEngine()
    frames_per_run = 30

    # Warm-up pass
    _ = engine.project(volume, plane)

    run_fps_values: list[float] = []
    for _ in range(3):
        t0 = time.perf_counter()
        for _ in range(frames_per_run):
            _ = engine.project(volume, plane)
        elapsed = time.perf_counter() - t0
        run_fps_values.append(frames_per_run / elapsed)

    median_fps = statistics.median(run_fps_values)
    median_ms = 1000.0 / median_fps
    print(f"\n[Benchmark 500^3 uint8] Median: {median_fps:.1f} FPS ({median_ms:.2f} ms/frame)")

    assert median_fps >= 30.0, f"Expected >= 30 FPS on 500^3 volume, got {median_fps:.1f} FPS."
