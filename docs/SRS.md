# Software Requirements Specification (SRS)
**Project:** High-Performance 3D Volumetric Plane Projection (`Ex0.py`)

---

## 1. Introduction

### 1.1 Purpose
This document defines **what the NRRD-to-Video-Slicer (`Ex0.py`) must do**—its inputs, outputs, validation rules, speed targets, and error behavior. It serves as the plain-English checklist used to design ([SDD.md](SDD.md)), build ([EDD.md](EDD.md)), and test ([STP.md](STP.md)) the program.

### 1.2 Scope & Boundaries
The program is a command-line tool run with three file paths:
```bash
python Ex0.py <file.nrrd> <file.csv> <file.mp4>
```
In order, it:
1. Loads a **3D scan** (`.nrrd` voxel grid),
2. Reads a list of **2D slicing shapes** from a `.csv` file (each row defines a 3-point triangle or 4-point trapezoid in 3D space),
3. Cuts a **2D grayscale cross-section** out of the 3D scan for each shape, and
4. Stitches all 2D slices (in CSV row order) into a **30 FPS `.mp4` video**.

**In Scope:**
* Checking CLI arguments, file extensions (`.nrrd`, `.csv`, `.mp4`), file existence, and write permissions.
* Loading 3D `.nrrd` scans with sizes $1 \le sx, sy, sz < 1024$ and non-negative integer voxels (`uint8`, `uint16`, `uint32`, plus promoting non-negative `int8`/`int16`/`int32` scans).
* Reading and validating 13-column `.csv` files (triangles and trapezoids) with three-tier geometric tolerances ($\le 1\%$ silent, $1\%\text{–}10\%$ warning, $> 10\%$ abort).
* Fast 3D-to-2D nearest-neighbor slicing, filling `0` (black) anywhere outside the shape or outside the 3D scan.
* Scaling brightness to 8-bit (`0..255`) using the whole scan's brightest value (`vmax`) and centering smaller slices on a uniform black video canvas.

**Out of Scope:**
* Graphical User Interfaces (GUI) or interactive 3D viewers.
* Medical diagnosis or database storage.
* Real-world millimeter/RAS coordinate transforms (all CSV numbers are direct 3D array indices).
* Smooth trilinear/bicubic interpolation (nearest-neighbor rounding is required).
* Shapes other than isosceles triangles and isosceles trapezoids.

