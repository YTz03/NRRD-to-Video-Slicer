"""Unit tests for PlaneParser (SRS FR-3, FR-4; SDD §2.3; STP TC-06, TC-07)."""

from __future__ import annotations

from pathlib import Path
import pytest

from src.exceptions import PlaneError
from src.plane import TrapezoidPlane, TrianglePlane
from src.plane_parser import PlaneParser


def test_parse_professor_sample_csv() -> None:
    """Verify parsing the 4-row professor sample CSV with mixed 3 & 4 point rows and warning on row 4.

    - Sent to: `PlaneParser.parse()` in `src/plane_parser.py`
    - Input: `data/sample_planes.csv` (4 mixed triangle/trapezoid rows; line 4 has a `4.12%` leg diff).
    - Expected Output: Ordered list `[TrianglePlane, TrapezoidPlane, TrianglePlane, TrapezoidPlane]` and 1 warning naming `"Row 4"`.
    """
    parser = PlaneParser()
    planes, warnings = parser.parse("data/sample_planes.csv")

    assert len(planes) == 4
    assert isinstance(planes[0], TrianglePlane)
    assert isinstance(planes[1], TrapezoidPlane)
    assert isinstance(planes[2], TrianglePlane)
    assert isinstance(planes[3], TrapezoidPlane)

    # Line 4 (3rd data row) has ~4.12% leg difference -> emits 1 warning
    assert len(warnings) == 1
    assert "Row 4" in warnings[0]


def test_skip_blank_lines_and_header(tmp_path: Path) -> None:
    """Verify blank lines and the header line are skipped while preserving 1-based line numbers.

    - Sent to: `PlaneParser.parse()` in `src/plane_parser.py`
    - Input: CSV file with empty lines and a header row before 1 valid triangle on line 4.
    - Expected Output: Returns 1 `TrianglePlane` with `row_index == 4` and `warnings == []`.
    """
    csv_content = (
        "\n"
        "Number of Point,x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4\n"
        "\n"
        "3,10,10,0,0,10,20,20,10,20,,,\n"
    )
    path = tmp_path / "with_blanks.csv"
    path.write_text(csv_content, encoding="utf-8")

    planes, warnings = PlaneParser().parse(path)
    assert len(planes) == 1
    assert warnings == []
    assert planes[0].row_index == 4


def test_reject_wrong_column_count(tmp_path: Path) -> None:
    """Abort with PlaneError naming the row number if a row does not have 13 columns (FR-3, FR-4).

    - Sent to: `PlaneParser._parse_row()` via `parse()` in `src/plane_parser.py`
    - Input: CSV file where line 2 has 10 columns instead of 13.
    - Expected Output: Raises `PlaneError` (`exit_code == 2`, `row_index == 2`).
    """
    path = tmp_path / "bad_cols.csv"
    path.write_text(
        "Number of Point,x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4\n"
        "3,10,10,0,0,10,20,20,10,20\n",
        encoding="utf-8",
    )
    with pytest.raises(PlaneError) as exc_info:
        PlaneParser().parse(path)
    assert exc_info.value.row_index == 2
    assert exc_info.value.exit_code == 2


def test_reject_point_count_mismatch_on_triangle_row(tmp_path: Path) -> None:
    """Abort if column 1 is 3 but the 4th point columns are non-empty (FR-3, FR-4).

    - Sent to: `PlaneParser._parse_row()` via `parse()` in `src/plane_parser.py`
    - Input: CSV row on line 2 with point count `3` (triangle) and extra numbers in columns 11–13.
    - Expected Output: Raises `PlaneError` (`exit_code == 2`, `row_index == 2`).
    """
    path = tmp_path / "mismatch_tri.csv"
    path.write_text(
        "Number of Point,x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4\n"
        "3,10,10,0,0,10,20,20,10,20,1,2,3\n",
        encoding="utf-8",
    )
    with pytest.raises(PlaneError) as exc_info:
        PlaneParser().parse(path)
    assert exc_info.value.row_index == 2


def test_reject_missing_fourth_point_on_trapezoid_row(tmp_path: Path) -> None:
    """Abort if column 1 is 4 but the 4th point cells are empty (FR-3, FR-4).

    - Sent to: `PlaneParser._parse_floats()` via `parse()` in `src/plane_parser.py`
    - Input: CSV row on line 2 with point count `4` (trapezoid) and empty columns 11–13.
    - Expected Output: Raises `PlaneError` (`exit_code == 2`, `row_index == 2`).
    """
    path = tmp_path / "mismatch_trap.csv"
    path.write_text(
        "Number of Point,x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4\n"
        "4,200,0,0,200,0,500,200,400,0,,,\n",
        encoding="utf-8",
    )
    with pytest.raises(PlaneError) as exc_info:
        PlaneParser().parse(path)
    assert exc_info.value.row_index == 2


def test_reject_non_numeric_coordinate(tmp_path: Path) -> None:
    """Abort if any coordinate cell contains non-numeric text (FR-4).

    - Sent to: `PlaneParser._parse_floats()` via `parse()` in `src/plane_parser.py`
    - Input: CSV row on line 2 containing `"abc"` instead of a coordinate number.
    - Expected Output: Raises `PlaneError` (`exit_code == 2`, `row_index == 2`).
    """
    path = tmp_path / "nan_cell.csv"
    path.write_text(
        "Number of Point,x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4\n"
        "3,10,abc,0,0,10,20,20,10,20,,,\n",
        encoding="utf-8",
    )
    with pytest.raises(PlaneError) as exc_info:
        PlaneParser().parse(path)
    assert exc_info.value.row_index == 2


def test_reject_empty_csv_file(tmp_path: Path) -> None:
    """Abort if the CSV has only a header and no plane rows (FR-4).

    - Sent to: `PlaneParser.parse()` in `src/plane_parser.py`
    - Input: CSV file containing only the text header and zero plane rows.
    - Expected Output: Raises `PlaneError` (`exit_code == 2`).
    """
    path = tmp_path / "header_only.csv"
    path.write_text("Number of Point,x1,y1,z1,x2,y2,z2,x3,y3,z3,x4,y4,z4\n", encoding="utf-8")
    with pytest.raises(PlaneError) as exc_info:
        PlaneParser().parse(path)
    assert exc_info.value.exit_code == 2
