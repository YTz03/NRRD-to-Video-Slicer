# Software Test Plan (STP) & Test Descriptions (STD)
**Project:** High-Performance 3D Volumetric Plane Projection (`Ex0.py`)

---

## 1. Software Test Plan (STP)

> **Big Picture:** Instead of only checking the final `.mp4` video by eye, our `pytest` suite automatically tests the program in **three layers**: (1) testing each class on its own using tiny, predictable fake 3D cubes, (2) running the full `python Ex0.py ...` CLI command and inspecting the generated `.mp4` video with OpenCV, and (3) timing a full-size $500^3$ cube to prove slicing runs fast ($\ge 30\text{ FPS}$ required, $\ge 100\text{ FPS}$ target).

### 1.1 Scope & Items Under Test
This plan verifies every functional requirement (`FR-1`–`FR-9`), non-functional requirement (`NFR-1`–`NFR-5`), and use case (`UC-01`–`UC-04`) in [SRS.md](SRS.md), covering `Ex0.py` and all six modules in `src/` ([SDD.md](SDD.md), [EDD.md](EDD.md)).

### 1.2 Three Levels of Testing
1. **Unit Tests (`test_volume_data.py`, `test_plane_geometry.py`, `test_plane_parser.py`, `test_projection_engine.py`, `test_video_exporter.py`):** Test each class completely on its own using small in-memory arrays and temporary files (`tmp_path`) so bugs are pinpointed immediately.
2. **End-to-End CLI Tests (`test_cli_demo.py`):** Run `python Ex0.py <file.nrrd> <file.csv> <file.mp4>` like a real user, open the output `.mp4` with `cv2.VideoCapture` to verify frame count, resolution, and `30.0 FPS`, and confirm bad inputs return exit code `1` or `2` with **no leftover partial video**.
3. **Speed Benchmarks (`test_benchmark_fps.py`, `src/run_experiment.py`):** Slice a $500 \times 500 \times 500$ `uint8` scan repeatedly (1 warm-up pass + 3 timed runs) to measure pure slicing FPS (`NFR-1`) as well as end-to-end runtime across the classroom dataset ([../results/EXPERIMENT.md](../results/EXPERIMENT.md)).

### 1.3 Smart Testing Tricks & Tools
* **Test Runner:** `pytest` (configured in `pytest.ini` — run all 35 tests anytime with `pytest -v`).
* **Axis-Swap Trap (`analytical_volume_uint8`):** Test cubes fill every voxel with the formula `M[x, y, z] = (x + 2*y + 3*z) % 256`. Because `x`, `y`, and `z` use different multipliers (`1`, `2`, `3`), if the code ever mixed up axes (such as `M[z, y, x]`), pixel checks would fail immediately.
* **Slow-Loop vs. Fast-NumPy Comparison (`_sequential_reference_project`):** `test_projection_engine.py` includes a simple, easy-to-read nested `for`-loop version of the slicing math and checks that the fast vectorized `ProjectionEngine.project()` produces the **exact same pixels** on angled triangles and trapezoids.
* **Automatic Video Inspection (`cv2.VideoCapture`):** Tests re-open saved `.mp4` files with OpenCV to check `FRAME_COUNT`, `FRAME_HEIGHT`, `FRAME_WIDTH`, and `FPS` automatically—no manual watching needed.

### 1.4 Test Environment & Dataset Specification

#### A. Shared Classroom Dataset (`data/` — Real Scans & Sweep Files)
Real 3D `.nrrd` scans paired with 13-column `.csv` plane lists:

