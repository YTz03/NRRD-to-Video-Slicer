"""Shared pytest fixtures for synthetic volumes and 13-column CSV trajectories (SRS §7.2, §8.1)."""

from __future__ import annotations

from pathlib import Path
import sys
import nrrd
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def analytical_volume_uint8() -> np.ndarray:
    """Create a 32x32x32 uint8 analytical volume where M[x, y, z] = (x + 2*y + 3*z) % 256."""
    x, y, z = np.meshgrid(
        np.arange(32, dtype=np.uint8),
        np.arange(32, dtype=np.uint8),
        np.arange(32, dtype=np.uint8),
        indexing="ij",
    )
    vol = (x.astype(np.uint16) + 2 * y.astype(np.uint16) + 3 * z.astype(np.uint16)) % 256
    return vol.astype(np.uint8)


@pytest.fixture
def nrrd_uint8_path(tmp_path: Path, analytical_volume_uint8: np.ndarray) -> Path:
    """Write the 32x32x32 uint8 analytical volume to a temporary .nrrd file."""
    path = tmp_path / "analytical_uint8.nrrd"
    nrrd.write(str(path), analytical_volume_uint8, index_order="F")
    return path


@pytest.fixture
def nrrd_uint16_path(tmp_path: Path) -> Path:
    """Write a 16x20x24 uint16 volume with known vmax = 4000 to a temporary .nrrd file."""
    vol = np.zeros((16, 20, 24), dtype=np.uint16)
    vol[5, 6, 7] = 2000
    vol[10, 12, 14] = 4000
    path = tmp_path / "sample_uint16.nrrd"
    nrrd.write(str(path), vol, index_order="F")
    return path


@pytest.fixture
def nrrd_uint32_path(tmp_path: Path) -> Path:
    """Write a 16x16x16 uint32 volume with known vmax = 100000 to a temporary .nrrd file."""
    vol = np.zeros((16, 16, 16), dtype=np.uint32)
    vol[8, 8, 8] = 100000
    path = tmp_path / "sample_uint32.nrrd"
    nrrd.write(str(path), vol, index_order="F")
    return path


@pytest.fixture
def sample_csv_path(tmp_path: Path) -> Path:
    """Write a valid 4-row 13-column CSV matching the professor's sample format (3 & 4 points)."""
    csv_text = (
        "Number of Point,x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4\n"
        "3,16,16,0,0,16,20,32,16,20,,,\n"
        "4,16,0,0,16,0,24,16,24,0,16,24,24\n"
        "3,16,16,-5,-4,16,20,32,18,20,,,\n"
        "4,16,4,0,16,0,24,16,20,0,16,24,24\n"
    )
    path = tmp_path / "planes.csv"
    path.write_text(csv_text, encoding="utf-8")
    return path
