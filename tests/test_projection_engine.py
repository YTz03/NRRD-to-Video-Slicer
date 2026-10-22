"""Unit tests for ProjectionEngine (SRS §3.4, §6, §8.1, FR-5, FR-6)."""

from __future__ import annotations

import numpy as np

from src.plane import EPSILON, Plane, TrapezoidPlane, TrianglePlane
from src.projection_engine import ProjectionEngine


def _sequential_reference_project(volume: np.ndarray, plane: Plane) -> np.ndarray:
    """Sequential scanline reference implementation from SRS §6.2 for equivalence verification."""
    n_rows = plane.height
    n_cols = plane.width
    t_l = plane.top_left
    t_r = plane.top_right
    b_l = plane.bottom_left
    b_r = plane.bottom_right
    sx, sy, sz = volume.shape

    out = np.zeros((n_rows, n_cols), dtype=volume.dtype)
    for y in range(n_rows):
        t = (y + 1.0) / n_rows
        a1 = t_l + t * (b_l - t_l)
        a2 = t_r + t * (b_r - t_r)
        vec = a2 - a1
        d12 = float(np.linalg.norm(vec))
        dp = vec / d12 if d12 > EPSILON else np.zeros(3, dtype=np.float64)

        for x in range(n_cols):
            x1 = x - (n_cols - d12) / 2.0
            if 0.0 <= x1 <= d12:
                p = a1 + x1 * dp
                ix, iy, iz = int(np.rint(p[0])), int(np.rint(p[1])), int(np.rint(p[2]))
                if 0 <= ix < sx and 0 <= iy < sy and 0 <= iz < sz:
                    out[y, x] = volume[ix, iy, iz]
    return out


def test_vectorized_matches_sequential_reference_triangle(
    analytical_volume_uint8: np.ndarray,
) -> None:
    """Verify vectorized triangle projection matches sequential scanline stepping pixel-for-pixel (§6.2, §6.3)."""
    tri = TrianglePlane(row_index=1, a=(16, 2, 16), b=(4, 26, 4), c=(28, 26, 28))
    engine = ProjectionEngine()

    vec_frame = engine.project(analytical_volume_uint8, tri)
    ref_frame = _sequential_reference_project(analytical_volume_uint8, tri)

    assert vec_frame.shape == (tri.height, tri.width)
    assert vec_frame.dtype == np.uint8
    np.testing.assert_array_equal(vec_frame, ref_frame)

    # Top row (near apex) has narrow scanline -> top-left and top-right corners outside triangle are 0 (FR-5)
    assert vec_frame[0, 0] == 0
    assert vec_frame[0, -1] == 0
    # Center of the triangle inside the volume is non-zero
    assert np.any(vec_frame > 0)


def test_vectorized_matches_sequential_reference_trapezoid(
    analytical_volume_uint8: np.ndarray,
) -> None:
    """Verify vectorized trapezoid projection matches sequential scanline stepping pixel-for-pixel."""
    trap = TrapezoidPlane(
        row_index=2,
        a_prime=(16, 4, 4),
        b=(16, 2, 24),
        a_double_prime=(16, 20, 4),
        c=(16, 22, 24),
    )
    engine = ProjectionEngine()

    vec_frame = engine.project(analytical_volume_uint8, trap)
    ref_frame = _sequential_reference_project(analytical_volume_uint8, trap)

    assert vec_frame.shape == (trap.height, trap.width)
    np.testing.assert_array_equal(vec_frame, ref_frame)


def test_out_of_volume_coordinates_masked_to_zero() -> None:
    """Sampled coordinates outside [0, sx-1] x [0, sy-1] x [0, sz-1] are assigned v = 0 (FR-6)."""
    vol = np.full((16, 16, 16), 200, dtype=np.uint8)
    engine = ProjectionEngine()

    # Plane completely outside the volume (negative coordinates)
    outside_tri = TrianglePlane(row_index=1, a=(-20, -20, -20), b=(-40, -20, -10), c=(-40, -20, -30))
    frame_outside = engine.project(vol, outside_tri)
    assert np.all(frame_outside == 0)

    # Plane partially intersecting the volume
    partial_tri = TrianglePlane(row_index=2, a=(8, 8, -10), b=(-10, 8, 10), c=(26, 8, 10))
    frame_partial = engine.project(vol, partial_tri)
    assert np.any(frame_partial == 200)
    assert np.any(frame_partial == 0)
