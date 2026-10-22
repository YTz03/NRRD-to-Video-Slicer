"""Geometry layer defining Plane, TrianglePlane, and TrapezoidPlane value objects (SRS §3.2, §4.3, §6.1)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence
import numpy as np

from src.exceptions import PlaneError

SILENT_TOLERANCE: float = 0.01  # 1%: accepted silently (FR-4)
MAX_TOLERANCE: float = 0.10     # 10%: above this aborts with PlaneError (FR-4)
EPSILON: float = 1e-9


def _to_vec3(coords: Sequence[float] | np.ndarray, row_index: int) -> np.ndarray:
    """Convert a 3-coordinate sequence into a read-only 1D float64 numpy array of shape (3,)."""
    arr = np.asarray(coords, dtype=np.float64)
    if arr.shape != (3,) or not np.all(np.isfinite(arr)):
        raise PlaneError("Point coordinates must be 3 finite real numbers.", row_index=row_index)
    arr = arr.copy()
    arr.flags.writeable = False
    return arr


@dataclass(frozen=True)
class Plane(ABC):
    """Abstract base class representing a 2D slicing plane region in 3D voxel space."""

    row_index: int

    @property
    @abstractmethod
    def top_left(self) -> np.ndarray:
        """Start point T_L of the left leg (shape (3,), float64)."""

    @property
    @abstractmethod
    def top_right(self) -> np.ndarray:
        """Start point T_R of the right leg (shape (3,), float64)."""

    @property
    @abstractmethod
    def bottom_left(self) -> np.ndarray:
        """End point B_L (b) of the left leg (shape (3,), float64)."""

    @property
    @abstractmethod
    def bottom_right(self) -> np.ndarray:
        """End point B_R (c) of the right leg (shape (3,), float64)."""

    @property
    def left_leg_length(self) -> float:
        """Euclidean length L1 = ||B_L - T_L||_2."""
        return float(np.linalg.norm(self.bottom_left - self.top_left))

    @property
    def right_leg_length(self) -> float:
        """Euclidean length L2 = ||B_R - T_R||_2."""
        return float(np.linalg.norm(self.bottom_right - self.top_right))

    @property
    def d_ab(self) -> float:
        """Longer leg length D_ab = max(L1, L2) (FR-5, §6.1)."""
        return max(self.left_leg_length, self.right_leg_length)

    @property
    @abstractmethod
    def d_bc(self) -> float:
        """Base width D_bc (FR-5, §6.1)."""

    @property
    def height(self) -> int:
        """Discrete output row count N = round(D_ab) (FR-5)."""
        return int(round(self.d_ab))

    @property
    def width(self) -> int:
        """Discrete output column count W = round(D_bc) (FR-5)."""
        return int(round(self.d_bc))

    def validate(self) -> list[str]:
        """Validate plane dimensions, isosceles leg tolerance, and shape-specific constraints (FR-4).

        Returns:
            A list of warning strings if 1% < delta <= 10%.

        Raises:
            PlaneError: If dimensions round to < 1 pixel or any deviation exceeds 10%.
        """
        l1 = self.left_leg_length
        l2 = self.right_leg_length
        max_leg = max(l1, l2)

        if max_leg < EPSILON or self.height < 1 or self.width < 1:
            raise PlaneError(
                f"Degenerate plane dimensions (height={self.height}, width={self.width}); must be >= 1 pixel.",
                row_index=self.row_index,
            )

        warnings: list[str] = []
        delta_leg = abs(l1 - l2) / max_leg
        if delta_leg > MAX_TOLERANCE:
            raise PlaneError(
                f"Isosceles leg difference {delta_leg:.2%} exceeds the 10% maximum limit.",
                row_index=self.row_index,
            )
        if delta_leg > SILENT_TOLERANCE:
            warnings.append(
                f"Warning (Row {self.row_index}): leg length difference is {delta_leg:.2%} (between 1% and 10%)."
            )

        self._validate_shape_specific(warnings)
        return warnings

    def _validate_shape_specific(self, warnings: list[str]) -> None:
        """Hook for subclass-specific geometric checks."""


@dataclass(frozen=True)
class TrianglePlane(Plane):
    """3-point isosceles triangle plane (a, b, c) with apex a and base b -> c (SRS §3.2, §6.1)."""

    a: np.ndarray
    b: np.ndarray
    c: np.ndarray

    def __init__(
        self,
        row_index: int,
        a: Sequence[float] | np.ndarray,
        b: Sequence[float] | np.ndarray,
        c: Sequence[float] | np.ndarray,
    ) -> None:
        object.__setattr__(self, "row_index", int(row_index))
        object.__setattr__(self, "a", _to_vec3(a, row_index))
        object.__setattr__(self, "b", _to_vec3(b, row_index))
        object.__setattr__(self, "c", _to_vec3(c, row_index))

    @property
    def top_left(self) -> np.ndarray:
        return self.a

    @property
    def top_right(self) -> np.ndarray:
        return self.a

    @property
    def bottom_left(self) -> np.ndarray:
        return self.b

    @property
    def bottom_right(self) -> np.ndarray:
        return self.c

    @property
    def d_bc(self) -> float:
        return float(np.linalg.norm(self.c - self.b))

    def _validate_shape_specific(self, warnings: list[str]) -> None:
        # Check that a, b, c are not collinear (triangle must have non-zero area)
        cross_norm = float(np.linalg.norm(np.cross(self.b - self.a, self.c - self.a)))
        if cross_norm < EPSILON:
            raise PlaneError(
                "Degenerate triangle: points a, b, c are collinear.",
                row_index=self.row_index,
            )


@dataclass(frozen=True)
class TrapezoidPlane(Plane):
    """4-point isosceles trapezoid plane (a', b, a'', c) with legs a' -> b and a'' -> c (SRS §3.2, §6.1)."""

    a_prime: np.ndarray
    b: np.ndarray
    a_double_prime: np.ndarray
    c: np.ndarray

    def __init__(
        self,
        row_index: int,
        a_prime: Sequence[float] | np.ndarray,
        b: Sequence[float] | np.ndarray,
        a_double_prime: Sequence[float] | np.ndarray,
        c: Sequence[float] | np.ndarray,
    ) -> None:
        object.__setattr__(self, "row_index", int(row_index))
        object.__setattr__(self, "a_prime", _to_vec3(a_prime, row_index))
        object.__setattr__(self, "b", _to_vec3(b, row_index))
        object.__setattr__(self, "a_double_prime", _to_vec3(a_double_prime, row_index))
        object.__setattr__(self, "c", _to_vec3(c, row_index))

    @property
    def top_left(self) -> np.ndarray:
        return self.a_prime

    @property
    def top_right(self) -> np.ndarray:
        return self.a_double_prime

    @property
    def bottom_left(self) -> np.ndarray:
        return self.b

    @property
    def bottom_right(self) -> np.ndarray:
        return self.c

    @property
    def d_bc(self) -> float:
        top_base = float(np.linalg.norm(self.a_double_prime - self.a_prime))
        bottom_base = float(np.linalg.norm(self.c - self.b))
        return max(top_base, bottom_base)

    def _validate_shape_specific(self, warnings: list[str]) -> None:
        # Check coplanarity of (a', b, a'', c) relative to D_ab (FR-4)
        v_leg1 = self.b - self.a_prime
        v_top = self.a_double_prime - self.a_prime
        normal = np.cross(v_leg1, v_top)
        norm_len = float(np.linalg.norm(normal))

        if norm_len < EPSILON:
            # Try normal from bottom base if top base is near-zero
            normal = np.cross(v_leg1, self.c - self.a_prime)
            norm_len = float(np.linalg.norm(normal))
            if norm_len < EPSILON:
                raise PlaneError(
                    "Degenerate trapezoid: all four points are collinear.",
                    row_index=self.row_index,
                )

        dist_c_to_plane = abs(float(np.dot(self.c - self.a_prime, normal))) / norm_len
        delta_cop = dist_c_to_plane / self.d_ab

        if delta_cop > MAX_TOLERANCE:
            raise PlaneError(
                f"Trapezoid coplanarity deviation {delta_cop:.2%} exceeds the 10% maximum limit.",
                row_index=self.row_index,
            )
        if delta_cop > SILENT_TOLERANCE:
            warnings.append(
                f"Warning (Row {self.row_index}): trapezoid coplanarity deviation is {delta_cop:.2%} (between 1% and 10%)."
            )
