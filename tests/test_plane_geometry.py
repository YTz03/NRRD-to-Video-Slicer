"""Unit tests for Plane, TrianglePlane, and TrapezoidPlane geometry and validation (SRS §3.2, §4.3, FR-4, FR-5)."""

from __future__ import annotations

import numpy as np
import pytest

from src.exceptions import PlaneError
from src.plane import TrapezoidPlane, TrianglePlane


def test_triangle_plane_four_corner_interface_and_dimensions() -> None:
    """Verify TrianglePlane maps top_left == top_right == a and computes rounded (height, width)."""
    # Isosceles triangle: a=(200,200,0), b=(0,200,400), c=(400,200,400)
    # L1 = sqrt(200^2 + 400^2) = 447.2136 -> N = 447
    # D_bc = 400.0 -> W = 400
    tri = TrianglePlane(row_index=2, a=(200, 200, 0), b=(0, 200, 400), c=(400, 200, 400))
    warnings = tri.validate()

    assert warnings == []
    np.testing.assert_array_equal(tri.top_left, [200.0, 200.0, 0.0])
    np.testing.assert_array_equal(tri.top_right, [200.0, 200, 0.0])
    np.testing.assert_array_equal(tri.bottom_left, [0.0, 200.0, 400.0])
    np.testing.assert_array_equal(tri.bottom_right, [400.0, 200.0, 400.0])
    assert tri.height == 447
    assert tri.width == 400


def test_trapezoid_plane_four_corner_interface_and_longer_base() -> None:
    """Verify TrapezoidPlane maps a', b, a'', c and uses the longer base for width (FR-5)."""
    # Row 4 from professor's sample: a'=(200,50,0), b=(200,0,500), a''=(200,350,0), c=(200,400,500)
    # L1 = L2 = sqrt(50^2 + 500^2) = 502.4938 -> N = 502
    # top base = 300, bottom base = 400 -> W = max(300, 400) = 400
    trap = TrapezoidPlane(
        row_index=5,
        a_prime=(200, 50, 0),
        b=(200, 0, 500),
        a_double_prime=(200, 350, 0),
        c=(200, 400, 500),
    )
    warnings = trap.validate()

    assert warnings == []
    np.testing.assert_array_equal(trap.top_left, [200.0, 50.0, 0.0])
    np.testing.assert_array_equal(trap.top_right, [200.0, 350.0, 0.0])
    np.testing.assert_array_equal(trap.bottom_left, [200.0, 0.0, 500.0])
    np.testing.assert_array_equal(trap.bottom_right, [200.0, 400.0, 500.0])
    assert trap.height == 502
    assert trap.width == 400


def test_leg_difference_within_1_percent_accepted_silently() -> None:
    """Leg difference <= 1% produces no warnings (FR-4)."""
    # L1 = 100.0, L2 = 100.8 (delta = 0.7936% <= 1%)
    tri = TrianglePlane(row_index=1, a=(0, 0, 0), b=(100, 0, 0), c=(0, 100.8, 0))
    warnings = tri.validate()
    assert warnings == []


def test_leg_difference_between_1_and_10_percent_emits_warning() -> None:
    """Leg difference in (1%, 10%] is accepted with a warning naming the row number (FR-4)."""
    # Row 3 from professor's sample: delta ~ 4.12%
    tri = TrianglePlane(
        row_index=4,
        a=(200, 200, -30),
        b=(-50, 200, 400),
        c=(400, 250, 400),
    )
    warnings = tri.validate()
    assert len(warnings) == 1
    assert "Row 4" in warnings[0]
    assert "%" in warnings[0]
    assert tri.height == round(max(tri.left_leg_length, tri.right_leg_length))


def test_leg_difference_above_10_percent_raises_plane_error() -> None:
    """Leg difference > 10% aborts with PlaneError (exit code 2, FR-4)."""
    # L1 = 100, L2 = 120 -> delta = 20 / 120 = 16.67% > 10%
    tri = TrianglePlane(row_index=7, a=(0, 0, 0), b=(100, 0, 0), c=(0, 120, 0))
    with pytest.raises(PlaneError) as exc_info:
        tri.validate()
    assert exc_info.value.exit_code == 2
    assert exc_info.value.row_index == 7
    assert "10%" in str(exc_info.value)


def test_trapezoid_coplanarity_warning_and_abort() -> None:
    """Verify trapezoid coplanarity check warns in (1%, 10%] and aborts above 10% (FR-4)."""
    # Coplanar in z=0 plane except c_z lifted by 5 on D_ab=100 -> 5% warning
    trap_warn = TrapezoidPlane(
        row_index=3,
        a_prime=(0, 0, 0),
        b=(0, 100, 0),
        a_double_prime=(50, 0, 0),
        c=(50, 100, 5),
    )
    warnings = trap_warn.validate()
    assert any("coplanarity" in w for w in warnings)

    # Lift c_z by 25 on D_ab ~ 103 -> > 10% abort
    trap_bad = TrapezoidPlane(
        row_index=8,
        a_prime=(0, 0, 0),
        b=(0, 100, 0),
        a_double_prime=(50, 0, 0),
        c=(50, 100, 25),
    )
    with pytest.raises(PlaneError) as exc_info:
        trap_bad.validate()
    assert exc_info.value.row_index == 8
    assert exc_info.value.exit_code == 2


def test_degenerate_coinciding_points_raise_plane_error() -> None:
    """Coinciding points or collinear triangles raise PlaneError instead of dividing by zero (FR-4, NFR-3)."""
    coinciding = TrianglePlane(row_index=9, a=(10, 10, 10), b=(10, 10, 10), c=(10, 10, 10))
    with pytest.raises(PlaneError):
        coinciding.validate()

    collinear = TrianglePlane(row_index=10, a=(0, 0, 0), b=(10, 0, 0), c=(-10, 0, 0))
    with pytest.raises(PlaneError):
        collinear.validate()
