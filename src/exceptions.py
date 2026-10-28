"""Domain exception hierarchy for the 3D Volumetric Plane Projection system (SRS NFR-3; SDD §3; EDD §1.4)."""

from __future__ import annotations


class SlicerError(Exception):
    """Base exception for all expected application errors, carrying a CLI exit code."""

    exit_code: int = 1

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InputError(SlicerError):
    """Raised on invalid CLI arguments, missing files, wrong extensions, or unwritable paths (FR-1)."""

    exit_code: int = 1


class VolumeError(SlicerError):
    """Raised when an NRRD file cannot be read or violates 3D grid/dtype constraints (FR-2)."""

    exit_code: int = 2


class PlaneError(SlicerError):
    """Raised when a CSV row or plane geometry fails structural or tolerance validation (FR-3, FR-4)."""

    exit_code: int = 2

    def __init__(self, reason: str, row_index: int | None = None) -> None:
        self.row_index = row_index
        self.reason = reason
        formatted = f"Row {row_index}: {reason}" if row_index is not None else reason
        super().__init__(formatted)


class EncodingError(SlicerError):
    """Raised when video stream initialization, frame writing, or finalization fails (FR-9)."""

    exit_code: int = 3
