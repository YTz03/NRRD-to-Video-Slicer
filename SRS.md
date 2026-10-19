# Software Requirements Specification (SRS)
**Project:** High-Performance 3D Volumetric Plane Projection (`Ex0.py`)

---

## 1. Introduction & System Goals

### 1.1 System Overview (Alignment)
This document specifies the functional requirements, non-functional constraints, software architecture, and execution pipeline for the 3D Volume Projection system. The software operates as an automated data-transformation pipeline: it ingests 3D volumetric raster data (`.nrrd` files), parses spatial trajectory coordinates representing slicing planes (`.csv` files), computes 2D planar projections (isosceles triangles or trapezoids), and encodes the sequential frames into a video file (`.mp4`).

### 1.2 Scope & Boundaries
The system is strictly defined as a Command-Line Interface (CLI) application invoked via:
```bash
python Ex0.py <file.nrrd> <file.csv> <file.mp4>
```
**In Scope:**
* Parsing 3D volumetric matrices and validating structural bounds.
* Executing vectorized geometric projection of 3D planes onto 2D discrete grids.
* Normalizing and encoding sequential 2D matrices into an `.mp4` video stream.

**Out of Scope:**
* Graphical User Interfaces (GUI) or interactive 3D rendering.
* Medical diagnostic interpretation or persistent database storage.

### 1.3 Engineering Priorities (The "North Star")
In strict accordance with the assignment guidelines, solving the mathematical projection is secondary to the quality of the software engineering. All design decisions are governed by two core priorities:
* **Object-Oriented Design (OOD & SOLID):** Enforcing strict separation of concerns—specifically the Single Responsibility Principle (SRP)—to decouple file I/O, mathematical computation, and media encoding into independent, testable modules.
* **Runtime Efficiency:** Bypassing standard Python nested loops via vectorized `NumPy` array operations to guarantee a minimum rendering speed of **30 FPS**, with an optimization target of **100+ FPS** on $500^3$ byte matrices.

---

## 2. System Requirements

### 2.1 Functional Requirements (FR)
* **FR-1 (CLI Parsing):** The system shall accept exactly three command-line arguments: input `.nrrd` path, input `.csv` path, and output `.mp4` path, validating their existence and file extensions before execution.
* **FR-2 (Volumetric Ingestion):** The system shall parse `.nrrd` files into a 3D matrix $M$ of dimensions $sx \times sy \times sz$ (where $1 \le sx, sy, sz < 2^{10}$) supporting unsigned integer formats (`uint8`, `uint16`, `uint32`).
* **FR-3 (Trajectory Parsing):** The system shall read `.csv` rows sequentially, extracting 3 spatial points (isosceles triangle) or 4 spatial points (isosceles trapezoid) in $(x, y, z)$ coordinates.
* **FR-4 (Vectorized Plane Projection):** For each coordinate set, the system shall compute the plane dimensions ($D_{ab} \times D_{bc}$), derive normalized directional vectors, and sample the 3D volume $M$ using nearest-neighbor (rounded) integer indices to construct the 2D matrix $E$.
* **FR-5 (Boundary Handling):** Any sampled 3D coordinate falling outside the valid bounds of $M$ ($x \notin [0, sx-1]$, $y \notin [0, sy-1]$, or $z \notin [0, sz-1]$) shall automatically be assigned a default voxel value of $v = 0$ without raising runtime exceptions.
* **FR-6 (Video Normalization & Export):** The system shall normalize higher bit-depth frames (`uint16`/`uint32`) to 8-bit unsigned integers (`uint8`) and encode the sequence of 2D matrices into a valid `.mp4` file.

### 2.2 Non-Functional Requirements (NFR)
* **NFR-1 (Performance):** Frame generation must execute in $\le 33.3\text{ ms}$ per frame ($\ge 30\text{ FPS}$), targeting $\le 10\text{ ms}$ per frame ($\ge 100\text{ FPS}$) for $500^3$ volumes using `NumPy` broadcasting.
* **NFR-2 (Memory Footprint):** The 3D matrix $M$ must be allocated in RAM once. Generated 2D frames ($E$) must be streamed directly to the video encoder and garbage-collected immediately to ensure $O(1)$ frame-memory overhead across arbitrarily long CSV files.
* **NFR-3 (Robustness & Fault Tolerance):** The system must gracefully handle degenerate geometric inputs (e.g., zero-distance between coinciding points preventing division-by-zero), malformed CSV rows, and I/O permission errors with clear diagnostic messages.

---

## 3. System Architecture (Classes & Modules)

To satisfy OOD principles, the system is divided into four decoupled modules. This architecture enables isolated unit testing and prevents changes in I/O formats from impacting the mathematical core.

### 3.1 `VolumeData` (Data Ingestion Layer)
* **Role:** Dedicated 3D data parser and state holder. Abstracts file-reading complexity away from the algorithmic engine.
* **Design Benefit (Decoupling):** If future requirements introduce new medical imaging formats (e.g., DICOM), only `VolumeData` requires modification.
* **Responsibilities:**
  * Load `.nrrd` files using `pynrrd`.
  * Validate grid constraints ($1 \le sx, sy, sz < 2^{10}$) and unsigned integer data types (`uint8`, `uint16`, `uint32`).
  * Expose the 3D volume as a read-only in-memory `numpy.ndarray` ($M$).

