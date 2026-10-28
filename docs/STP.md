# Software Test Plan (STP) & Test Descriptions (STD)
**Project:** High-Performance 3D Volumetric Plane Projection (`Ex0.py`)

---

## 1. Software Test Plan (STP)

### 1.1 Scope & Items Under Test
This test plan covers the verification and validation of all functional requirements (`FR-1`–`FR-9`), non-functional requirements (`NFR-1`–`NFR-5`), and use cases (`UC-01`–`UC-04`) defined in [SRS.md](SRS.md), across all six modules of the `src/` package ([SDD.md](SDD.md), [EDD.md](EDD.md)) and the `Ex0.py` CLI entry point.

### 1.2 Test Levels
1. **Unit & Component Testing (`tests/test_volume_data.py`, `test_plane_geometry.py`, `test_plane_parser.py`, `test_projection_engine.py`, `test_video_exporter.py`):** Verifies each class in isolation using deterministic in-memory fixtures without external file dependencies.
2. **Integration & System Testing (`tests/test_cli_demo.py`):** Invokes the full `python Ex0.py <file.nrrd> <file.csv> <file.mp4>` CLI pipeline via subprocess and in-process calls, inspecting the encoded `.mp4` stream with `cv2.VideoCapture` and verifying fast-fail exit codes (`1, 2, 3`).
3. **Performance & Throughput Benchmarking (`tests/test_benchmark_fps.py`, `src/run_experiment.py`):** Measures pure projection throughput on a $500^3$ `uint8` volume against the mandatory $\ge 30\text{ FPS}$ floor and $\ge 100\text{ FPS}$ target (`NFR-1`), as well as end-to-end runtime on the classroom dataset ([../results/EXPERIMENT.md](../results/EXPERIMENT.md)).

### 1.3 Test Approach & Tools
* **Test Runner:** `pytest` (configured via `pytest.ini`).
* **Mathematical Reference Equivalence:** `test_projection_engine.py` compares the vectorized `ProjectionEngine.project()` output pixel-for-pixel against a sequential nested-loop scanline reference implementation (`_sequential_reference_project`).
* **Video Stream Inspection:** `cv2.VideoCapture` verifies `CAP_PROP_FRAME_COUNT`, `CAP_PROP_FRAME_HEIGHT`, `CAP_PROP_FRAME_WIDTH`, and `CAP_PROP_FPS`.

### 1.4 Test Environment & Dataset Specification

#### A. Shared Classroom Dataset (`data/` — End-to-End & Visual Verification)
Real-world 3D volumetric `.nrrd` scans paired with 13-column `.csv` trajectory files:

| File | Type / Bit Depth | Dimensions ($sx, sy, sz$) | Purpose in Testing & Demo |
|---|---|---|---|
| `data/croissant.nrrd` | `uint8` | `(500, 500, 500)` | Full-scale $500^3$ benchmark volume (`NFR-1`) paired with `croissant_sweep.csv`. |
| `data/onion.nrrd` | `uint8` | `(256, 256, 130)` | Multi-layer concentric structure for visual slice verification (`FR-5`). |
| `data/biscuit_cake.nrrd` | `uint16` | `(256, 256, 130)` | 16-bit unsigned volume ($v_{\max}=3986$) verifying global `vmax` scaling (`FR-8`). |
| `data/swiss_roll.nrrd` | `uint32` | `(256, 256, 130)` | 32-bit unsigned volume ($v_{\max}=186330$) verifying 32-to-8-bit normalization (`FR-8`). |
| `data/MRHead_1.nrrd` | `int16` $\ge 0$ $\to$ `uint16` | `(256, 256, 130)` | 3D Slicer MRI head scan ($v_{\max}=279$) verifying non-negative signed promotion (`FR-2`). |
| `data/sample_planes.csv` | 4 rows (mixed `3` & `4`) | Heights $447\text{–}502$, Width $400$ | Exercises mixed triangles/trapezoids, negative out-of-volume coords (`FR-6`), and a $4.12\%$ warning row (`FR-4`). |
| `data/croissant_sweep.csv` | 60 rows (30 trap + 30 tri) | Max canvas `514 × 500` | Smooth 60-frame sweep generating `results/demo_output.mp4`. |
| `data/mrhead_planes.csv` | 135 rows | Anatomical sweep | High-frame-count trajectory verifying $O(1)$ frame memory streaming (`NFR-2`). |

