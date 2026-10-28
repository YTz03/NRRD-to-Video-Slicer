"""Stateless vectorized 3D-to-2D projection engine (SRS FR-5, FR-6, NFR-1; SDD §2.4; EDD §2)."""

from __future__ import annotations

import numpy as np

from src.plane import EPSILON, Plane


class ProjectionEngine:
    """Computes 2D cross-sectional slices of a 3D volume using NumPy broadcasting."""

    def project(self, volume: np.ndarray, plane: Plane) -> np.ndarray:
        """Project a 3D volume M onto the given Plane P to produce a 2D frame E (EDD §2.4).

        Args:
            volume: 3D numpy.ndarray M of shape (sx, sy, sz) indexed as M[x, y, z].
            plane: Validated Plane object (TrianglePlane or TrapezoidPlane).

        Returns:
            2D numpy.ndarray E of shape (height, width) = (N, W) with the same dtype as M.
            Pixels outside the triangle/trapezoid footprint or outside M hold 0.
        """
        n_rows = plane.height
        n_cols = plane.width
        t_l = plane.top_left
        t_r = plane.top_right
        b_l = plane.bottom_left
        b_r = plane.bottom_right
        sx, sy, sz = volume.shape

        # Step 1: 1D Row Arrays (shape (N, 1) and (N, 3))
        y = np.arange(n_rows, dtype=np.float64)[:, None]                # (N, 1)
        t = (y + 1.0) / n_rows                                          # (N, 1)
        a1 = t_l[None, :] + t * (b_l - t_l)[None, :]                    # (N, 3)
        a2 = t_r[None, :] + t * (b_r - t_r)[None, :]                    # (N, 3)
        vec = a2 - a1                                                   # (N, 3)
        d12 = np.linalg.norm(vec, axis=1, keepdims=True)                # (N, 1)
        dp = np.divide(vec, d12, out=np.zeros_like(vec), where=(d12 > EPSILON))

        # Step 2: 2D Scanline Offset & Shape Mask (shape (N, W))
        x = np.arange(n_cols, dtype=np.float64)[None, :]                # (1, W)
        x1 = x - (n_cols - d12) / 2.0                                   # (N, W)
        mask_shape = (x1 >= 0.0) & (x1 <= d12)                          # (N, W) bool

        # Step 3: 3D Sample Coordinates & Nearest-Neighbor Rounding (shape (N, W))
        ix = np.rint(a1[:, 0:1] + x1 * dp[:, 0:1]).astype(np.intp)
        iy = np.rint(a1[:, 1:2] + x1 * dp[:, 1:2]).astype(np.intp)
        iz = np.rint(a1[:, 2:3] + x1 * dp[:, 2:3]).astype(np.intp)

        # Step 4: Volume Boundary Mask (shape (N, W))
        mask_vol = (
            (ix >= 0) & (ix < sx)
            & (iy >= 0) & (iy < sy)
            & (iz >= 0) & (iz < sz)
        )
        valid = mask_shape & mask_vol                                   # (N, W) bool

        # Step 5: Single-Pass Masked Voxel Gather (shape (N, W))
        frame = np.zeros((n_rows, n_cols), dtype=volume.dtype)
        frame[valid] = volume[ix[valid], iy[valid], iz[valid]]
        return frame
