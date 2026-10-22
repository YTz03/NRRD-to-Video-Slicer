"""Unit tests for VolumeData (SRS §3.1, §4.1, §8.1, FR-2, FR-8)."""

from __future__ import annotations

from pathlib import Path
import nrrd
import numpy as np
import pytest

from src.exceptions import VolumeError
from src.volume_data import VolumeData


def test_load_valid_uint8_volume(
    nrrd_uint8_path: Path,
    analytical_volume_uint8: np.ndarray,
) -> None:
    """Verify loading a valid uint8 NRRD preserves M[x, y, z] axis order and read-only flag."""
    vol = VolumeData(nrrd_uint8_path)
    assert vol.shape == (32, 32, 32)
    assert vol.dtype == np.dtype(np.uint8)
    assert vol.matrix.flags.writeable is False
    assert vol.vmax == int(np.max(analytical_volume_uint8))
    np.testing.assert_array_equal(vol.matrix, analytical_volume_uint8)

    with pytest.raises(ValueError):
        vol.matrix[0, 0, 0] = 99


def test_load_valid_uint16_and_uint32_volumes(
    nrrd_uint16_path: Path,
    nrrd_uint32_path: Path,
) -> None:
    """Verify uint16 and uint32 NRRD files load properly and precompute vmax (FR-2, FR-8)."""
    vol16 = VolumeData(nrrd_uint16_path)
    assert vol16.shape == (16, 20, 24)
    assert vol16.dtype == np.dtype(np.uint16)
    assert vol16.vmax == 4000
    assert vol16.matrix[10, 12, 14] == 4000

    vol32 = VolumeData(nrrd_uint32_path)
    assert vol32.shape == (16, 16, 16)
    assert vol32.dtype == np.dtype(np.uint32)
    assert vol32.vmax == 100000
    assert vol32.matrix[8, 8, 8] == 100000


def test_promote_non_negative_signed_integer_volumes(tmp_path: Path) -> None:
    """Verify non-negative int8/int16/int32 NRRDs are promoted to uint8/uint16/uint32 (FR-2)."""
    arr_int16 = np.zeros((16, 16, 16), dtype=np.int16)
    arr_int16[4, 5, 6] = 279
    path = tmp_path / "non_negative_short.nrrd"
    nrrd.write(str(path), arr_int16)

    vol = VolumeData(path)
    assert vol.dtype == np.dtype(np.uint16)
    assert vol.vmax == 279
    assert vol.matrix[4, 5, 6] == 279
    assert vol.matrix.flags.writeable is False


def test_reject_non_3d_volume(tmp_path: Path) -> None:
    """Reject 2D arrays with VolumeError (exit code 2, FR-2)."""
    arr_2d = np.zeros((32, 32), dtype=np.uint8)
    path = tmp_path / "invalid_2d.nrrd"
    nrrd.write(str(path), arr_2d)

    with pytest.raises(VolumeError) as exc_info:
        VolumeData(path)
    assert exc_info.value.exit_code == 2
    assert "3D" in str(exc_info.value)


def test_reject_dimension_exceeding_1023(tmp_path: Path) -> None:
    """Reject volumes where any axis is >= 2^10 (1024) with VolumeError (FR-2)."""
    arr_large = np.zeros((1024, 2, 2), dtype=np.uint8)
    path = tmp_path / "too_large.nrrd"
    nrrd.write(str(path), arr_large)

    with pytest.raises(VolumeError) as exc_info:
        VolumeData(path)
    assert exc_info.value.exit_code == 2
    assert "1024" in str(exc_info.value)


@pytest.mark.parametrize("bad_dtype", [np.int16, np.int32, np.float32, np.float64])
def test_reject_signed_or_float_dtypes(tmp_path: Path, bad_dtype: type) -> None:
    """Reject negative signed integer or floating-point volumes with VolumeError (FR-2)."""
    arr = np.full((8, 8, 8), -1, dtype=bad_dtype)
    path = tmp_path / f"bad_{np.dtype(bad_dtype).name}.nrrd"
    nrrd.write(str(path), arr)

    with pytest.raises(VolumeError) as exc_info:
        VolumeData(path)
    assert exc_info.value.exit_code == 2
    assert "Unsupported voxel data type" in str(exc_info.value)


def test_reject_corrupted_nrrd_file(tmp_path: Path) -> None:
    """Reject unreadable/corrupted NRRD files with VolumeError (exit code 2)."""
    path = tmp_path / "corrupt.nrrd"
    path.write_text("NOT A VALID NRRD HEADER", encoding="utf-8")

    with pytest.raises(VolumeError) as exc_info:
        VolumeData(path)
    assert exc_info.value.exit_code == 2