#### B. Synthetic & Boundary Datasets (`tests/conftest.py` — Automated Unit Testing)
| Dataset Category | Specification | Purpose |
|---|---|---|
| **Analytical Unit-Test Volumes** | $16^3$ to $32^3$ arrays in `uint8`, `uint16`, `uint32` with closed-form voxel values $M[x, y, z] = (x + 2y + 3z) \bmod 256$. | Verify pixel-exact projection (`FR-5`), axis ordering (`FR-2`), and `vmax` scaling (`FR-8`). |
| **500³ Benchmark Volume** | $500 \times 500 \times 500$ `uint8` volume ($125\text{ MB}$) with $500 \times 500$ isosceles triangle planes. | Measure pure projection FPS over 3 runs of 30 frames after 1 warm-up pass (`NFR-1`). |
| **Invalid & Boundary Fixtures** | 2D NRRD, $1024 \times 2 \times 2$ NRRD, negative `int16`/`float32` NRRDs, corrupt headers, CSVs with wrong column counts, $\delta > 10\%$, non-coplanar trapezoids, and coinciding points. | Verify fast-fail error messages, zero partial MP4 files, and exit codes `1, 2, 3` (`FR-1`, `FR-2`, `FR-4`, `NFR-3`). |

### 1.5 Entry & Exit Criteria
* **Entry Criteria:** Source modules in `src/` implement all interfaces in [SDD.md](SDD.md); test fixtures in `tests/conftest.py` and `data/` are present.
* **Exit Criteria:** 100% of unit, integration, and CLI demo test cases (`TC-01`–`TC-15`) pass; $500^3$ benchmark achieves $\ge 30\text{ FPS}$ mandatory ($\ge 100\text{ FPS}$ target); zero unhandled exceptions on negative test cases.

### 1.6 Schedule, Roles & Risk Register
* **Schedule & Review Gates:**
  1. *SRR (Requirements Gate):* Baseline `SRS.md` & test traceability.
  2. *PDR / CDR (Design Gates):* Baseline `SDD.md`, `EDD.md`, and `STP.md` test descriptions (`TC-01..15`).
  3. *TRR & Final Demo Gate:* Execute full `pytest` suite and `src/run_experiment.py` across all 5 classroom NRRD volumes.
* **Risk Register & Mitigation Matrix:**

| Risk ID | Risk Description | Probability | Impact | Mitigation Strategy |
|---|---|---|---|---|
| **R-01** | Pure Python nested loops fail the $\ge 30\text{ FPS}$ / $\ge 100\text{ FPS}$ requirement on $500^3$ volumes (`NFR-1`). | High | High | Vectorize `ProjectionEngine.project()` using 2D `NumPy` broadcasting (`ADR-01`, verified by `TC-15`). |
| **R-02** | Real-world MRI NRRD files (`MRHead_1.nrrd`) store non-negative voxels as signed `int16` (`short`) rather than `uint16`. | High | Med | Inspect `min(M) >= 0` in `VolumeData` and promote non-negative signed integer volumes to unsigned (`FR-2`, verified by `TC-02`). |
| **R-03** | Classroom CSV rows contain slight floating-point or human-authored leg discrepancies ($1\%\text{–}10\%$, e.g., Row 3 of `sample_planes.csv`). | Med | High | Use 3-tier tolerance ($\le 1\%$ silent, $1\text{–}10\%$ warning, $>10\%$ abort) and fractional $t \in (0,1]$ leg stepping (`FR-4`, `TC-05`, `TC-06`). |
| **R-04** | OpenCV `mp4v` writer produces unreadable files on some OS codecs when fed single-channel 2D grayscale arrays. | Med | Med | Convert 2D `uint8` canvas to 3-channel BGR via `cv2.cvtColor(..., COLOR_GRAY2BGR)` and verify with `cv2.VideoCapture` (`TC-11`, `TC-12`). |
| **R-05** | Mid-stream exception leaves a corrupted partial `.mp4` file on disk. | Low | High | Wrap `VideoExporter` in a context manager whose `__exit__` unlinks the output file on any exception (`TC-14`). |

---

## 2. Software Test Descriptions (STD)

Each test case below follows the course STD standard and maps directly to an automated test in `tests/`.

