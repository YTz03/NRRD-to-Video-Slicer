"""CSV plane list reader and factory (SRS §3.3, FR-3, FR-4)."""

from __future__ import annotations

import csv
from pathlib import Path

from src.exceptions import PlaneError
from src.plane import Plane, TrapezoidPlane, TrianglePlane

EXPECTED_COLUMNS = 13


class PlaneParser:
    """Parses a 13-column CSV trajectory file into a validated list of Plane objects."""

    def parse(self, csv_path: str | Path) -> tuple[list[Plane], list[str]]:
        """Read and validate all plane rows in the CSV file before any frame is rendered (FR-3, FR-4).

        Args:
            csv_path: Path to the input `.csv` file.

        Returns:
            Tuple of `(planes, warnings)` where `planes` is the ordered list of validated
            `Plane` objects and `warnings` is the list of warning messages for 1% < delta <= 10%.

        Raises:
            PlaneError: On the first malformed row, geometric violation > 10%, or empty trajectory.
        """
        path = Path(csv_path)
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle))
        except Exception as exc:
            raise PlaneError(f"Failed to read CSV file '{path}': {exc}") from exc

        planes: list[Plane] = []
        warnings: list[str] = []
        seen_first_nonblank = False

        for line_number, raw_row in enumerate(rows, start=1):
            # Ignore completely blank lines (FR-3)
            if not raw_row or all(cell.strip() == "" for cell in raw_row):
                continue

            # Skip optional header on the first non-blank line if its first cell is non-numeric (FR-3)
            if not seen_first_nonblank:
                seen_first_nonblank = True
                if not self._is_numeric(raw_row[0]):
                    continue

            plane = self._parse_row(raw_row, row_index=line_number)
            row_warnings = plane.validate()
            warnings.extend(row_warnings)
            planes.append(plane)

        if not planes:
            raise PlaneError("CSV file contains no valid plane rows.")

        return planes, warnings

    @staticmethod
    def _is_numeric(text: str) -> bool:
        try:
            float(text.strip())
            return True
        except ValueError:
            return False

    def _parse_row(self, row: list[str], row_index: int) -> Plane:
        """Parse a single 13-column CSV row into a TrianglePlane or TrapezoidPlane."""
        if len(row) != EXPECTED_COLUMNS:
            raise PlaneError(
                f"Expected {EXPECTED_COLUMNS} columns, got {len(row)}.",
                row_index=row_index,
            )

        count_str = row[0].strip()
        try:
            point_count_float = float(count_str)
            if not point_count_float.is_integer():
                raise ValueError
            point_count = int(point_count_float)
        except ValueError as exc:
            raise PlaneError(
                f"Invalid point count '{count_str}' in column 1; must be 3 or 4.",
                row_index=row_index,
            ) from exc

        if point_count not in (3, 4):
            raise PlaneError(
                f"Unsupported point count {point_count}; must be 3 (triangle) or 4 (trapezoid).",
                row_index=row_index,
            )

        if point_count == 3:
            # Columns 1..9 must be filled numbers; columns 10..12 must be empty (FR-3, FR-4)
            if any(cell.strip() != "" for cell in row[10:13]):
                raise PlaneError(
                    "Point count is 3, but 4th-point columns (x4, y4, z4) are not empty.",
                    row_index=row_index,
                )
            coords = self._parse_floats(row[1:10], row_index=row_index, expected_count=9)
            return TrianglePlane(
                row_index=row_index,
                a=coords[0:3],
                b=coords[3:6],
                c=coords[6:9],
            )

        # point_count == 4: Columns 1..12 must all be filled numbers in order a', b, a'', c (FR-3, FR-4)
        coords = self._parse_floats(row[1:13], row_index=row_index, expected_count=12)
        return TrapezoidPlane(
            row_index=row_index,
            a_prime=coords[0:3],
            b=coords[3:6],
            a_double_prime=coords[6:9],
            c=coords[9:12],
        )

    @staticmethod
    def _parse_floats(cells: list[str], row_index: int, expected_count: int) -> list[float]:
        values: list[float] = []
        for idx, cell in enumerate(cells, start=1):
            stripped = cell.strip()
            if stripped == "":
                raise PlaneError(
                    f"Missing coordinate value in coordinate cell {idx} (expected {expected_count} coordinates).",
                    row_index=row_index,
                )
            try:
                val = float(stripped)
            except ValueError as exc:
                raise PlaneError(
                    f"Non-numeric coordinate value '{stripped}' in coordinate cell {idx}.",
                    row_index=row_index,
                ) from exc
            values.append(val)
        return values