### 1.3 Definitions, Acronyms & Notation
| Term | Simple Meaning |
|---|---|
| **$M$** | The 3D scan array of size $sx \times sy \times sz$, accessed as `M[x, y, z]`. |
| **Voxel Space** | Whole-number 3D grid coordinates where $0 \le x < sx$, $0 \le y < sy$, $0 \le z < sz$. CSV points live in this coordinate space. |
| **Plane ($P$)** | One 2D slicing shape from a CSV row: either an **isosceles triangle** $(a, b, c)$ or an **isosceles trapezoid** $(a', b, a'', c)$ with left leg $a' \to b$ and right leg $a'' \to c$. |
| **Sample Point ($p$)** | A 3D `(x, y, z)` position on plane $P$ whose rounded coordinates are looked up inside $M$. |
| **$E$** | One raw 2D slice image (before border padding), with pixel height $N$ and pixel width $W$. |
| **$D_{ab}$** | Side leg length of the shape (the longer leg if the two differ slightly). Sets slice height $N = \text{round}(D_{ab})$. |
| **$D_{bc}$** | Base width of the shape ($\|c-b\|_2$ for a triangle; the wider of top vs. bottom base for a trapezoid). Sets slice width $W = \text{round}(D_{bc})$. |
| **Scanline** | One horizontal pixel row $y$ of slice $E$, stretching from the left leg point $a_1(y)$ to the right leg point $a_2(y)$. |
| **Out-of-Volume** | Any sample point whose rounded `(x, y, z)` falls outside $M$'s boundaries; its pixel is set to `0` (black). |
| **$v_{\max}$** | The brightest voxel value anywhere in $M$, used once to scale 16/32-bit slices into `0..255`. |

### 1.4 References
* Course Assignment Specification: *Intro2SE Ex1 — Algorithm: Implementing a plane projection of 3D volume* (Pages 1–3).
* 3D Slicer NRRD Format Specification ([teem.sourceforge.net/nrrd](https://teem.sourceforge.net/nrrd/)).
* Companion Project Documents: [SDD.md](SDD.md) (Architecture), [EDD.md](EDD.md) (Detailed Functions & Math), [STP.md](STP.md) (Test Plan), [../results/EXPERIMENT.md](../results/EXPERIMENT.md) (Benchmark Report).

---

## 2. Overall Description

### 2.1 Product Perspective
`Ex0.py` is a standalone, non-interactive command-line tool. It reads `.nrrd` and `.csv` files from local disk and writes a standard `.mp4` video without needing internet access, external servers, or user prompts.

### 2.2 User Classes & Actors
| Actor | How They Use the Program |
|---|---|
| **Researcher / Student User** | Runs `Ex0.py` in a terminal to create cross-sectional fly-through videos of 3D scans; expects clear error messages on mistakes and smooth `.mp4` playback. |
| **Automated Grading / CI Script** | Calls `Ex0.py` automatically on test files and checks exit codes (`0, 1, 2, 3`), exact frame counts, video dimensions, and $\ge 30\text{ FPS}$ speed. |

### 2.3 Operating Environment
* **OS:** macOS, Linux, and Windows (plus Linux Docker containers on `aarch64` / `x86_64`).
* **Python:** Python 3.10+.
* **Hardware:** Standard laptop/desktop CPU with enough RAM to hold one $500^3$ volume ($\sim 125\text{ MB}$ for `uint8`, up to $500\text{ MB}$ for `uint32`).

### 2.4 Design & Implementation Constraints
* **Exact CLI Command:** Must run as `python Ex0.py <file.nrrd> <file.csv> <file.mp4>`.
* **Volume Size & Types:** Each 3D axis must be $1 \le s < 1024$ (`2^10`). Voxels must be 8-, 16-, or 32-bit unsigned integers (non-negative signed integers like 3D Slicer's 16-bit `short` `MRHead_1.nrrd` are automatically promoted to unsigned).
* **Matching the Classroom CSV Data (`data/sample_planes.csv`):**
  * *Why 4-point rows use `(a', b, a'', c)` order:* Page 2 defines a trapezoid by two equal-length leg vectors $a' \to b$ and $a'' \to c$, and [`data/sample_planes.csv`](../data/sample_planes.csv) stores 4-point rows in that exact column order (`a', b, a'', c`). Width $D_{bc}$ uses $\max(\text{top base}, \text{bottom base})$ so trapezoids work whether the top or bottom is wider.
  * *Why geometry uses `1% / 10%` tolerance tiers:* Page 3 Q&A mentions a tiny `EPS=0.001`, whereas Row 3 of the provided [`data/sample_planes.csv`](../data/sample_planes.csv) has legs of length $497.39$ and $476.86$ (a $4.12\%$ difference). Using three tiers—$\le 1\%$ silent, $1\%\text{–}10\%$ warning, $> 10\%$ abort—handles both strict math tests and the classroom dataset cleanly.
* **All-or-Nothing Video Creation:** If *any* CSV row is invalid, the program must abort before creating an `.mp4` file (never leaving a partial or broken video behind).

### 2.5 Assumptions & Dependencies
* CSV coordinates are already in voxel grid indices relative to `M[x, y, z]`.
* Only standard `pip` packages (`numpy`, `pynrrd`, `opencv-python`) are used at runtime.

---

## 3. Specific Requirements

### 3.1 External Interface Requirements
* **EIR-1 (Command-Line Interface):**
  * **Command:** `python Ex0.py <file.nrrd> <file.csv> <file.mp4>`
  * **`stdout`:** Kept completely silent during normal runs so scripts can call the tool cleanly.
  * **`stderr`:** Prints `1%–10%` geometry warnings and clear single-line `"Error: ..."` messages on failure.
  * **Exit Codes:** `0` = Success, `1` = Bad CLI args / missing file / permission error, `2` = Invalid NRRD scan or CSV plane row, `3` = Video encoding failure.
* **EIR-2 (`.nrrd` Input File):** 3D NRRD raster (`uint8`, `uint16`, `uint32`, or non-negative `int8`/`int16`/`int32`), where NRRD axes 0, 1, 2 map to `x, y, z`.
* **EIR-3 (`.csv` Input File):** UTF-8 CSV with 13 columns per data row: `Number of Point, x1,y1,z1, x2,y2,z2, x3,y3,z3, x4,y4,z4`.
* **EIR-4 (`.mp4` Output File):** MPEG-4 video (`mp4v` codec) at `30.0 FPS` where every frame has size `(H_max, W_max)`.

### 3.2 Functional Requirements (FR)

*(MoSCoW Priorities: **Must** = Required, **Should** = Important quality goal)*

* **FR-1 — Check CLI Arguments & File Paths [Must]:**
  * Require exactly 3 arguments ending in `.nrrd`, `.csv`, and `.mp4` (case-insensitive).
  * Confirm both input files exist and the output directory/file is writable before loading data.
  * On failure: print a clear error to `stderr` and exit with code `1`.

* **FR-2 — Load & Validate 3D NRRD Scan [Must]:**
  * Load the `.nrrd` file as `M[x, y, z]` and verify it is 3D with $1 \le sx, sy, sz < 1024$.
  * Accept `uint8`, `uint16`, `uint32`, and promote non-negative `int8`/`int16`/`int32` scans to unsigned.
  * Reject non-3D arrays, axes $\ge 1024$, negative voxel values, or float types with exit code `2`.

* **FR-3 — Parse 13-Column CSV Plane List [Must]:**
  * Read rows in order, ignoring blank lines and skipping the first non-blank line if its first cell is text (header).
  * Require 13 columns per row, with Column 1 set to `3` (triangle) or `4` (trapezoid); both types can be mixed in one file.
  * If `3`: read points $a, b, c$ from columns 2–10 and require columns 11–13 to be empty.
  * If `4`: read points $a', b, a'', c$ from columns 2–13 (forming legs $a' \to b$ and $a'' \to c$).

* **FR-4 — Validate All Planes Before Rendering [Must]:**
  * Check every CSV row up front before creating the video:
  * **Immediate abort errors:** Point count not `3` or `4`, wrong filled/empty columns, missing or non-numeric numbers, collinear points (zero area), or rounded pixel size $N < 1$ or $W < 1$.
  * **Isosceles leg check** ($\delta = |L_1 - L_2| / \max(L_1, L_2)$) and **Trapezoid flatness check** (distance of $c$ from plane $(a', b, a'')$ divided by $D_{ab}$):
    * $\le 1\%$: accept silently.
    * $1\% < \text{deviation} \le 10\%$: accept and print a warning with the 1-based row number to `stderr`.
    * $> 10\%$: abort immediately.
  * On abort: print the 1-based CSV row number and reason to `stderr`, create **no** `.mp4` file, and exit with code `2`.

* **FR-5 — Slice 3D Volume onto 2D Plane [Must]:**
  * Build a 2D image $E$ of height $N = \text{round}(D_{ab})$ rows and width $W = \text{round}(D_{bc})$ columns (`E[row, col]`).
  * Step down both legs by fraction $t = (y+1)/N$ for each row $y \in [0, N-1]$ to get scanline endpoints $a_1(y)$ and $a_2(y)$, center the scanline horizontally inside width $W$, and copy voxel values from $M$ at rounded nearest-neighbor integer coordinates.
  * Set pixels outside the triangle/trapezoid edges to `0`.

* **FR-6 — Handle Out-of-Bounds Coordinates Safely [Must]:**
  * Any sample point whose rounded `(x, y, z)` falls outside `[0..sx-1, 0..sy-1, 0..sz-1]` must be given pixel value `0` (black) without crashing.

* **FR-7 — Center Smaller Slices on a Uniform Canvas [Must]:**
  * Compute the max height $H_{\max} = \max_i N_i$ and max width $W_{\max} = \max_i W_i$ across all planes in the CSV.
  * Center any smaller $(N, W)$ slice on a black (`0`) $H_{\max} \times W_{\max}$ canvas so all video frames match in size.

* **FR-8 — Normalize Brightness Using Global `vmax` [Must]:**
  * Keep `uint8` slices as-is (`0..255`).
  * Scale `uint16` and `uint32` slices to `uint8` using one scan-wide factor: $v_8 = \text{round}(v \times 255 / v_{\max})$, where $v_{\max}$ is the max value in $M$ (an all-zero scan outputs all-zero frames).

* **FR-9 — Export 30 FPS MP4 Video [Must]:**
  * Write all normalized, padded frames in CSV order to an `.mp4` file at `30.0 FPS` (`mp4v` codec), overwriting an existing file if present.
  * If encoding fails: delete any partial `.mp4` file and exit with code `3`.

### 3.3 Non-Functional Requirements (NFR)
* **NFR-1 — Slicing Speed (FPS) [Must]:**
  * On a $500^3$ `uint8` scan with $500 \times 500$ planes, pure slicing speed (excluding file I/O and MP4 encoding) must be **$\ge 30\text{ FPS}$** ($\le 33.3\text{ ms/frame}$), targeting **$\ge 100\text{ FPS}$** ($\le 10.0\text{ ms/frame}$), measured as the median of $\ge 3$ runs after 1 warm-up pass.
* **NFR-2 — Constant Frame Memory (`O(1)`) [Must]:**
  * Load 3D scan $M$ into RAM once, and stream 2D frames one at a time to the encoder (freeing each frame immediately) so memory never grows with CSV length.
* **NFR-3 — Clean Errors (No Tracebacks) [Must]:**
  * Never crash with raw Python stack traces or `ZeroDivisionError` on bad files or geometry; always exit cleanly with code `0`, `1`, `2`, or `3`.
* **NFR-4 — Independent Automated Tests [Should]:**
  * Every requirement (`FR-1..9`, `NFR-1..5`) must be verified by automated `pytest` tests without needing manual human inspection.
* **NFR-5 — Cross-Platform Portability [Should]:**
  * Run identically on Python 3.10+ across macOS, Linux, and Windows using only `numpy`, `pynrrd`, and `opencv-python`.

---

## 4. Appendices

### 4.1 Use Case Model & UML Use Case Diagram

```mermaid
flowchart LR
    User(["👤 Researcher / CLI User"])
    Grad(["🤖 Automated Grading Script"])

    subgraph Boundary["NRRD-to-Video-Slicer System (Ex0.py)"]
        UC1(["UC-01: Generate Projection Video from Volume & CSV"])
        UC2(["UC-02: Validate CSV Plane Trajectory"])
        UC3(["UC-03: Normalize & Center-Pad Slice Frames"])
        UC4(["UC-04: Report Diagnostic Warning / Error"])
    end

    User --- UC1
    Grad --- UC1
    UC1 -.->|"&lt;&lt;include&gt;&gt;"| UC2
    UC1 -.->|"&lt;&lt;include&gt;&gt;"| UC3
    UC4 -.->|"&lt;&lt;extend&gt;&gt;<br/>[1% &lt; delta &lt;= 10% or invalid input]"| UC2
    UC4 -.->|"&lt;&lt;extend&gt;&gt;<br/>[I/O or encoding error]"| UC1
```

### 4.2 Detailed Use Cases

#### `UC-01`: Generate Projection Video from Volume & CSV
* **Actor:** CLI User or Grading Script
* **Preconditions:** Python environment ready; input `.nrrd` and `.csv` paths and writable `.mp4` folder available.
* **Main Success Steps:**
  1. User runs `python Ex0.py <file.nrrd> <file.csv> <file.mp4>`.
  2. Program checks CLI arguments, extensions, and file permissions (`FR-1`).
  3. Program loads `.nrrd` scan $M$, checks size/dtype (`FR-2`), and saves global max brightness $v_{\max}$ (`FR-8`).
  4. Program parses and validates all CSV rows up front (`UC-02`, `FR-3`, `FR-4`).
  5. Program finds max canvas size $(H_{\max}, W_{\max})$ (`FR-7`) and opens the 30 FPS `.mp4` writer (`FR-9`).
  6. For each plane, program slices $M$ into 2D array $E$ (`FR-5`, `FR-6`), normalizes and center-pads $E$ (`UC-03`, `FR-7`, `FR-8`), writes the frame, and frees $E$ (`FR-9`, `NFR-2`).
  7. Program closes the `.mp4` file and exits with code `0`.
* **Error Paths:**
  * **2a. Bad CLI args / missing file / unwritable path:** Calls `UC-04` (`InputError`) → exit code `1`.
  * **3a. Bad NRRD dimensions / negative or float voxels:** Calls `UC-04` (`VolumeError`) → exit code `2`.
  * **4a. Bad CSV row or $>10\%$ geometry error:** Calls `UC-04` (`PlaneError`), writes no `.mp4` → exit code `2`.
  * **6a. Video writer fails:** Deletes partial `.mp4`, calls `UC-04` (`EncodingError`) → exit code `3`.
* **Result:** Playable 30 FPS `.mp4` with one $(H_{\max}, W_{\max})$ frame per CSV data row.

#### `UC-02`: Validate CSV Plane Trajectory
* **Actor:** System (used by `UC-01`)
* **Main Success Steps:**
  1. Reads CSV lines, skipping blank lines and an optional text header (`FR-3`).
  2. Verifies 13 columns per row, reads point count (`3` or `4`), and parses 3D coordinates (`FR-3`).
  3. Calculates leg lengths, base width, pixel size $(N, W)$, leg difference $\delta$, and trapezoid flatness (`FR-4`).
  4. All differences are $\le 1\%$ and $N, W \ge 1$; returns validated planes with no warnings.
* **Alternative / Error Paths:**
  * **3a. Difference between $1\%$ and $10\%$:** Keeps the plane, emits a row warning via `UC-04`, and continues.
  * **2a / 3b. Malformed row, collinear points, size $< 1$ pixel, or difference $> 10\%$:** Aborts immediately via `UC-04` with the 1-based row number.

#### `UC-03`: Normalize & Center-Pad Slice Frames
* **Actor:** System (used by `UC-01`)
* **Main Success Steps:**
  1. Scales `uint16`/`uint32` slice $E$ to `uint8` using $\text{round}(E \times 255 / v_{\max})$ (`FR-8`), or keeps `uint8` as-is (if $v_{\max} = 0$, outputs all zeros).
  2. Centers the $(N, W)$ slice on a black $(H_{\max}, W_{\max})$ canvas (`FR-7`).
  3. Sends the padded frame to the `.mp4` writer and frees temporary memory (`NFR-2`).

#### `UC-04`: Report Diagnostic Warning / Error
* **Actor:** System (triggered on warnings or errors)
* **Warning Path ($1\% < \delta \le 10\%$):** Prints `"Warning (Row X): ..."` to `stderr` (keeping `stdout` empty) and lets video creation continue.
* **Fatal Error Paths:** Prints `"Error: ..."` to `stderr` without a traceback, ensures no partial `.mp4` remains on disk, and exits with `1` (`InputError`), `2` (`VolumeError` / `PlaneError`), or `3` (`EncodingError`).

### 4.3 UML Activity Diagram: Flow of `UC-01` & `UC-02`

```mermaid
flowchart TD
    Start([Start: python Ex0.py nrrd csv mp4]) --> CheckCLI{"CLI args & paths<br/>valid? (FR-1)"}
    CheckCLI -->|"[invalid]"| Exit1(["Print error to stderr<br/>Exit Code 1"])
    CheckCLI -->|"[valid]"| LoadVol["Load NRRD volume M &<br/>compute vmax (FR-2, FR-8)"]
    LoadVol --> CheckVol{"3D, 1<=s<1024,<br/>unsigned/non-neg? (FR-2)"}
    CheckVol -->|"[invalid]"| Exit2Vol(["Print VolumeError to stderr<br/>Exit Code 2"])
    CheckVol -->|"[valid]"| ParseCSV["Read 13-col CSV rows &<br/>check geometry (FR-3, FR-4)"]
    ParseCSV --> CheckGeo{"Plane deviation<br/>check (FR-4)"}
    CheckGeo -->|"[structural error or delta > 10%]"| Exit2Plane(["Print Row # & PlaneError<br/>No MP4 created · Exit Code 2"])
    CheckGeo -->|"[1% < delta <= 10%]"| Warn["Print Warning (Row #) to stderr"]
    CheckGeo -->|"[delta <= 1%]"| CalcCanvas["Compute uniform canvas<br/>H_max, W_max (FR-7)"]
    Warn --> CalcCanvas
    CalcCanvas --> LoopStart["For each validated Plane in CSV order"]
    LoopStart --> Project["Project 3D M onto 2D frame E<br/>Mask outside-shape & out-of-volume to 0 (FR-5, FR-6)"]
    Project --> NormPad["Normalize to uint8 via vmax (FR-8)<br/>Center-pad on H_max x W_max canvas (FR-7)"]
    NormPad --> WriteMP4["Write frame to 30 FPS MP4 stream<br/>& free frame memory (FR-9, NFR-2)"]
    WriteMP4 --> MorePlanes{"More planes<br/>in CSV?"}
    MorePlanes -->|"[yes]"| LoopStart
    MorePlanes -->|"[no]"| CloseMP4(["Close MP4 stream<br/>Exit Code 0"])
```

### 4.4 Domain Data Dictionary
| Entity / Field | Type | Rules & Meaning |
|---|---|---|
| `M` | 3D Array (`uint8` / `uint16` / `uint32`) | Size $1 \le sx, sy, sz < 1024$; voxel values $\ge 0$. |
| `Number of Point` | Integer (CSV Col 1) | `3` = triangle, `4` = trapezoid. |
| `x1..z4` | Floats (CSV Cols 2–13) | 3D voxel coordinates; Cols 11–13 must be empty when Col 1 is `3`. |
| `delta` ($\delta$) | Ratio $\in [0, 1]$ | $|L_1 - L_2| / \max(L_1, L_2)$; $\le 1\%$ silent, $1\%\text{–}10\%$ warn, $> 10\%$ abort. |
| `E` | 2D Array ($N \times W$) | Raw slice before padding; $N = \text{round}(D_{ab}) \ge 1$, $W = \text{round}(D_{bc}) \ge 1$. |
| `Canvas Frame` | 2D Array ($H_{\max} \times W_{\max}$, `uint8`) | `0..255` grayscale slice centered on a black (`0`) background. |

### 4.5 Requirements Traceability Matrix
| Req ID | Requirement Summary | Use Case | Design Ref ([SDD](SDD.md) / [EDD](EDD.md)) | Test Cases ([STP / STD](STP.md)) | Status |
|---|---|---|---|---|---|
| **FR-1** | CLI argument & path validation (exit code 1) | `UC-01`, `UC-04` | `SDD §2.6`, `EDD §1.4` | `TC-12`, `TC-13` | Passed |
| **FR-2** | NRRD ingestion, grid bounds & dtype validation | `UC-01`, `UC-04` | `SDD §2.1`, `EDD §1.1` | `TC-01`, `TC-02`, `TC-03` | Passed |
| **FR-3** | 13-column CSV parsing (3- & 4-point rows) | `UC-01`, `UC-02` | `SDD §2.3`, `EDD §3` | `TC-06`, `TC-07` | Passed |
| **FR-4** | Plane validation ($\le 1\%$ silent, $1\text{–}10\%$ warn, $>10\%$ abort) | `UC-02`, `UC-04` | `SDD §2.2`, `EDD §1.2` | `TC-04`, `TC-05`, `TC-07`, `TC-14` | Passed |
| **FR-5** | 3D-to-2D plane projection & outside-shape zeroing | `UC-01` | `SDD §2.4`, `EDD §2` | `TC-08`, `TC-09` | Passed |
| **FR-6** | Out-of-volume boundary masking ($v = 0$) | `UC-01` | `SDD §2.4`, `EDD §2.4` | `TC-09` | Passed |
| **FR-7** | Uniform $H_{\max} \times W_{\max}$ canvas & centered black padding | `UC-03` | `SDD §2.5`, `EDD §3` | `TC-10`, `TC-11`, `TC-12` | Passed |
| **FR-8** | Global `vmax` brightness normalization to `uint8` | `UC-03` | `SDD §2.1, §2.5`, `EDD §1.1` | `TC-01`, `TC-10` | Passed |
| **FR-9** | MP4 video export (30 FPS, `mp4v`, CSV order) | `UC-01`, `UC-04` | `SDD §2.5`, `EDD §4.1` | `TC-11`, `TC-12` | Passed |
| **NFR-1** | $\ge 30\text{ FPS}$ mandatory, $\ge 100\text{ FPS}$ target on $500^3$ | `UC-01` | `SDD §5.1`, `EDD §2.4, §6` | `TC-15` | Passed (435 FPS) |
| **NFR-2** | Single volume load & $O(1)$ frame memory streaming | `UC-01`, `UC-03` | `SDD §2.6`, `EDD §4.1, §6` | `TC-12` | Passed |
| **NFR-3** | Fault tolerance & deterministic exit codes (`0..3`) | `UC-01`, `UC-04` | `SDD §3`, `EDD §1.4, §5` | `TC-03`, `TC-05`, `TC-13`, `TC-14` | Passed |
| **NFR-4** | Decoupled module testability & full traceability | All | `SDD §2, §3`, `EDD §8` | `TC-01`–`TC-15` | Passed |
| **NFR-5** | Cross-platform Python 3.10+ portability | `UC-01` | `SDD §4` | `TC-12`, Docker CI | Passed |
