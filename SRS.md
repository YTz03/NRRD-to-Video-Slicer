# Software Requirements Specification (SRS)
**Project:** High-Performance 3D Volumetric Plane Projection (`Ex0.py`)

---

## 1. Introduction & System Goals

### 1.1 System Overview
This document specifies the functional requirements, non-functional constraints, software architecture, and execution pipeline for the 3D Volume Projection system. The software operates as an automated data-transformation pipeline that:
1. loads a 3D volumetric raster (`.nrrd`),
2. reads a list of slicing planes from a `.csv` file (each plane = 3 or 4 points),
3. projects each plane (isosceles triangle or isosceles trapezoid) onto a 2D image, and
4. encodes all images, in CSV order, as frames of an `.mp4` video.

### 1.2 Scope & Boundaries
The system is strictly defined as a Command-Line Interface (CLI) application invoked via:
```bash
python Ex0.py <file.nrrd> <file.csv> <file.mp4>
```
**In Scope:**
* Loading NRRD volumes and validating their size and data type.
* Parsing and validating plane definitions from CSV (3-point triangle / 4-point trapezoid).
* Executing vectorized geometric projection of 3D planes onto 2D discrete grids.
* Normalizing and encoding sequential 2D matrices into an `.mp4` video stream.
* Testing and benchmarking on a shared classroom dataset of several NRRD volumes and matching CSV plane files (see the Dataset section).

**Out of Scope:**
* Graphical User Interfaces (GUI) or interactive 3D rendering.
* Medical diagnostic interpretation or persistent database storage.
* Physical/world (RAS) coordinates – all plane points are given in voxel index space (see §1.4).
* Interpolation other than nearest-neighbor (e.g. trilinear).
* Plane shapes other than isosceles triangles and isosceles trapezoids.

### 1.3 Engineering Priorities
The quality of the software engineering takes precedence over the projection math itself. Two priorities govern all design decisions:
* **Object-Oriented Design (OOD & SOLID):** Strict separation of concerns (SRP) between file I/O, geometry, projection math, and video encoding, so each module is independent and testable.
* **Runtime Efficiency:** Vectorized `NumPy` array operations instead of per-pixel Python loops.
  * Minimum requirement: **30 FPS** or more on $500^3$ byte matrices.
  * Target: **100+ FPS**.
  * Stretch goal: 300+ FPS, the level a well-optimized compiled implementation (e.g. Java on an Apple M2) can reach.