| File | Voxel Type | Size ($sx, sy, sz$) | What It Tests |
|---|---|---|---|
| `data/croissant.nrrd` | `uint8` | `(500, 500, 500)` | Full-scale $500^3$ speed benchmark (`NFR-1`) paired with `croissant_sweep.csv`. |
| `data/onion.nrrd` | `uint8` | `(256, 256, 130)` | Layered structure for checking clean oblique cross-sections (`FR-5`). |
| `data/biscuit_cake.nrrd` | `uint16` | `(256, 256, 130)` | 16-bit scan ($v_{\max}=3986$) testing global `vmax` scaling to `0..255` (`FR-8`). |
| `data/swiss_roll.nrrd` | `uint32` | `(256, 256, 130)` | 32-bit scan ($v_{\max}=186330$) testing 32-to-8-bit scaling (`FR-8`). |
| `data/MRHead_1.nrrd` | `int16` $\ge 0$ $\to$ `uint16` | `(256, 256, 130)` | 3D Slicer MRI head scan ($v_{\max}=279$) testing non-negative signed promotion (`FR-2`). |
| `data/sample_planes.csv` | 4 rows (`3` & `4` pts) | Heights $447\text{–}502$, Width $400$ | Tests mixed triangles/trapezoids, negative out-of-bounds coords (`FR-6`), and a $4.12\%$ warning row (`FR-4`). |
| `data/croissant_sweep.csv` | 60 rows (30 trap + 30 tri) | Max canvas `514 × 500` | Smooth 60-frame sweep producing `results/demo_output.mp4`. |
| `data/mrhead_planes.csv` | 135 rows | Anatomical sweep | Long trajectory verifying flat $O(1)$ frame memory (`NFR-2`). |

#### B. Synthetic & Boundary Datasets (`tests/conftest.py` — Shared Pytest Fixtures)
Generated automatically in temporary folders (`tmp_path`) so unit tests run anywhere with zero external setup:
* `analytical_volume_uint8`: `32×32×32` `uint8` cube where `M[x, y, z] = (x + 2*y + 3*z) % 256` (catches any axis/coordinate mistake).
* `nrrd_uint8_path`, `nrrd_uint16_path` (`vmax=4000`), `nrrd_uint32_path` (`vmax=100000`): Temporary `.nrrd` files testing bit-depth loading and brightness scaling (`FR-2`, `FR-8`).
* `sample_csv_path`: Temporary 4-row, 13-column `.csv` mixing triangles (`3`) and trapezoids (`4`), out-of-bounds coordinates, and a `1%–10%` warning row.
* **Bad-Input Fixtures (created inside negative tests):** 2D NRRDs, `1024×2×2` oversized NRRDs, negative `int16`/`int32` and `float32`/`float64` NRRDs, corrupt text headers, and malformed CSV rows (wrong column counts, `"abc"` text, $>10\%$ geometry errors, collinear points).

### 1.5 Entry & Exit Criteria
* **Entry Criteria:** All modules in `src/` implement the interfaces in [SDD.md](SDD.md); fixtures in `tests/conftest.py` and `data/` are available.
* **Exit Criteria:** All 15 test cases (`TC-01`–`TC-15`, 35 `pytest` items) pass; $500^3$ benchmark achieves $\ge 30\text{ FPS}$ ($\ge 100\text{ FPS}$ target) on Python 3.10+; zero unhandled Python tracebacks on bad inputs.

### 1.6 Schedule, Roles & Risk Register
* **Review Gates:**
  1. *SRR (Requirements):* Baseline `SRS.md` & requirement-to-test links.
  2. *PDR / CDR (Design):* Baseline `SDD.md`, `EDD.md`, and `TC-01..15` in `STP.md`.
  3. *TRR & Final Demo:* Run full `pytest` suite and `src/run_experiment.py` across all classroom scans.
* **Five Key Risks & How We Test Them:**

| Risk ID | What Could Go Wrong | Likelihood | Impact | How We Prevent & Test It |
|---|---|---|---|---|
| **R-01** | Python `for` loops are ~100× too slow for $500^3$ scans (`NFR-1`). | High | High | Use 2D `NumPy` array broadcasting in `ProjectionEngine.project()` (`ADR-01`, tested in `TC-15`). |
| **R-02** | Real MRI scans (`MRHead_1.nrrd`) save non-negative voxels as signed `int16` (`short`). | High | Med | Check `min(M) >= 0` in `VolumeData` and promote non-negative signed integers to unsigned (`FR-2`, tested in `TC-02`). |
| **R-03** | Classroom CSV rows have slight `1%–10%` leg length differences (e.g., Row 3 of `sample_planes.csv` is `4.12%`). | Med | High | Use 3-tier tolerances ($\le 1\%$ silent, $1\text{–}10\%$ warn, $>10\%$ abort) and fractional $t \in (0,1]$ stepping (`FR-4`, tested in `TC-05`, `TC-06`). |
| **R-04** | OpenCV `mp4v` produces unplayable videos on some systems if given 1-channel 2D arrays. | Med | Med | Convert 2D `uint8` slices to 3-channel BGR before writing and re-open the `.mp4` with `cv2.VideoCapture` (`TC-11`, `TC-12`). |
| **R-05** | Crashing mid-run leaves a broken, half-written `.mp4` file on disk. | Low | High | Validate all CSV rows up front and wrap `VideoExporter` in a `with` block whose `__exit__` deletes partial `.mp4` files (`TC-14`). |

