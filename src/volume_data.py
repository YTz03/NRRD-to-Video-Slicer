"""Data ingestion layer for loading and validating 3D NRRD volumes (SRS §3.1, §4.1, FR-2, FR-8)."""

from __future__ import annotations

from pathlib import Path
import nrrd
import numpy as np

from src.exceptions import VolumeError

MAX_DIMENSION_EXCLUSIVE = 1 << 10  # 2^10 = 1024
ALLOWED_DTYPES = (np.dtype(np.uint8), np.dtype(np.uint16), np.dtype(np.uint32))
SIGNED_TO_UNSIGNED = {
    np.dtype(np.int8): np.dtype(np.uint8),
    np.dtype(np.int16): np.dtype(np.uint16),
    np.dtype(np.int32): np.dtype(np.uint32),
}


class VolumeData:
    """Loads, validates, and holds a read-only 3D volumetric raster matrix M."""

    def __init__(self, file_path: str | Path) -> None:
        self._path = Path(file_path)
        raw_matrix = self._load_nrrd(self._path)
        validated = self._validate_matrix(raw_matrix)

        # Ensure contiguous memory and enforce strict read-only immutability (SRS §4.1)
        matrix = np.ascontiguousarray(validated)
        matrix.flags.writeable = False
        self._matrix: np.ndarray = matrix

        # Precompute global maximum intensity once at load time for FR-8 normalization
        self._vmax: int = int(np.max(self._matrix))

    @staticmethod
    def _load_nrrd(path: Path) -> np.ndarray:
        """Read an NRRD file with axis order M[x, y, z] (first NRRD axis = x)."""
        try:
            data, _ = nrrd.read(str(path), index_order="F")
        except Exception as exc:
            raise VolumeError(f"Failed to parse NRRD file '{path}': {exc}") from exc
        return data

    @staticmethod
    def _validate_matrix(matrix: np.ndarray) -> np.ndarray:
        """Validate 3D dimensionality, size bounds (1 <= s < 2^10), and unsigned int dtype (FR-2)."""
        if not isinstance(matrix, np.ndarray) or matrix.ndim != 3:
            ndim = getattr(matrix, "ndim", "N/A")
            raise VolumeError(f"Volume must be a 3D matrix, got {ndim}D.")

        sx, sy, sz = matrix.shape
        if not (
            1 <= sx < MAX_DIMENSION_EXCLUSIVE
            and 1 <= sy < MAX_DIMENSION_EXCLUSIVE
            and 1 <= sz < MAX_DIMENSION_EXCLUSIVE
        ):
            raise VolumeError(
                f"Volume dimensions ({sx}, {sy}, {sz}) must satisfy 1 <= sx, sy, sz < {MAX_DIMENSION_EXCLUSIVE}."
            )

        if matrix.dtype in SIGNED_TO_UNSIGNED:
            if int(np.min(matrix)) < 0:
                raise VolumeError(
                    f"Unsupported voxel data type '{matrix.dtype}' with negative values; voxel values must be unsigned."
                )
            matrix = matrix.astype(SIGNED_TO_UNSIGNED[matrix.dtype], copy=False)

        if matrix.dtype not in ALLOWED_DTYPES:
            raise VolumeError(
                f"Unsupported voxel data type '{matrix.dtype}'. Allowed types: uint8, uint16, uint32."
            )
        return matrix

    @property
    def matrix(self) -> np.ndarray:
        """Read-only 3D numpy.ndarray M indexed as M[x, y, z]."""
        return self._matrix

    @property
    def shape(self) -> tuple[int, int, int]:
        """Dimensions (sx, sy, sz) of the 3D volume."""
        sx, sy, sz = self._matrix.shape
        return int(sx), int(sy), int(sz)

    @property
    def dtype(self) -> np.dtype:
        """Unsigned integer NumPy dtype of the volume."""
        return self._matrix.dtype

    @property
    def vmax(self) -> int:
        """Global maximum voxel value in M (computed once at load time, FR-8)."""
        return self._vmax