### 1.4 Definitions & Notation
| Term | Meaning |
|---|---|
| **M** | The 3D volume, a matrix of size $sx \times sy \times sz$, indexed `M[x][y][z]`. |
| **Voxel space** | Integer coordinates $0 \le x < sx$, $0 \le y < sy$, $0 \le z < sz$. All CSV points are given in this space. |
| **Plane (P)** | The slicing region: an isosceles triangle $(a, b, c)$ or an isosceles trapezoid $(a', b, a'', c)$ with legs $a' \to b$ and $a'' \to c$. Written as capital **P** so it is not confused with a sample point. |
| **Sample point (p)** | A real-valued 3D point on the plane where M is sampled. |
| **E** | The 2D output image (one video frame) for a single plane. |
| **D_ab** | Leg length: $dist(a,b) = dist(a,c)$ for a triangle; $dist(a',b) = dist(a'',c)$ for a trapezoid. Gives the height of E. If the two legs differ slightly (see FR-4), the longer leg is used. |
| **D_bc** | Base length $dist(b,c)$. Gives the width of E. |
| **v(ab), v(ac)** | Unit vectors from the apex (or $a'$, $a''$) toward b and c. |
| **Scanline** | One row y of E, sampled along the segment $a_1 \to a_2$. |
| **Out-of-volume** | A sample point p whose rounded coordinates fall outside M; its value is 0. |

---

## 2. System Requirements

### 2.1 Functional Requirements (FR)
* **FR-1 (CLI Parsing):** The system shall accept exactly three command-line arguments: input `.nrrd` path, input `.csv` path, and output `.mp4` path, validating that the input files exist, that all three paths have the expected extensions, and that the output directory is writable, before execution. On any failure it shall print a usage/diagnostic message and exit with code 1.
* **FR-2 (Volumetric Ingestion):** The system shall parse `.nrrd` files into a 3D matrix $M$ of dimensions $sx \times sy \times sz$ (where $1 \le sx, sy, sz < 2^{10}$) supporting unsigned integer formats (`uint8`, `uint16`, `uint32`). The array shall be indexed `M[x][y][z]`, with the first NRRD axis as $x$. Volumes that are not 3D, exceed the size limits, or use another data type shall be rejected with a clear error (exit code 2).
* **FR-3 (Plane List Parsing):** The system shall read the `.csv` file with comma-separated columns, one plane per row, in file order:
  * Layout: 13 columns: `Number of Point, x1,y1,z1, x2,y2,z2, x3,y3,z3, x4,y4,z4`.
  * The first line is a header and is skipped (a first line whose first cell is non-numeric). Blank lines are ignored.
  * Column 1 is the number of points: `3` (isosceles triangle) or `4` (isosceles trapezoid). Triangle and trapezoid rows may be mixed in one file.
  * Triangle (`3`): points are $a, b, c$ in columns 2–10; the cells of point 4 are empty.
  * Trapezoid (`4`): points are $a', b, a'', c$ in columns 2–13, so that the two legs are $a' \to b$ and $a'' \to c$.
  * Coordinates are real numbers in voxel space (§1.4). They may be negative or exceed the volume bounds; such points are handled by FR-6.
* **FR-4 (Plane Validation):** All rows shall be validated before any frame is rendered.
  * **Structural errors abort the run:** a point count other than 3 or 4, a point count that does not match the number of filled coordinate cells, a missing or non-numeric coordinate, or a plane whose $D_{ab}$ or $D_{bc}$ rounds to less than 1 pixel.
  * **Isosceles check:** the leg difference $\delta = |L_1 - L_2| / \max(L_1, L_2)$ is computed from the two legs ($dist(a,b)$ and $dist(a,c)$ for a triangle; $dist(a',b)$ and $dist(a'',c)$ for a trapezoid).
    * $\delta \le 1\%$: accepted silently.
    * $1\% < \delta \le 10\%$: the plane is projected, and a warning naming the row number and $\delta$ is printed.
    * $\delta > 10\%$: the run aborts.
  * **Trapezoid coplanarity:** the distance of $c$ from the plane through $a', b, a''$, divided by $D_{ab}$, is checked with the same 1% / 10% limits.
  * On abort, the system shall print the row number and the reason, exit with code 2, and write no video file. This guarantees that the number of video frames equals the number of CSV rows.
* **FR-5 (Vectorized Plane Projection):** For each plane, the system shall compute the plane dimensions, derive the scanline end points, and sample the 3D volume $M$ using nearest-neighbor (rounded) integer indices to construct the 2D matrix $E$.
  * $E$ has $N = \text{round}(D_{ab})$ rows ($y$, top to bottom) and $W = \text{round}(D_{bc})$ columns ($x$), stored as `E[row][col]`. $D_{ab}$ is the longer of the two legs. For a trapezoid, $D_{bc}$ is the longer of the two bases.
  * Each row $y$ corresponds to a fraction $t$ of the way along both legs: $a_1 = a + t(b - a)$ and $a_2 = a + t(c - a)$ for a triangle; $a_1 = a' + t(b - a')$ and $a_2 = a'' + t(c - a'')$ for a trapezoid. For isosceles planes this is identical to stepping one voxel per row. The row is sampled along the segment $a_1 \to a_2$ and centered horizontally.
  * Pixels of $E$ that lie outside the triangle/trapezoid shall be 0.
  * The exact formulas are defined in the Algorithm section.
* **FR-6 (Boundary Handling):** Any sampled 3D coordinate falling outside the valid bounds of $M$ ($x \notin [0, sx-1]$, $y \notin [0, sy-1]$, or $z \notin [0, sz-1]$) after rounding shall automatically be assigned a default voxel value of $v = 0$ without raising runtime exceptions.
* **FR-7 (Uniform Frame Size):** All frames in one video shall have the same size. The video canvas is (max height) × (max width) over all planes. Each smaller frame shall be centered on the canvas with black (0) padding. The canvas size is calculated from geometry only, before any frame is rendered.
* **FR-8 (Bit-Depth Normalization):** `uint8` volumes shall be used as-is. For `uint16` / `uint32` volumes, every frame shall be scaled with one global factor, $v_8 = \text{round}(v \times 255 / v_{max})$, where $v_{max}$ is the maximum value of the whole volume (an all-zero volume produces all-zero frames).
* **FR-9 (Video Export):** The system shall encode the sequence of 2D 8-bit grayscale matrices into a valid `.mp4` file, one frame per plane in CSV order, at a fixed 30 frames per second of playback with the `mp4v` codec. The output file shall be overwritten if it exists.

### 2.2 Non-Functional Requirements (NFR)
* **NFR-1 (Performance):** Frame generation must execute in $\le 33.3\text{ ms}$ per frame ($\ge 30\text{ FPS}$), targeting $\le 10\text{ ms}$ per frame ($\ge 100\text{ FPS}$) for $500^3$ volumes using `NumPy` broadcasting. FPS is measured on a $500^3$ `uint8` volume with $500 \times 500$ frames, timing only the projection step (sampling and masking, not file loading or video encoding), as the median of at least 3 runs after one warm-up, and is reported together with the hardware used. End-to-end FPS (including encoding) shall also be reported for information.
* **NFR-2 (Memory Footprint):** The 3D matrix $M$ must be allocated in RAM once. Generated 2D frames ($E$) must be streamed directly to the video encoder and not retained after writing, so frame memory stays constant ($O(1)$) for CSV files of any length.
* **NFR-3 (Robustness & Fault Tolerance):** The system must gracefully handle degenerate geometric inputs (no division by zero when points coincide: such rows are invalid per FR-4), malformed CSV rows (abort with row number and reason), and I/O errors (clear message, no stack trace). Exit codes: `0` = success, `1` = argument or file/permission error, `2` = invalid volume or invalid CSV row, `3` = video encoding failure.
* **NFR-4 (Maintainability & Testability):** Each module (volume loading, plane parsing/geometry, projection, video export) shall be usable and testable without the others, communicating only through the data structures in §4. Every requirement shall be covered by at least one automated test (traceability table in the Testing section).
* **NFR-5 (Portability):** The system shall run on Python 3.10+ on macOS, Linux and Windows using only pip-installable packages (`numpy`, `pynrrd`, `opencv-python`).

---

## 3. System Architecture (Classes & Modules)

To satisfy OOD principles, the system is divided into six decoupled modules. This architecture enables isolated unit testing and prevents changes in I/O formats from impacting the mathematical core. Only `AppController` knows all the modules; the others communicate only through the data structures in §4.

```text
AppController ──► VolumeData         .nrrd ──► M (read-only array), max value
     │
     ├──────────► PlaneParser        .csv  ──► list of Plane objects (all validated, FR-4)
     │                                         Plane = TrianglePlane | TrapezoidPlane
     │
     ├──────────► ProjectionEngine   (M, Plane) ──► frame E   (one call per plane)
     │
     └──────────► VideoExporter      E ──► padded, normalized frame ──► .mp4
```

### 3.1 `VolumeData` (Data Ingestion Layer)
* **Role:** Dedicated 3D data parser and state holder. Abstracts file-reading complexity away from the algorithmic engine.
* **Design Benefit (Decoupling):** If future requirements introduce new medical imaging formats (e.g., DICOM), only `VolumeData` requires modification.
* **Responsibilities:**
  * Load `.nrrd` files using `pynrrd`, with the first NRRD axis as $x$ so the array is indexed `M[x][y][z]` (FR-2).
  * Validate grid constraints ($1 \le sx, sy, sz < 2^{10}$) and unsigned integer data types (`uint8`, `uint16`, `uint32`); raise a `VolumeError` (exit code 2) for any violation.
  * Expose the 3D volume as a read-only in-memory `numpy.ndarray` ($M$).
  * Expose the maximum value of the volume, computed once at load time, used for the global brightness scaling (FR-8).

### 3.2 `Plane` Model: `TrianglePlane` and `TrapezoidPlane` (Geometry Layer)
* **Role:** Immutable value objects that represent one slicing plane and know their own geometry. `Plane` is an abstract base class; `TrianglePlane` (points $a, b, c$) and `TrapezoidPlane` (points $a', b, a'', c$) are its two subclasses.
* **Design Benefit (Open/Closed, polymorphism):** The engine works with any `Plane`. Adding a new shape means adding a subclass, with no change to `ProjectionEngine` and no `if triangle / else trapezoid` branches.
* **Common interface (every plane provides):**
  * Four corner points: `top_left` and `top_right` (where the two legs start: both equal $a$ for a triangle, $a'$ and $a''$ for a trapezoid), and `bottom_left` ($b$) and `bottom_right` ($c$). A triangle is a trapezoid whose top edge has shrunk to a point (`top_left == top_right`), so the engine uses one formula for both: $a_1 = \text{top\_left} + t(\text{bottom\_left} - \text{top\_left})$ and $a_2 = \text{top\_right} + t(\text{bottom\_right} - \text{top\_right})$.
  * `height` $N = \text{round}(D_{ab})$ (the longer leg) and `width` $W = \text{round}(D_{bc})$ (the longer base for a trapezoid).
  * `validate()`: runs the FR-4 checks (leg difference $\delta$, trapezoid coplanarity, minimum size). It returns the warnings for $1\% < \delta \le 10\%$ and raises `PlaneError` (exit code 2) above 10% or for degenerate shapes, so zero-length vectors can never reach the engine.

### 3.3 `PlaneParser` (Plane List Reader)
* **Role:** Reads the `.csv` file and turns it into `Plane` objects. Knows the CSV layout and nothing about volumes or video.
* **Design Benefit (Decoupling):** If the plane list format changes (JSON, another column layout), only `PlaneParser` changes.
* **Responsibilities:**
  * Skip the header and blank lines, read the point-count column, and read the 3 or 4 coordinate triples (FR-3).
  * Create a `TrianglePlane` or `TrapezoidPlane` per row (a small factory keyed on the point count).
  * Call `validate()` on every plane and collect the warnings; stop at the first structural error with the row number and the reason (FR-4), raising `PlaneError`. The parser itself contains no geometry rules.
  * Return the full ordered list of planes, so the whole file is checked before any frame is rendered.

### 3.4 `ProjectionEngine` (Algorithmic Core)
* **Role:** Stateless mathematical engine. Computes 2D slicing planes completely independently of file I/O or video codecs.
* **Design Benefit (Testability):** Supports isolated Unit Testing by accepting synthetic 3D `NumPy` arrays and simple `Plane` objects without touching the filesystem.
* **Responsibilities:**
  * Take the plane's height, width and corner points from the `Plane` interface.
  * Construct a 2D sampling grid via `NumPy` vectorization (`np.linspace` / broadcasting), eliminating Python `for` loops over pixels, using the fraction-$t$ formulas of FR-5.
  * Round spatial coordinates to nearest integer indices, apply boolean boundary masks (setting out-of-bounds indices to $v = 0$), and extract the 2D matrix ($E$). Pixels outside the shape are 0.

### 3.5 `VideoExporter` (Presentation Layer)
* **Role:** Media stream compiler. Transforms raw 2D mathematical matrices into a standard `.mp4` video stream.
* **Design Benefit (Flexibility):** Decouples output encoding from geometry calculation. Switching output formats (e.g., to `.avi` or `.png` sequences) requires zero changes to `ProjectionEngine`.
* **Responsibilities:**
  * Initialize the video writer stream (`mp4v` codec, 30 FPS, and the canvas size supplied by the controller, FR-7 and FR-9).
  * Normalize incoming 2D matrices ($E$) from `uint16`/`uint32` into standard `uint8` $[0, 255]$ grayscale frames with the global factor derived from the volume's maximum value (FR-8), and center each frame on the canvas with black padding (FR-7).
  * Write sequential frames to the video buffer and safely close/release the `.mp4` file descriptor upon completion (context manager); raise `EncodingError` (exit code 3) on failure.

### 3.6 `AppController` (Execution Orchestrator / `Ex0.py`)
* **Role:** Central coordinator that wires the decoupled modules together and manages the execution lifecycle.
* **Design Benefit (Maintainability):** Keeps top-level workflow linear, clean, and readable while centralizing exception handling.
* **Responsibilities:**
  * Parse and validate CLI arguments (`<file.nrrd> <file.csv> <file.mp4>`) (FR-1).
  * Instantiate `VolumeData`, `PlaneParser`, `ProjectionEngine`, and `VideoExporter`.
  * Obtain the full validated list of planes from `PlaneParser`, compute the canvas size (largest height and width) and pass it to `VideoExporter`, then for each plane call the engine and pipe the resulting frame to the exporter.
  * Print the warnings collected from validation, and translate errors into exit codes. This is the only place where errors are handled: `InputError` → 1, `VolumeError` / `PlaneError` → 2, `EncodingError` → 3 (NFR-3).

---

## 4. Core Data Structures

To guarantee high-speed vectorized execution and strict interface contracts between modules, the system relies on contiguous memory arrays and immutable value objects rather than standard Python lists. All communication between the modules in §3 happens exclusively through the four structures below.

### 4.1 3D Volume Matrix ($M$)
* **Data Type:** `numpy.ndarray` (3D), with `flags.writeable = False`.
* **Format:** Unsigned integers (`np.uint8`, `np.uint16`, or `np.uint32`).
* **Dimensions & Indexing:** $sx \times sy \times sz$ where $1 \le sx, sy, sz < 2^{10}$, indexed `M[x, y, z]` with $0 \le x < sx$, $0 \le y < sy$, $0 \le z < sz$ (FR-2).
* **Companion Metadata (`vmax`):** Scalar integer/float storing the global maximum value of $M$, computed once when the volume is loaded and passed to `VideoExporter` for global brightness scaling (FR-8).
* **State & Memory Rationale:** Represents the immutable scanned volume. Loaded into RAM once by `VolumeData` and passed by reference to `ProjectionEngine` to avoid expensive memory copying.

### 4.2 2D Projection Frame ($E$) & Video Canvas Frame
* **Data Type:** `numpy.ndarray` (2D).
* **Format:** Inherits unsigned integer type from $M$ during sampling; normalized to `np.uint8` in the range $[0, 255]$ using the global factor `vmax` (FR-8) inside `VideoExporter`.
* **Dimensions & Orientation:** Dynamically computed per plane as $N \times W = \text{round}(D_{ab}) \times \text{round}(D_{bc})$, indexed as `E[row, col]` (where `row = y` runs top-to-bottom from $0$ to $N-1$, and `col = x` runs left-to-right from $0$ to $W-1$, FR-5). Unsampled pixels outside the triangle/trapezoid footprint and out-of-volume samples hold `0`.
* **Padded Canvas Frame:** Inside `VideoExporter`, each normalized $N \times W$ frame is centered onto a fixed `np.uint8` canvas of shape $H_{\max} \times W_{\max}$ (the maximum height and width over all planes in the CSV, FR-7) initialized to `0` (black).
* **Lifecycle & Interface Rationale:** Serves as the data contract between `ProjectionEngine` and `VideoExporter`. Each frame is generated, written immediately to the video stream, and not retained after writing, keeping frame memory $O(1)$ (NFR-2).

### 4.3 Slicing Plane Objects (`Plane`: `TrianglePlane`, `TrapezoidPlane`)
* **Data Type:** Immutable dataclass objects (`@dataclass(frozen=True)`) inheriting from the abstract base class `Plane` (§3.2).
* **Format & Fields:**
  * `row_index: int` – 1-based CSV row number, used for warning and error messages (FR-4).
  * Four 3D corner vectors as 1D `numpy.ndarray` of shape `(3,)` (`float64`): `top_left`, `top_right`, `bottom_left` ($b$), and `bottom_right` ($c$). For a `TrianglePlane`, `top_left` and `top_right` both equal the apex $a$; for a `TrapezoidPlane`, they equal $a'$ and $a''$.
  * `height: int` ($N = \text{round}(D_{ab})$) and `width: int` ($W = \text{round}(D_{bc})$), where $D_{ab}$ is the longer leg and, for a trapezoid, $D_{bc}$ is the longer base (FR-5).
* **Interface Rationale:** Enforces immutability during geometric calculations, guaranteeing that input coordinates cannot be accidentally mutated during vector operations, while hiding the difference between triangles and trapezoids behind one four-corner contract.

### 4.4 Domain Exception Hierarchy
* **Data Type:** Custom exception classes inheriting from a common base class `SlicerError(Exception)`:
  * `InputError` – bad CLI arguments, missing files, wrong extensions, or unwritable output path (exit code `1`, FR-1).
  * `VolumeError` – non-3D volume, dimensions outside $1 \le s < 2^{10}$, or unsupported data type (exit code `2`, FR-2).
  * `PlaneError` – malformed CSV row, leg or coplanarity deviation above 10%, or degenerate dimensions $< 1$ pixel, carrying `row_index` and reason (exit code `2`, FR-3, FR-4).
  * `EncodingError` – video writer initialization or frame write failure (exit code `3`, FR-9).
* **Interface Rationale:** Allows lower-level modules to signal failures cleanly without calling `sys.exit()` themselves, keeping them unit-testable while `AppController` translates each exception into its required exit code (NFR-3).

---

## 5. Data Flow (Execution Pipeline)

The chronological execution pipeline is divided into three distinct phases managed by `AppController`:

### 5.1 Phase 1: Initialization, Ingestion & Up-Front Validation
1. **CLI Invocation:** User executes `python Ex0.py <file.nrrd> <file.csv> <file.mp4>`.
2. **Validation & Instantiation:** `AppController` validates argument count, input file existence, file extensions, and output directory write permissions (raising `InputError` → exit code `1` on failure, FR-1), and initializes `VolumeData`, `PlaneParser`, `ProjectionEngine`, and `VideoExporter`.
3. **One-Time Volume Load:** `VolumeData` reads the `.nrrd` file with axis order `M[x, y, z]`, verifies dimension and type constraints (raising `VolumeError` → exit code `2` on violation, FR-2), locks the 3D matrix $M$ in RAM as read-only (`writeable = False`), and computes the global maximum intensity `vmax` once (FR-8).
4. **Up-Front CSV Parsing & Plane Validation:** `PlaneParser` reads all rows of the 13-column `.csv` file (FR-3), builds the corresponding `TrianglePlane` or `TrapezoidPlane` objects, and runs `validate()` on each (FR-4). Warnings for $1\% < \delta \le 10\%$ are collected and printed; any structural error or deviation above 10% raises `PlaneError` (exit code `2`) before any video file is created.
5. **Canvas Sizing & Encoder Setup:** `AppController` computes the uniform canvas dimensions $H_{\max} = \max_i N_i$ and $W_{\max} = \max_i W_i$ across all validated planes (FR-7) and opens `VideoExporter` (with `(H_max, W_max)`, `vmax`, 30 FPS, and the `mp4v` codec, FR-9).

### 5.2 Phase 2: The Transformation Loop
For each validated `Plane` object in sequence, the following isolated cycle executes:
1. **Plane Dispatch:** `AppController` passes the `Plane` object, along with a reference to $M$, to `ProjectionEngine`.
2. **Vectorized Sampling:** `ProjectionEngine` reads the plane's precomputed height ($N$), width ($W$), and four corner vectors, builds the 2D sampling coordinate grid in a single vectorized step using the fraction-$t$ scanline formulas (FR-5), rounds coordinates to nearest integer voxel indices, applies out-of-bounds and outside-shape masking ($v=0$, FR-5, FR-6), and returns the 2D matrix $E$ of shape $N \times W$.
3. **Normalization, Padding & Encoding:** `AppController` passes $E$ to `VideoExporter`. `VideoExporter` normalizes the bit-depth to `uint8` using the global `vmax` factor (FR-8), centers the frame onto a black $H_{\max} \times W_{\max}$ canvas (FR-7), appends the frame to the `.mp4` stream, and discards the reference to $E$ so per-frame memory remains $O(1)$ (NFR-2).

### 5.3 Phase 3: Finalization, Error Handling & Cleanup
1. **Stream Termination:** Upon processing all planes, `AppController` instructs `VideoExporter` to finalize the video stream.
2. **Resource Release:** `VideoExporter` flushes all remaining buffered data and closes the `.mp4` file handle (guaranteed via `try...finally` / context management even if an error occurs).
3. **Graceful Exit & Exception Mapping:** On success, the application releases the 3D matrix $M$ from RAM and exits with status code `0`. If any domain exception is raised during Phases 1–3, `AppController` catches it, prints a clear diagnostic message without a Python traceback, and exits with the mapped code (`InputError` → `1`, `VolumeError` / `PlaneError` → `2`, `EncodingError` → `3`, NFR-3).


---

## 6. Detailed Projection Algorithm

This section specifies the exact mathematical formulation and vectorized `NumPy` implementation used by `Plane` and `ProjectionEngine` to project a 3D triangle or trapezoid plane onto a 2D discrete matrix $E$ (FR-5, FR-6).

### 6.1 Unified Four-Corner Geometry (`Plane` Layer)
Every slicing plane is represented by four 3D corner vectors $(\mathbf{T}_L, \mathbf{T}_R, \mathbf{B}_L, \mathbf{B}_R) \in \mathbb{R}^3$:
* **Isosceles Triangle ($a, b, c$):**
  $$\mathbf{T}_L = a, \quad \mathbf{T}_R = a, \quad \mathbf{B}_L = b, \quad \mathbf{B}_R = c$$
  Leg lengths: $L_1 = \|b - a\|_2$, $L_2 = \|c - a\|_2$, $D_{ab} = \max(L_1, L_2)$. Base length: $D_{bc} = \|c - b\|_2$.
* **Isosceles Trapezoid ($a', b, a'', c$):**
  $$\mathbf{T}_L = a', \quad \mathbf{T}_R = a'', \quad \mathbf{B}_L = b, \quad \mathbf{B}_R = c$$
  Leg lengths: $L_1 = \|b - a'\|_2$, $L_2 = \|c - a''\|_2$, $D_{ab} = \max(L_1, L_2)$. Base length: $D_{bc} = \max(\|a'' - a'\|_2, \|c - b\|_2)$.
* **Discrete Output Dimensions:** The 2D output matrix $E$ has height $N = \text{round}(D_{ab})$ rows and width $W = \text{round}(D_{bc})$ columns, stored as `E[row, col]` (`row = y` $\in [0, N-1]$, `col = x` $\in [0, W-1]$) and initialized to `0`.

### 6.2 Conceptual Scanline Formulation
In the sequential scanline model, each row $y \in \{0, 1, \dots, N - 1\}$ steps down both legs simultaneously and sweeps a horizontal scanline from the left leg point $\mathbf{a}_1(y)$ to the right leg point $\mathbf{a}_2(y)$:
1. **Fractional Step Along Both Legs:**
   $$t(y) = \frac{y + 1}{N} \quad \text{for } y = 0, 1, \dots, N - 1 \quad \big(t \in (0, 1]\big)$$
2. **Scanline Endpoints:**
   $$\mathbf{a}_1(y) = \mathbf{T}_L + t(y)(\mathbf{B}_L - \mathbf{T}_L), \qquad \mathbf{a}_2(y) = \mathbf{T}_R + t(y)(\mathbf{B}_R - \mathbf{T}_R)$$
3. **Scanline Length & Unit Direction Vector:**
   $$d_{12}(y) = \|\mathbf{a}_2(y) - \mathbf{a}_1(y)\|_2, \qquad \mathbf{dp}(y) = \begin{cases} \dfrac{\mathbf{a}_2(y) - \mathbf{a}_1(y)}{d_{12}(y)} & \text{if } d_{12}(y) > 10^{-9} \\ \mathbf{0} & \text{otherwise} \end{cases}$$
4. **Centered Horizontal Sweep:** For a step offset $x_1 \in [0, d_{12}(y)]$ along the scanline, the 3D sample point and centered column index are:
   $$\mathbf{p}(y, x_1) = \mathbf{a}_1(y) + x_1\,\mathbf{dp}(y), \qquad x = \frac{W}{2} - \frac{d_{12}(y)}{2} + x_1$$
   Inverting the centering relation for each integer column $x \in \{0, 1, \dots, W - 1\}$ gives:
   $$x_1(y, x) = x - \frac{W - d_{12}(y)}{2}$$
   A column $x$ on row $y$ lies inside the triangle/trapezoid if and only if $0 \le x_1(y, x) \le d_{12}(y)$.

### 6.3 Vectorized `NumPy` Implementation (`ProjectionEngine`)
To achieve $\ge 100\text{ FPS}$ on $500^3$ volumes (NFR-1), `ProjectionEngine.project(M, plane)` executes the entire projection in five vectorized array operations with zero Python loops:
1. **1D Row Arrays (shape `(N, 1)` and `(N, 3)`):**
   ```python
   y   = np.arange(N, dtype=np.float64)[:, None]          # (N, 1)
   t   = (y + 1.0) / N                                    # (N, 1)
   a1  = T_L[None, :] + t * (B_L - T_L)[None, :]          # (N, 3)
   a2  = T_R[None, :] + t * (B_R - T_R)[None, :]          # (N, 3)
   vec = a2 - a1                                          # (N, 3)
   d12 = np.linalg.norm(vec, axis=1, keepdims=True)       # (N, 1)
   dp  = np.divide(vec, d12, out=np.zeros_like(vec), where=(d12 > 1e-9))
   ```
2. **2D Scanline Offset & Shape Mask (shape `(N, W)`):**
   ```python
   x          = np.arange(W, dtype=np.float64)[None, :]   # (1, W)
   x1         = x - (W - d12) / 2.0                       # (N, W)
   mask_shape = (x1 >= 0.0) & (x1 <= d12)                 # (N, W) bool
   ```
3. **3D Sample Coordinates & Nearest-Neighbor Rounding (shape `(N, W, 3)`):**
   ```python
   P   = a1[:, None, :] + x1[:, :, None] * dp[:, None, :] # (N, W, 3)
   idx = np.rint(P).astype(np.intp)                       # (N, W, 3)
   ```
4. **Volume Boundary Mask (shape `(N, W)`):**
   ```python
   ix, iy, iz = idx[:, :, 0], idx[:, :, 1], idx[:, :, 2]
   mask_vol   = (ix >= 0) & (ix < sx) & (iy >= 0) & (iy < sy) & (iz >= 0) & (iz < sz)
   valid      = mask_shape & mask_vol                     # (N, W) bool
   ```
5. **Single-Pass Masked Voxel Gather (shape `(N, W)`):**
   ```python
   E        = np.zeros((N, W), dtype=M.dtype)
   E[valid] = M[ix[valid], iy[valid], iz[valid]]
   return E
   ```

### 6.4 Summary of Resolved Algorithmic Edge Cases
| Edge Case | Resolution in §6 |
|---|---|
| **Apex division by zero ($d_{12} = 0$)** | $t = (y + 1) / N$ steps past the apex before row 0, and `np.divide(..., where=(d12 > 1e-9))` guards any zero-width scanline. |
| **Column off-by-one ($x == W$)** | Evaluating $x_1(y, x)$ over integer columns $x \in [0, W - 1]$ and masking with $0 \le x_1 \le d_{12}$ makes column overflow impossible. |
| **Slight leg-length mismatch (1%–10%)** | Parametric fraction $t \in (0, 1]$ keeps both legs synchronized from top to bottom while matching unit-vector stepping when $L_1 = L_2$. |
| **Continuous 3D point vs. discrete voxel** | `np.rint(P).astype(np.intp)` rounds to nearest integer voxel coordinates before bounds checking (FR-5, FR-6). |
| **Pixels outside shape or outside volume** | $E$ is initialized to `0` and populated only where `mask_shape & mask_vol` is true. |
| **Transposed image orientation** | $E$ has shape `(N, W)` indexed as `E[row, col] = E[y, x]`. |


---

## 7. Dataset Specification

The system is validated and benchmarked against two complementary dataset categories: a shared classroom dataset of volumetric scans and trajectory files, and a suite of deterministic synthetic datasets for automated testing and FPS benchmarking.

### 7.1 Shared Classroom Dataset (End-to-End & Visual Verification)
A shared collection of real-world 3D volumetric `.nrrd` files paired with 13-column `.csv` plane trajectory files:
* **Volumetric Scans (`.nrrd`):** Multiple 3D medical and volumetric datasets spanning different grid resolutions within $1 \le sx, sy, sz < 2^{10}$ and unsigned integer bit depths (`uint8`, `uint16`, `uint32`, FR-2).
* **Plane Trajectories (`.csv`):** Curated sequences of 3-point (triangle) and 4-point (trapezoid) rows exercising:
  * Axis-aligned sweeps (along X, Y, and Z) and arbitrary oblique slicing angles.
  * Mixed triangle (`3`) and trapezoid (`4`) rows within the same CSV file, including varying plane dimensions to exercise centered canvas padding (FR-7).
  * Coordinates extending outside the volume bounds (e.g., negative coordinates) to verify zero-masking ($v = 0$, FR-6).
  * Slightly non-isosceles rows ($1\% < \delta \le 10\%$) to verify warning generation and fraction-$t$ projection (FR-4, FR-5).

### 7.2 Synthetic & Benchmark Datasets (Automated Testing)
Generated programmatically by the test and benchmark suite so unit and performance tests run deterministically without external file dependencies:

| Dataset Category | Specification | Purpose |
|---|---|---|
| **Analytical Unit-Test Volumes** | Small 3D arrays ($16^3$ to $64^3$) in `uint8`, `uint16`, and `uint32` with known closed-form voxel values (e.g., $M[x, y, z] = x + y + z$ or single bright planes). | Verify pixel-exact projection accuracy (FR-5), global `vmax` normalization (FR-8), and axis ordering (FR-2). |
| **Performance Benchmark Volume** | A $500 \times 500 \times 500$ `uint8` volume ($125\text{ MB}$) paired with a 100-row CSV of $500 \times 500$ slicing planes. | Measure pure projection throughput against the mandatory $\ge 30\text{ FPS}$ floor and $\ge 100\text{ FPS}$ target (NFR-1). |
| **Invalid & Boundary Fixtures** | Volumes with dimensions $\ge 2^{10}$ or signed/float types; CSV rows with wrong column counts, $\delta > 10\%$ leg mismatch, non-coplanar trapezoids, or zero-area planes. | Verify fast-fail error messages and CLI exit codes `1`, `2`, and `3` (FR-1, FR-2, FR-4, NFR-3). |


---

## 8. Testing Strategy & Experimental Evaluation

This section defines the automated testing strategy, end-to-end CLI demo verification, performance benchmarking protocol, and requirement traceability matrix (NFR-4).

### 8.1 Unit & Component Testing (`pytest`)
Each module in §3 is tested in isolation using synthetic in-memory fixtures (§7.2):
* **`test_volume_data.py`:** Verifies loading of valid `uint8`, `uint16`, and `uint32` NRRD volumes, `M[x, y, z]` axis ordering, `flags.writeable == False`, accurate `vmax` computation, and `VolumeError` on non-3D arrays, dimensions $\ge 2^{10}$, or signed/floating-point types (FR-2, FR-8).
* **`test_plane_geometry.py`:** Verifies four-corner mapping and rounded dimensions $(N, W)$ for `TrianglePlane` and `TrapezoidPlane`; silent acceptance when $\delta \le 1\%$; warning generation when $1\% < \delta \le 10\%$; and `PlaneError` when $\delta > 10\%$, when trapezoid points are non-coplanar ($>10\%$), or when $N < 1$ or $W < 1$ (FR-4, FR-5).
* **`test_plane_parser.py`:** Verifies parsing of the 13-column CSV format, header and blank-line skipping, mixed triangle (`3`) and trapezoid (`4`) rows, and immediate `PlaneError` with the exact 1-based row number on malformed cells or point-count mismatches (FR-3, FR-4).
* **`test_projection_engine.py`:** Verifies pixel-exact slice values on analytical volumes ($M[x, y, z] = x + y + z$), equivalence between vectorized projection and sequential scanline stepping on isosceles shapes, zero-masking of pixels outside a triangle's footprint, and zero-masking ($v = 0$) of negative or out-of-volume coordinates (FR-5, FR-6, §6).
* **`test_video_exporter.py`:** Verifies global `vmax` scaling from `uint16`/`uint32` to `uint8` $[0, 255]$ (including all-zero volumes), centered black padding onto the $H_{\max} \times W_{\max}$ canvas, and clean file-handle teardown (FR-7, FR-8, FR-9).

### 8.2 End-to-End CLI Demo Verification (`Ex0.py`)
Integration tests invoke the full command-line entry point:
```bash
python Ex0.py <file.nrrd> <file.csv> <file.mp4>
```
* **Valid Demo Run:** Executes `Ex0.py` on a shared classroom `.nrrd` and `.csv` pair, asserts exit code `0`, opens the generated `.mp4` with `cv2.VideoCapture`, and verifies that:
  1. The video stream opens cleanly and has non-zero byte size.
  2. The encoded frame count equals the exact number of plane rows in the CSV file.
  3. The frame resolution equals $(H_{\max}, W_{\max})$ across all planes in the CSV.
  4. The video metadata reports a playback rate of 30 FPS.
* **Fast-Fail Error Runs:** Invokes `Ex0.py` with missing/wrong-extension paths (asserts exit code `1`), an invalid volume or a CSV containing a bad row (asserts exit code `2` and verifies that no partial `.mp4` file is left on disk), and an unencodable output stream (asserts exit code `3`, NFR-3).

### 8.3 Performance Benchmark & Experimental Evaluation
* **500³ Throughput Benchmark (NFR-1):** Runs `ProjectionEngine.project` over 100 planes ($500 \times 500$ pixels each) slicing through a $500 \times 500 \times 500$ `uint8` volume. After 1 warm-up pass, the median per-frame time and FPS across at least 3 runs are recorded. The test asserts $\ge 30\text{ FPS}$ ($\le 33.3\text{ ms/frame}$) and evaluates progress toward the $\ge 100\text{ FPS}$ ($\le 10.0\text{ ms/frame}$) target.
* **Experimental Report & Video Artifact:** An experiment is executed on the shared classroom dataset via `Ex0.py`, producing the output `.mp4` video and a concise results summary documenting:
  * Test hardware and OS environment (CPU/SoC, RAM, Python & NumPy versions).
  * Input volume dimensions, bit depth, and CSV trajectory length/types.
  * Measured pure projection FPS vs. end-to-end pipeline FPS (including NRRD load and MP4 encoding), and constant $O(1)$ frame-memory behavior.
  * Visual inspection of the generated `.mp4` slices (smooth progression across frames, centered padding, and clean black boundaries for out-of-volume coordinates).

### 8.4 Requirements Traceability Matrix
| Req ID | Summary | Primary Module(s) | Verification Test |
|---|---|---|---|
| **FR-1** | CLI parsing & path validation (exit code 1) | `AppController` | `test_cli_demo.py` |
| **FR-2** | NRRD ingestion, bounds & dtype validation | `VolumeData` | `test_volume_data.py` |
| **FR-3** | 13-column CSV parsing (3- & 4-point rows) | `PlaneParser` | `test_plane_parser.py` |
| **FR-4** | Plane validation (1% silent, 1–10% warn, >10% abort) | `Plane`, `PlaneParser` | `test_plane_geometry.py`, `test_plane_parser.py` |
| **FR-5** | Vectorized projection & outside-shape zeroing | `ProjectionEngine` | `test_projection_engine.py` |
| **FR-6** | Out-of-volume boundary masking ($v = 0$) | `ProjectionEngine` | `test_projection_engine.py` |
| **FR-7** | Uniform $H_{\max} \times W_{\max}$ canvas & centered black padding | `AppController`, `VideoExporter` | `test_video_exporter.py`, `test_cli_demo.py` |
| **FR-8** | Global `vmax` normalization to `uint8` | `VolumeData`, `VideoExporter` | `test_video_exporter.py` |
| **FR-9** | MP4 export (30 FPS, `mp4v`, CSV order) | `VideoExporter` | `test_video_exporter.py`, `test_cli_demo.py` |
| **NFR-1** | $\ge 30\text{ FPS}$ mandatory, $\ge 100\text{ FPS}$ target on $500^3$ | `ProjectionEngine` | `test_benchmark_fps.py` |
| **NFR-2** | Single volume allocation & $O(1)$ frame streaming | `VolumeData`, `AppController` | `test_cli_demo.py` |
| **NFR-3** | Fault tolerance & exit codes (`0, 1, 2, 3`) | `AppController`, `SlicerError` | `test_cli_demo.py` |
| **NFR-4** | Decoupled module testability & traceability | All modules (§3, §4) | Full `pytest` suite (§8.1–§8.4) |
| **NFR-5** | Python 3.10+ cross-platform portability | Environment / dependencies | CI / local `pytest` execution |