---

## 2. Software Test Descriptions (STD)

Every test function in `tests/` is listed below in simple terms: **what part of the code it checks**, **what goes in**, and **what is expected to come out**.

### 2.1 Test-by-Test Reference (`Sent to` / `Input` / `Expected Output`)

#### A. `tests/test_volume_data.py` — Checks `VolumeData` (`src/volume_data.py`)

* **`test_load_valid_uint8_volume`** (`TC-01`)
  * **Sent to:** `VolumeData(file_path)` in `src/volume_data.py`
  * **Input:** Valid `32×32×32` 8-bit (`uint8`) `.nrrd` file.
  * **Expected Output:** Exact `32×32×32` `(x, y, z)` array, accurate `vmax`, and read-only lock (changing a pixel raises `ValueError`).
* **`test_load_valid_uint16_and_uint32_volumes`** (`TC-01`)
  * **Sent to:** `VolumeData(file_path)` in `src/volume_data.py`
  * **Input:** Valid `uint16` (max `4000`) and `uint32` (max `100000`) `.nrrd` files.
  * **Expected Output:** Exact shapes and types loaded with `vmax == 4000` and `vmax == 100000`.
* **`test_promote_non_negative_signed_integer_volumes`** (`TC-02`)
  * **Sent to:** `VolumeData._validate_matrix()` in `src/volume_data.py`
  * **Input:** Signed `int16` `.nrrd` file whose values are all `>= 0` (`0..279`).
  * **Expected Output:** Promoted to unsigned `uint16` with `vmax == 279` and read-only lock.
* **`test_reject_non_3d_volume`** (`TC-03`)
  * **Sent to:** `VolumeData._validate_matrix()` in `src/volume_data.py`
  * **Input:** A 2D (`32×32`) `.nrrd` file instead of a 3D cube.
  * **Expected Output:** Raises `VolumeError` (`exit_code == 2`).
* **`test_reject_dimension_exceeding_1023`** (`TC-03`)
  * **Sent to:** `VolumeData._validate_matrix()` in `src/volume_data.py`
  * **Input:** Oversized `1024×2×2` `.nrrd` file.
  * **Expected Output:** Raises `VolumeError` (`exit_code == 2`).
* **`test_reject_signed_or_float_dtypes`** (`TC-03`)
  * **Sent to:** `VolumeData._validate_matrix()` in `src/volume_data.py`
  * **Input:** `8×8×8` `.nrrd` files filled with `-1` using `int16`, `int32`, `float32`, and `float64`.
  * **Expected Output:** Raises `VolumeError` (`exit_code == 2`) for every unsupported type.
* **`test_reject_corrupted_nrrd_file`** (`TC-03`)
  * **Sent to:** `VolumeData._load_nrrd()` in `src/volume_data.py`
  * **Input:** Plain text file (`"NOT A VALID NRRD HEADER"`) saved as `.nrrd`.
  * **Expected Output:** Raises `VolumeError` (`exit_code == 2`).

---

#### B. `tests/test_plane_geometry.py` — Checks `Plane`, `TrianglePlane`, `TrapezoidPlane` (`src/plane.py`)

* **`test_triangle_plane_four_corner_interface_and_dimensions`** (`TC-04`)
  * **Sent to:** `TrianglePlane` & `Plane.validate()` in `src/plane.py`
  * **Input:** 3 points forming an isosceles triangle (`a=(200,200,0)`, `b=(0,200,400)`, `c=(400,200,400)`).
  * **Expected Output:** `top_left == top_right == a`, `height == 447`, `width == 400`, and `warnings == []`.
