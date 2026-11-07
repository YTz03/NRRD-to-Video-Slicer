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

Below is a plain-English walkthrough of **what goes into each test, what it does, and when it passes**, followed by the complete traceability table (`TC-01`–`TC-15`).

### 2.1 File-by-File Test Walkthrough

#### A. 3D Scan Loading (`tests/test_volume_data.py` — `TC-01` to `TC-03`)
* **`TC-01` (`test_load_valid_uint8_volume`, `test_load_valid_uint16_and_uint32_volumes`):**
  * **Feeds in:** Valid `uint8`, `uint16` (`vmax=4000`), and `uint32` (`vmax=100000`) `.nrrd` files.
  * **Does:** Loads each file with `VolumeData` and tries to overwrite `vol.matrix[0, 0, 0] = 99`.
  * **Passes if:** Shape, dtype, voxel positions, and `vmax` match 100%, and modifying `vol.matrix` raises `ValueError` (proving it is read-only).
* **`TC-02` (`test_promote_non_negative_signed_integer_volumes`):**
  * **Feeds in:** A signed `int16` `.nrrd` scan with values `0..279`.
  * **Passes if:** `VolumeData` promotes it cleanly to `uint16` with `vmax == 279`.
* **`TC-03` (`test_reject_non_3d_volume`, `test_reject_dimension_exceeding_1023`, `test_reject_signed_or_float_dtypes`, `test_reject_corrupted_nrrd_file`):**
  * **Feeds in:** A 2D image, a `1024×2×2` scan, negative `int16`/`int32` scans, `float32`/`float64` scans, and a fake text file.
  * **Passes if:** Every bad file raises `VolumeError` with `exit_code == 2`.

#### B. Shape Geometry & Tolerances (`tests/test_plane_geometry.py` — `TC-04` to `TC-05`)
* **`TC-04` (`test_triangle_plane_four_corner_interface_and_dimensions`, `test_trapezoid_plane_four_corner_interface_and_longer_base`):**
  * **Feeds in:** Known 3D coordinates for a triangle and a trapezoid (top base `300`, bottom base `400`).
  * **Passes if:** Triangle maps `top_left == top_right == a` with rounded pixel size `(447, 400)`; trapezoid picks the wider base (`400`) and rounds to `(502, 400)` with zero warnings.
* **`TC-05` (`test_leg_difference_*`, `test_trapezoid_coplanarity_warning_and_abort`, `test_degenerate_coinciding_points_raise_plane_error`):**
  * **Feeds in:** Shapes with `0.79%`, `4.12%`, and `16.67%` leg differences; trapezoids bent out of plane by `5%` and `25%`; and coinciding/collinear points.
  * **Passes if:** `<= 1%` gives no warnings; `1%–10%` returns a warning naming the row number; `> 10%` or zero-area points raise `PlaneError` (`exit_code == 2`) without dividing by zero.

#### C. CSV Trajectory Reader (`tests/test_plane_parser.py` — `TC-06` to `TC-07`)
* **`TC-06` (`test_parse_professor_sample_csv`, `test_skip_blank_lines_and_header`):**
  * **Feeds in:** `data/sample_planes.csv` and a CSV containing blank lines and a header row.
  * **Passes if:** Builds the exact ordered list of `TrianglePlane` and `TrapezoidPlane` objects, skips blank/header lines while keeping accurate 1-based line numbers, and catches the `Row 4` warning.
* **`TC-07` (`test_reject_wrong_column_count`, `test_reject_point_count_mismatch_*`, `test_reject_missing_fourth_point_*`, `test_reject_non_numeric_coordinate`, `test_reject_empty_csv_file`):**
  * **Feeds in:** 10-column CSV, `3`-point row with 4th-point numbers, `4`-point row missing 4th-point numbers, `"abc"` coordinate text, and header-only CSV.
  * **Passes if:** Raises `PlaneError` (`exit_code == 2`) with the exact offending `row_index`.

#### D. 3D-to-2D Slicing Math (`tests/test_projection_engine.py` — `TC-08` to `TC-09`)
* **`TC-08` (`test_vectorized_matches_sequential_reference_triangle`, `test_vectorized_matches_sequential_reference_trapezoid`):**
  * **Feeds in:** The `32×32×32` `analytical_volume_uint8` cube and angled `TrianglePlane` / `TrapezoidPlane` objects.
  * **Does:** Runs both the fast vectorized `ProjectionEngine.project()` and the simple nested-loop `_sequential_reference_project()`.
  * **Passes if:** Both output 2D images match pixel-for-pixel, and corners outside the triangle's edges are `0`.
* **`TC-09` (`test_out_of_volume_coordinates_masked_to_zero`):**
  * **Feeds in:** A `16×16×16` cube filled with `200`, sliced once completely in negative space `(-20..-40)` and once halfway across the boundary.
  * **Passes if:** Exterior slice is all `0`s (no crash), and partial slice has `200` inside the cube and `0` outside.

#### E. Brightness Scaling, Padding & MP4 Writer (`tests/test_video_exporter.py` — `TC-10` to `TC-11`)
* **`TC-10` (`test_normalize_frame_uint8_unchanged`, `test_normalize_frame_uint16_and_uint32_global_vmax`, `test_pad_frame_centers_with_black_border`):**
  * **Feeds in:** `uint8`, `uint16` (`[0, 500, 1000]`, `vmax=1000`), `uint32`, and all-zero slices; plus a `2×4` white slice padded onto a `6×8` canvas.
  * **Passes if:** `uint8` is unchanged, `16/32-bit` scales to `[0, 128, 255]`, `vmax=0` stays `0`, and the `2×4` slice lands dead-center at rows `2..3`, cols `2..5` surrounded by black `0`s.
* **`TC-11` (`test_video_exporter_writes_readable_mp4_stream`):**
  * **Feeds in:** Two `uint16` frames of different sizes (`20×30` and `40×50`).
  * **Does:** Writes `out.mp4` via `with VideoExporter(...)` and re-opens it with `cv2.VideoCapture`.
  * **Passes if:** File opens cleanly with `2` frames, size `40×50`, and `30.0 FPS`.

#### F. End-to-End CLI & Speed Benchmark (`tests/test_cli_demo.py`, `tests/test_benchmark_fps.py` — `TC-12` to `TC-15`)
* **`TC-12` (`test_cli_valid_demo_run_end_to_end`):** Runs `python Ex0.py <nrrd> <csv> <mp4>` in a subprocess → checks exit code `0`, `Warning` on `stderr`, and 4-frame `30 FPS` `.mp4` output.
* **`TC-13` (`test_cli_exit_code_1_on_bad_arguments_or_missing_files`):** Feeds missing args, `.avi` extension, and missing `.nrrd` → checks exit code `1`.
* **`TC-14` (`test_cli_exit_code_2_on_bad_csv_row_creates_no_video`):** Feeds a CSV whose 2nd plane has a `50%` leg mismatch → checks exit code `2` and confirms **no** `.mp4` file was created.
* **`TC-15` (`test_500_cubed_projection_fps_benchmark`):** Slices a $500^3$ `uint8` cube (`500×500` plane) for 1 warm-up + 3 timed runs of 30 frames → checks `median_fps >= 30.0`.

---

### 2.2 Master STD Summary Table (`TC-01`–`TC-15`)

| TC ID | Automated Test Function(s) | Verifies | Input Data | What It Checks | Status |
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