### 3.2 `ProjectionEngine` (Algorithmic Core)
* **Role:** Stateless mathematical engine. Computes 2D slicing planes completely independently of file I/O or video codecs.
* **Design Benefit (Testability):** Supports isolated Unit Testing by accepting synthetic 3D `NumPy` arrays and mock coordinate tuples without touching the filesystem.
* **Responsibilities:**
  * Compute Euclidean distances ($D_{ab}, D_{bc}$) and normalized step vectors, guarding against zero-length vectors.
  * Construct a 2D sampling grid via `NumPy` vectorization (`np.linspace` / broadcasting), eliminating Python `for` loops over pixels.
  * Round spatial coordinates to nearest integer indices, apply boolean boundary masks (setting out-of-bounds indices to $v = 0$), and extract the 2D matrix ($E$).

### 3.3 `VideoExporter` (Presentation Layer)
* **Role:** Media stream compiler. Transforms raw 2D mathematical matrices into a standard `.mp4` video stream.
* **Design Benefit (Flexibility):** Decouples output encoding from geometry calculation. Switching output formats (e.g., to `.avi` or `.png` sequences) requires zero changes to `ProjectionEngine`.
* **Responsibilities:**
  * Initialize the video writer stream (codec, FPS, and spatial resolution locked to the target frame dimensions).
  * Normalize incoming 2D matrices ($E$) from `uint16`/`uint32` into standard `uint8` $[0, 255]$ grayscale frames, ensuring dimensional consistency across frames.
  * Write sequential frames to the video buffer and safely close/release the `.mp4` file descriptor upon completion.

### 3.4 `AppController` (Execution Orchestrator / `Ex0.py`)
* **Role:** Central coordinator that wires the decoupled modules together and manages the execution lifecycle.
* **Design Benefit (Maintainability):** Keeps top-level workflow linear, clean, and readable while centralizing exception handling.
* **Responsibilities:**
  * Parse and validate CLI arguments (`<file.nrrd> <file.csv> <file.mp4>`).
  * Instantiate `VolumeData`, `ProjectionEngine`, and `VideoExporter`.
  * Stream rows from the `.csv` file, route coordinates to the engine, and pipe resulting 2D frames to the exporter.

---

## 4. Core Data Structures

To guarantee high-speed vectorized execution and strict interface contracts between modules, the system relies on contiguous memory arrays rather than standard Python lists.

### 4.1 3D Volume Matrix ($M$)
* **Data Type:** `numpy.ndarray` (3D)
* **Format:** Unsigned integers (`np.uint8`, `np.uint16`, or `np.uint32`).
* **Dimensions:** $sx \times sy \times sz$ where $1 \le sx, sy, sz < 2^{10}$.
* **State & Memory Rationale:** Represents the immutable scanned volume. Loaded into RAM once by `VolumeData` and passed by reference to `ProjectionEngine` to avoid expensive memory copying.

### 4.2 2D Projection Frame ($E$)
* **Data Type:** `numpy.ndarray` (2D)
* **Format:** Inherits unsigned integer type from $M$ during sampling; normalized to `np.uint8` inside `VideoExporter`.
* **Dimensions:** Dynamically computed as $\text{round}(D_{ab}) \times \text{round}(D_{bc})$.
* **Lifecycle & Interface Rationale:** Serves as the data contract between `ProjectionEngine` and `VideoExporter`. Each frame is generated, written immediately to the video stream, and dereferenced from RAM to prevent memory exhaustion.

### 4.3 Spatial Trajectory (Plane Coordinates)
* **Data Type:** `tuple[tuple[float, float, float], ...]`
* **Format:** 3 or 4 3D points `((x1, y1, z1), (x2, y2, z2), (x3, y3, z3), ...)` parsed per `.csv` row.
* **Interface Rationale:** Enforces immutability during geometric calculations, guaranteeing that input coordinates cannot be accidentally mutated during vector operations.

---

## 5. Data Flow (Execution Pipeline)

The chronological execution pipeline is divided into three distinct phases managed by `AppController`:

### 5.1 Phase 1: Initialization & Ingestion
1. **CLI Invocation:** User executes `python Ex0.py <file.nrrd> <file.csv> <file.mp4>`.
2. **Validation & Instantiation:** `AppController` validates file paths and initializes `VolumeData`, `ProjectionEngine`, and `VideoExporter`.
3. **One-Time Volume Load:** `VolumeData` reads the `.nrrd` file, verifies dimension and type constraints, and locks the 3D matrix $M$ in RAM.

### 5.2 Phase 2: The Transformation Loop
For each row in the `.csv` trajectory file, the following isolated cycle executes:
1. **Coordinate Parsing:** `AppController` parses the row into an immutable tuple of 3D points and passes it, along with a reference to $M$, to `ProjectionEngine`.
2. **Vectorized Sampling:** `ProjectionEngine` calculates distances ($D_{ab}, D_{bc}$) and normalized direction vectors, builds the 2D sampling coordinate grid in a single vectorized step, applies out-of-bounds masking ($v=0$), and returns the 2D matrix $E$.
3. **Encoding & Flushing:** `AppController` passes $E$ to `VideoExporter` (initializing the writer dimensions on the first valid frame). `VideoExporter` normalizes the bit-depth to `uint8`, appends the frame to the `.mp4` stream, and releases $E$ from memory.

### 5.3 Phase 3: Finalization & Cleanup
1. **Stream Termination:** Upon reaching the end of the `.csv` file, `AppController` instructs `VideoExporter` to finalize the video stream.
2. **Resource Release:** `VideoExporter` flushes all remaining buffered data and closes the `.mp4` file handle (guaranteed via `try...finally` / context management even if an error occurs).
3. **Graceful Exit:** The application releases the 3D matrix $M$ from RAM and exits with status code `0`.