* **`test_trapezoid_plane_four_corner_interface_and_longer_base`** (`TC-04`)
  * **Sent to:** `TrapezoidPlane` & `Plane.validate()` in `src/plane.py`
  * **Input:** 4 points forming a flat trapezoid (top width `300`, bottom width `400`, legs `502.49`).
  * **Expected Output:** Maps all 4 corners, picks wider base (`width == 400`), `height == 502`, and `warnings == []`.
* **`test_leg_difference_within_1_percent_accepted_silently`** (`TC-05`)
  * **Sent to:** `Plane.validate()` in `src/plane.py`
  * **Input:** Triangle with legs `100.0` and `100.8` (`0.79%` difference, `<= 1%`).
  * **Expected Output:** `warnings == []` (accepted silently).
* **`test_leg_difference_between_1_and_10_percent_emits_warning`** (`TC-05`)
  * **Sent to:** `Plane.validate()` in `src/plane.py`
  * **Input:** Triangle on `row_index=4` with a `4.12%` leg difference (`1% < diff <= 10%`).
  * **Expected Output:** Returns 1 warning string naming `"Row 4"` and sets `height` from the longer leg.
* **`test_leg_difference_above_10_percent_raises_plane_error`** (`TC-05`)
  * **Sent to:** `Plane.validate()` in `src/plane.py`
  * **Input:** Triangle on `row_index=7` with legs `100` and `120` (`16.67%` difference, `> 10%`).
  * **Expected Output:** Raises `PlaneError` (`exit_code == 2`, `row_index == 7`).
* **`test_trapezoid_coplanarity_warning_and_abort`** (`TC-05`)
  * **Sent to:** `TrapezoidPlane._validate_shape_specific()` in `src/plane.py`
  * **Input:** Two trapezoids with the 4th corner bent out of plane by `5%` (`row_index=3`) and `~25%` (`row_index=8`).
  * **Expected Output:** `5%` returns a coplanarity warning; `~25%` raises `PlaneError` (`exit_code == 2`, `row_index == 8`).
* **`test_degenerate_coinciding_points_raise_plane_error`** (`TC-05`)
  * **Sent to:** `Plane.validate()` & `TrianglePlane._validate_shape_specific()` in `src/plane.py`
  * **Input:** 3 identical points `(10,10,10)` and 3 points lying on the same straight line.
  * **Expected Output:** Both raise `PlaneError` (`exit_code == 2`) without dividing by zero.

---

#### C. `tests/test_plane_parser.py` — Checks `PlaneParser` (`src/plane_parser.py`)

* **`test_parse_professor_sample_csv`** (`TC-06`)
  * **Sent to:** `PlaneParser.parse()` in `src/plane_parser.py`
  * **Input:** `data/sample_planes.csv` (4 mixed triangle/trapezoid rows; line 4 has a `4.12%` leg diff).
  * **Expected Output:** Ordered list `[TrianglePlane, TrapezoidPlane, TrianglePlane, TrapezoidPlane]` and 1 warning naming `"Row 4"`.
* **`test_skip_blank_lines_and_header`** (`TC-06`)
  * **Sent to:** `PlaneParser.parse()` in `src/plane_parser.py`
  * **Input:** CSV file with empty lines and a header row before 1 valid triangle on line 4.
  * **Expected Output:** Returns 1 `TrianglePlane` with `row_index == 4` and `warnings == []`.
* **`test_reject_wrong_column_count`** (`TC-07`)
  * **Sent to:** `PlaneParser._parse_row()` in `src/plane_parser.py`
  * **Input:** CSV file where line 2 has 10 columns instead of 13.
  * **Expected Output:** Raises `PlaneError` (`exit_code == 2`, `row_index == 2`).
* **`test_reject_point_count_mismatch_on_triangle_row`** (`TC-07`)
  * **Sent to:** `PlaneParser._parse_row()` in `src/plane_parser.py`
  * **Input:** CSV row on line 2 with point count `3` (triangle) and extra numbers in columns 11–13.
  * **Expected Output:** Raises `PlaneError` (`exit_code == 2`, `row_index == 2`).