| TC ID | Title & Automated Test Function | Verifies | Preconditions & Input Data | Action Steps | Expected Result | Status |
|---|---|---|---|---|---|---|
| **TC-01** | **Load Valid `uint8`, `uint16`, `uint32` Volumes**<br/>`test_load_valid_uint8_volume`<br/>`test_load_valid_uint16_and_uint32_volumes` | `FR-2`, `FR-8` | Synthetic `32x32x32` `uint8`, `16x20x24` `uint16` ($v_{\max}=4000$), and `16x16x16` `uint32` ($v_{\max}=100000$) NRRD files. | Instantiate `VolumeData(path)` and attempt to mutate `vol.matrix[0,0,0]`. | Shapes and dtypes match; `vmax` equals exact maximum; `matrix.flags.writeable` is `False` (mutation raises `ValueError`). | **Pass** |
| **TC-02** | **Promote Non-Negative Signed Integer NRRDs**<br/>`test_promote_non_negative_signed_integer_volumes` | `FR-2` | `16x16x16` `int16` NRRD file with values in $[0, 279]$. | Instantiate `VolumeData(path)`. | Promoted cleanly to `uint16` with `vmax == 279` and `writeable == False`. | **Pass** |
| **TC-03** | **Reject Invalid NRRD Dimensions, Dtypes & Corrupt Files**<br/>`test_reject_non_3d_volume`<br/>`test_reject_dimension_exceeding_1023`<br/>`test_reject_signed_or_float_dtypes`<br/>`test_reject_corrupted_nrrd_file` | `FR-2`, `NFR-3`, `UC-04` | 2D `(32,32)` NRRD; `(1024,2,2)` NRRD; negative `int16`/`int32` and `float32`/`float64` NRRDs; corrupt text file. | Instantiate `VolumeData(path)` on each invalid fixture. | Raises `VolumeError` with `exit_code == 2` and descriptive message. | **Pass** |
| **TC-04** | **Four-Corner Mapping & Rounded Dimensions for Triangle & Trapezoid**<br/>`test_triangle_plane_four_corner_interface_and_dimensions`<br/>`test_trapezoid_plane_four_corner_interface_and_longer_base` | `FR-4`, `FR-5` | Triangle $a=(200,200,0), b=(0,200,400), c=(400,200,400)$; Trapezoid with top base $300$, bottom base $400$, legs $502.49$. | Instantiate `TrianglePlane` and `TrapezoidPlane` and call `validate()`. | Triangle: `top_left == top_right == a`, $(N, W) = (447, 400)$. Trapezoid: $(N, W) = (502, 400)$. Zero warnings. | **Pass** |
| **TC-05** | **Plane Tolerance Thresholds ($\le 1\%$, $1\text{–}10\%$, $>10\%$) & Degenerate Shapes**<br/>`test_leg_difference_within_1_percent_accepted_silently`<br/>`test_leg_difference_between_1_and_10_percent_emits_warning`<br/>`test_leg_difference_above_10_percent_raises_plane_error`<br/>`test_trapezoid_coplanarity_warning_and_abort`<br/>`test_degenerate_coinciding_points_raise_plane_error` | `FR-4`, `NFR-3`, `UC-02`, `UC-04` | Planes with $\delta = 0.79\%$, $\delta = 4.12\%$, $\delta = 16.67\%$; trapezoids with $5\%$ and $25\%$ coplanarity offset; coinciding/collinear points. | Call `plane.validate()` on each plane. | $\le 1\%$: `warnings == []`; $1\text{–}10\%$: returns warning naming `Row #`; $>10\%$ or collinear/coinciding: raises `PlaneError` (`exit_code == 2`). | **Pass** |
| **TC-06** | **Parse Valid 13-Column CSV with Header, Blanks & Mixed Shapes**<br/>`test_parse_professor_sample_csv`<br/>`test_skip_blank_lines_and_header` | `FR-3`, `FR-4`, `UC-02` | `data/sample_planes.csv` (4 rows: mixed `3` and `4`, row 4 has $4.12\%$ leg diff) and CSV with blank lines. | Call `PlaneParser().parse(path)`. | Returns 4 `Plane` objects (`TrianglePlane`, `TrapezoidPlane`, ...) and 1 warning on `Row 4`; preserves 1-based line numbers. | **Pass** |
| **TC-07** | **Reject Malformed CSV Rows with Exact 1-Based Row Number**<br/>`test_reject_wrong_column_count`<br/>`test_reject_point_count_mismatch_on_triangle_row`<br/>`test_reject_missing_fourth_point_on_trapezoid_row`<br/>`test_reject_non_numeric_coordinate`<br/>`test_reject_empty_csv_file` | `FR-3`, `FR-4`, `NFR-3`, `UC-02`, `UC-04` | CSVs with 10 columns, `3`-point row with non-empty 4th point, `4`-point row with empty 4th point, `"abc"` coordinate, and header-only CSV. | Call `PlaneParser().parse(path)`. | Raises `PlaneError` with `exit_code == 2` and exact `row_index`. | **Pass** |
| **TC-08** | **Vectorized Projection Equivalence with Sequential Reference**<br/>`test_vectorized_matches_sequential_reference_triangle`<br/>`test_vectorized_matches_sequential_reference_trapezoid` | `FR-5` | `32x32x32` analytical `uint8` volume; oblique `TrianglePlane` and `TrapezoidPlane`. | Run `ProjectionEngine.project()` and `_sequential_reference_project()`. | Output matrices match pixel-for-pixel (`np.testing.assert_array_equal`); corners outside triangle footprint are `0`. | **Pass** |
| **TC-09** | **Out-of-Volume Coordinates Masked to Zero**<br/>`test_out_of_volume_coordinates_masked_to_zero` | `FR-6` | `16x16x16` volume filled with `200`; one plane completely in negative space $(-20..-40)$, one partially intersecting. | Call `ProjectionEngine.project(vol, plane)`. | Exterior plane produces all `0`s without error; partial plane contains `200` inside bounds and `0` outside bounds. | **Pass** |
| **TC-10** | **Global `vmax` Normalization & Centered Black Canvas Padding**<br/>`test_normalize_frame_uint8_unchanged`<br/>`test_normalize_frame_uint16_and_uint32_global_vmax`<br/>`test_pad_frame_centers_with_black_border` | `FR-7`, `FR-8`, `UC-03` | `uint8`, `uint16` (`[0, 500, 1000]`, $v_{\max}=1000$), `uint32`, and all-zero frames; `2x4` bright frame padded onto `6x8` canvas. | Call `VideoExporter.normalize_frame()` and `pad_frame()`. | `uint16`/`uint32` map to `[0, 128, 255]`; all-zero maps to `0`; `2x4` slice is centered at `rows 2..3, cols 2..5` with `0` border. | **Pass** |
| **TC-11** | **MP4 Video Stream Encoding & Metadata Verification**<br/>`test_video_exporter_writes_readable_mp4_stream` | `FR-7`, `FR-8`, `FR-9` | Two `uint16` frames of shapes `(20, 30)` and `(40, 50)` with $v_{\max}=1000$. | Write via `with VideoExporter(...)` and open result with `cv2.VideoCapture`. | File size $> 0$; frame count $== 2$; resolution $== (40, 50)$; playback rate $== 30.0\text{ FPS}$. | **Pass** |
| **TC-12** | **End-to-End CLI Demo Execution (`Ex0.py`)**<br/>`test_cli_valid_demo_run_end_to_end` | `FR-1`–`FR-9`, `NFR-2`, `UC-01` | Valid `uint8` NRRD path, 4-row `sample_planes.csv`, output `demo.mp4` path. | Execute `python Ex0.py <nrrd> <csv> <mp4>` via `subprocess.run`. | Return code `0`; warning printed to `stderr`; `demo.mp4` has 4 frames at 30.0 FPS. | **Pass** |
| **TC-13** | **CLI Fast-Fail Exit Code 1 on Bad Arguments or Paths**<br/>`test_cli_exit_code_1_on_bad_arguments_or_missing_files` | `FR-1`, `NFR-3`, `UC-01`, `UC-04` | Missing arguments, `.avi` extension, non-existent `.nrrd` path. | Call `Ex0.main(...)`. | Returns exit code `1` with diagnostic message on `stderr`. | **Pass** |
| **TC-14** | **CLI Fast-Fail Exit Code 2 Leaves No Partial Video File**<br/>`test_cli_exit_code_2_on_bad_csv_row_creates_no_video` | `FR-4`, `NFR-3`, `UC-01`, `UC-02`, `UC-04` | CSV where Row 2 is valid and Row 3 has a $50\%$ leg mismatch ($>10\%$). | Call `Ex0.main([nrrd, bad_csv, out_mp4])`. | Returns exit code `2`; `out_mp4.exists()` is `False`. | **Pass** |
| **TC-15** | **500³ Volume Throughput Benchmark ($\ge 30\text{ FPS}$ Must, $\ge 100\text{ FPS}$ Target)**<br/>`test_500_cubed_projection_fps_benchmark` & `src/run_experiment.py` | `NFR-1` | Synthetic $500^3$ `uint8` volume ($500 \times 500$ `TrianglePlane`) and classroom `data/croissant.nrrd` ($500^3$, 60 planes). | 1 warm-up pass + 3 timed runs; compute median pure projection FPS. | Asserts `median_fps >= 30.0` (measured **435.3 FPS** / $2.30\text{ ms/frame}$ on `croissant.nrrd`, exceeding both 30 FPS floor and 100 FPS target). | **Pass** |