* **`test_reject_missing_fourth_point_on_trapezoid_row`** (`TC-07`)
  * **Sent to:** `PlaneParser._parse_floats()` in `src/plane_parser.py`
  * **Input:** CSV row on line 2 with point count `4` (trapezoid) and empty columns 11–13.
  * **Expected Output:** Raises `PlaneError` (`exit_code == 2`, `row_index == 2`).
* **`test_reject_non_numeric_coordinate`** (`TC-07`)
  * **Sent to:** `PlaneParser._parse_floats()` in `src/plane_parser.py`
  * **Input:** CSV row on line 2 containing `"abc"` instead of a coordinate number.
  * **Expected Output:** Raises `PlaneError` (`exit_code == 2`, `row_index == 2`).
* **`test_reject_empty_csv_file`** (`TC-07`)
  * **Sent to:** `PlaneParser.parse()` in `src/plane_parser.py`
  * **Input:** CSV file containing only the text header and zero plane rows.
  * **Expected Output:** Raises `PlaneError` (`exit_code == 2`).

---

#### D. `tests/test_projection_engine.py` — Checks `ProjectionEngine` (`src/projection_engine.py`)

* **`test_vectorized_matches_sequential_reference_triangle`** (`TC-08`)
  * **Sent to:** `ProjectionEngine.project(volume, plane)` in `src/projection_engine.py`
  * **Input:** `32×32×32` `uint8` analytical cube and an angled `TrianglePlane`.
  * **Expected Output:** 2D `uint8` slice matching the simple `for`-loop reference pixel-for-pixel, with `0` in top corners outside the triangle.
* **`test_vectorized_matches_sequential_reference_trapezoid`** (`TC-08`)
  * **Sent to:** `ProjectionEngine.project(volume, plane)` in `src/projection_engine.py`
  * **Input:** `32×32×32` `uint8` analytical cube and an angled `TrapezoidPlane`.
  * **Expected Output:** 2D `uint8` slice matching the simple `for`-loop reference pixel-for-pixel.
* **`test_out_of_volume_coordinates_masked_to_zero`** (`TC-09`)
  * **Sent to:** `ProjectionEngine.project(volume, plane)` in `src/projection_engine.py`
  * **Input:** `16×16×16` cube filled with `200`, sliced by one negative-space triangle and one half-inside triangle.
  * **Expected Output:** Outside slice is all `0`s (no crash); half-inside slice has `200` inside and `0` outside.

---

#### E. `tests/test_video_exporter.py` — Checks `VideoExporter` (`src/video_exporter.py`)

* **`test_normalize_frame_uint8_unchanged`** (`TC-10`)
  * **Sent to:** `VideoExporter.normalize_frame(frame, vmax)` in `src/video_exporter.py`
  * **Input:** 2D `uint8` array `[[0, 50, 200]]` and `vmax=200`.
  * **Expected Output:** Exact same `uint8` array `[[0, 50, 200]]` without rescaling.
* **`test_normalize_frame_uint16_and_uint32_global_vmax`** (`TC-10`)
  * **Sent to:** `VideoExporter.normalize_frame(frame, vmax)` in `src/video_exporter.py`
  * **Input:** `uint16` `[[0, 500, 1000]]` (`vmax=1000`), `uint32` `[[0, 50000, 100000]]` (`vmax=100000`), and all-zeros (`vmax=0`).
  * **Expected Output:** `16/32-bit` arrays scale to `uint8` `[[0, 128, 255]]`; all-zero input returns all `0`s.
* **`test_pad_frame_centers_with_black_border`** (`TC-10`)
  * **Sent to:** `VideoExporter.pad_frame(frame, canvas_height, canvas_width)` in `src/video_exporter.py`
  * **Input:** Small `2×4` white (`255`) array and target canvas `6×8`.
  * **Expected Output:** `6×8` `uint8` array with the `2×4` white rectangle centered at rows `2..3`, cols `2..5` and `0` borders.
* **`test_video_exporter_writes_readable_mp4_stream`** (`TC-11`)
  * **Sent to:** `VideoExporter` (`open`, `write_frame`, `close`) in `src/video_exporter.py`
  * **Input:** Two `uint16` frames (`20×30` and `40×50`) with `canvas=(40, 50)` and `vmax=1000`.
  * **Expected Output:** Non-empty `out.mp4` file that opens in OpenCV with `2` frames, size `40×50`, and `30.0 FPS`.

---

#### F. `tests/test_cli_demo.py` & `tests/test_benchmark_fps.py` — Checks `Ex0.py`, `AppController`, & Speed

* **`test_cli_valid_demo_run_end_to_end`** (`TC-12`)
  * **Sent to:** `Ex0.py` CLI subprocess → `AppController.run()` in `src/app_controller.py`
  * **Input:** Valid `uint8` `.nrrd` path, 4-row `planes.csv` path, and output `demo.mp4` path.
  * **Expected Output:** Exit code `0`, warning printed to `stderr`, and playable `demo.mp4` with `4` frames at `30.0 FPS`.
* **`test_cli_exit_code_1_on_bad_arguments_or_missing_files`** (`TC-13`)
  * **Sent to:** `Ex0.main()` → `AppController.validate_cli_args()` in `src/app_controller.py`
  * **Input:** `0` args, `2` args, `.avi` output path instead of `.mp4`, and missing `.nrrd` path.
  * **Expected Output:** Returns exit code `1` for every bad call.
* **`test_cli_exit_code_2_on_bad_csv_row_creates_no_video`** (`TC-14`)
  * **Sent to:** `Ex0.main()` → `AppController.run()` & `PlaneParser.parse()`
  * **Input:** Valid `.nrrd` path and a `.csv` where the 2nd plane has a `50%` leg mismatch (`> 10%`).
  * **Expected Output:** Returns exit code `2` and creates **no** `.mp4` file on disk.
* **`test_500_cubed_projection_fps_benchmark`** (`TC-15`)
  * **Sent to:** `ProjectionEngine.project(volume, plane)` in `src/projection_engine.py`
  * **Input:** `500×500×500` `uint8` cube and a `500×500` `TrianglePlane` (1 warm-up + 3 runs of 30 slices).
  * **Expected Output:** `median_fps >= 30.0` (`<= 33.3 ms` per frame).

---

### 2.2 Master STD Summary Table (`TC-01`–`TC-15`)

| TC ID | Automated Test Function(s) | Verifies | Input Data | Expected Output | Status |
|---|---|---|---|---|---|
| **TC-01** | `test_load_valid_uint8_volume`<br/>`test_load_valid_uint16_and_uint32_volumes` | `FR-2`, `FR-8` | `32³` `uint8`, `16×20×24` `uint16` (`vmax=4000`), `16³` `uint32` (`vmax=100000`) NRRDs. | Exact `(x, y, z)` shape/values, exact `vmax`, and read-only lock (`writeable == False`). | **Pass** |
| **TC-02** | `test_promote_non_negative_signed_integer_volumes` | `FR-2` | `16³` `int16` NRRD with values `0..279`. | Promoted cleanly to `uint16` with `vmax == 279`. | **Pass** |
| **TC-03** | `test_reject_non_3d_volume`<br/>`test_reject_dimension_exceeding_1023`<br/>`test_reject_signed_or_float_dtypes`<br/>`test_reject_corrupted_nrrd_file` | `FR-2`, `NFR-3`, `UC-04` | 2D NRRD, `1024×2×2` NRRD, negative `int16`/`int32` & `float32`/`float64` NRRDs, corrupt text file. | Raises `VolumeError` (`exit_code == 2`) with clear reason. | **Pass** |
| **TC-04** | `test_triangle_plane_four_corner_interface_and_dimensions`<br/>`test_trapezoid_plane_four_corner_interface_and_longer_base` | `FR-4`, `FR-5` | Valid 3D triangle and trapezoid (top `300`, bottom `400`). | Unified 4-corner mapping and rounded sizes `(447, 400)` & `(502, 400)` with 0 warnings. | **Pass** |
| **TC-05** | `test_leg_difference_*`<br/>`test_trapezoid_coplanarity_warning_and_abort`<br/>`test_degenerate_coinciding_points_raise_plane_error` | `FR-4`, `NFR-3`, `UC-02`, `UC-04` | `0.79%`, `4.12%`, `16.67%` leg diffs; `5%` & `25%` bent trapezoids; collinear points. | `<=1%` silent; `1–10%` warns with `Row #`; `>10%` or collinear raises `PlaneError` (`exit_code == 2`). | **Pass** |
| **TC-06** | `test_parse_professor_sample_csv`<br/>`test_skip_blank_lines_and_header` | `FR-3`, `FR-4`, `UC-02` | `data/sample_planes.csv` and CSV with blank lines & header. | Parses mixed `3`/`4`-point planes, skips blanks/header, keeps 1-based line numbers, warns on `Row 4`. | **Pass** |
| **TC-07** | `test_reject_wrong_column_count`<br/>`test_reject_point_count_mismatch_on_triangle_row`<br/>`test_reject_missing_fourth_point_on_trapezoid_row`<br/>`test_reject_non_numeric_coordinate`<br/>`test_reject_empty_csv_file` | `FR-3`, `FR-4`, `NFR-3`, `UC-02`, `UC-04` | 10-col CSV, mismatched 4th-point cells, `"abc"` cell, header-only CSV. | Raises `PlaneError` (`exit_code == 2`) with exact 1-based `row_index`. | **Pass** |
| **TC-08** | `test_vectorized_matches_sequential_reference_triangle`<br/>`test_vectorized_matches_sequential_reference_trapezoid` | `FR-5` | `32³` analytical cube + angled triangle & trapezoid. | Vectorized NumPy output matches nested `for`-loop reference pixel-for-pixel; outside-shape corners are `0`. | **Pass** |
| **TC-09** | `test_out_of_volume_coordinates_masked_to_zero` | `FR-6` | `16³` cube (`200`) + negative/partial planes. | Out-of-bounds coordinates safely produce `0` without crashing. | **Pass** |
| **TC-10** | `test_normalize_frame_uint8_unchanged`<br/>`test_normalize_frame_uint16_and_uint32_global_vmax`<br/>`test_pad_frame_centers_with_black_border` | `FR-7`, `FR-8`, `UC-03` | `uint8`/`uint16`/`uint32`/zero frames; `2×4` frame on `6×8` canvas. | `16/32-bit` maps to `[0, 128, 255]`; `2×4` frame centered on black `6×8` background. | **Pass** |
| **TC-11** | `test_video_exporter_writes_readable_mp4_stream` | `FR-7`, `FR-8`, `FR-9` | `(20, 30)` and `(40, 50)` `uint16` frames (`vmax=1000`). | Saved `.mp4` opens in `cv2.VideoCapture` with 2 frames, `(40, 50)` size, and `30.0 FPS`. | **Pass** |
| **TC-12** | `test_cli_valid_demo_run_end_to_end` | `FR-1`–`FR-9`, `NFR-2`, `UC-01` | Valid NRRD + 4-row `sample_planes.csv` + `demo.mp4`. | `Ex0.py` exits `0`, prints warning to `stderr`, and writes valid 4-frame `30 FPS` `.mp4`. | **Pass** |
| **TC-13** | `test_cli_exit_code_1_on_bad_arguments_or_missing_files` | `FR-1`, `NFR-3`, `UC-01`, `UC-04` | Wrong arg count, `.avi` output, missing `.nrrd`. | Returns exit code `1` cleanly. | **Pass** |
| **TC-14** | `test_cli_exit_code_2_on_bad_csv_row_creates_no_video` | `FR-4`, `NFR-3`, `UC-01`, `UC-02`, `UC-04` | CSV with valid Row 2 and `50%` mismatch on Row 3. | Returns exit code `2` and leaves **no** `.mp4` file on disk. | **Pass** |
| **TC-15** | `test_500_cubed_projection_fps_benchmark` & `src/run_experiment.py` | `NFR-1` | $500^3$ `uint8` cube + `500×500` plane (1 warm-up + 3 runs). | Median FPS $\ge 30.0$ (**435.3 FPS** measured in Python 3.11 container). | **Pass** |
