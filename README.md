# NRRD-to-Video-Slicer

A high-performance, Object-Oriented Python CLI system that slices 3D volumetric NRRD datasets along arbitrary 3-point (triangle) and 4-point (trapezoid) planes defined in a CSV trajectory and compiles the projections into an MP4 video.

---

## 1. Problem Statement & Mathematical Definition

### Problem Statement
Given a 3D raster data matrix ($M$) representing volumetric data (such as medical MRI or CT scans) and a sequence of slicing planes ($P$) in 3D space, the objective is to compute and extract the 2D matrix ($E$ — output image) representing the cross-sectional projection of each plane $P$ within the volume $M$, and encode the sequence of slices into an `.mp4` video stream. Because the general continuous-to-discrete plane projection problem is not well-defined for direct raster implementation, this project establishes a complete software engineering specification, modular Object-Oriented design, and vectorized algorithm.

### Formal Definition
* **3D Volumetric Input ($M$):** A 3D matrix of dimensions $sx \times sy \times sz$, where $1 \le sx, sy, sz < 2^{10}$ ($1024$) and integer voxel coordinates satisfy $0 \le x < sx$, $0 \le y < sy$, $0 \le z < sz$. Each voxel entry $M[x][y][z]$ holds an unsigned integer value ($8, 16,$ or $32\text{-bit}$).
* **Slicing Plane ($P$):** Defined spatially in voxel coordinates by either:
  * **3 points ($a, b, c$):** Forming an **isosceles triangle** where $dist(a,b) = dist(a,c) = D_{ab}$, and base length $D_{bc} = dist(b,c)$.
  * **4 points ($a', b, a'', c$):** Forming an **isosceles trapezoid** defined by two coplanar leg vectors of equal length ($\vec{a'b}$ and $\vec{a''c}$).
* **2D Projection Output ($E$):** A 2D matrix of dimensions $\text{round}(D_{ab}) \times \text{round}(D_{bc})$ populated by sampling $M$ at nearest-neighbor (rounded) voxel indices. Any sample point $p(x,y,z)$ falling outside the boundaries of $M$ or outside the triangle/trapezoid footprint is assigned a default value of $v = 0$.

---

## 2. Scope of Work (SOW) & Project Agreement

### 2.1 Objectives
1. **Design & Specify an Under-Defined Algorithm:** Resolve all discrete rasterization, boundary, and geometric tolerance ambiguities of 3D plane projection in formal engineering documents before coding.
2. **Object-Oriented Architecture (SOLID):** Decouple NRRD file ingestion, CSV parsing, plane geometry, vectorized math, and MP4 video encoding into independent, unit-testable components.
3. **High-Throughput Runtime Efficiency:** Achieve **$\ge 30\text{ FPS}$ mandatory** and **$\ge 100\text{ FPS}$ target** on a $500^3$ byte matrix using `NumPy` array broadcasting.

### 2.2 Deliverables
| Deliverable ID | Artifact | Description |
| :--- | :--- | :--- |
| **D-1** | [`/docs`](docs/) Specification Suite | [SRS.md](docs/SRS.md), [SDD.md](docs/SDD.md), [EDD.md](docs/EDD.md), and [STP.md](docs/STP.md). |
| **D-2** | [`Ex0.py`](Ex0.py) & [`src/`](src/) Package | Modular OOP implementation of the CLI projection pipeline. |
| **D-3** | [`tests/`](tests/) Automated Test Suite | Unit, integration, CLI demo, and $500^3$ FPS benchmark tests (`TC-01..TC-15`). |
| **D-4** | [`results/`](results/) Experiment & Video | [`demo_output.mp4`](results/demo_output.mp4) and [`EXPERIMENT.md`](results/EXPERIMENT.md) benchmark evaluation. |

### 2.3 In Scope & Out of Scope
**In Scope:**
* Loading 3D `.nrrd` volumes and validating dimensionality ($1 \le sx, sy, sz < 2^{10}$) and unsigned integer types (`uint8`, `uint16`, `uint32`, plus promotion of non-negative signed integer scans such as `short` MRI files).
* Parsing and validating 13-column `.csv` plane trajectory files containing 3-point triangles and 4-point trapezoids (with $\le 1\%$ silent, $1\%\text{–}10\%$ warning, and $>10\%$ abort tolerances).
* Executing vectorized 3D-to-2D geometric plane projection with nearest-neighbor voxel sampling and zero-masking ($v=0$) for out-of-volume or outside-shape pixels.
* Global volume-maximum (`vmax`) brightness normalization to 8-bit grayscale and centered black-canvas padding ($H_{\max} \times W_{\max}$) into a 30 FPS `.mp4` video.

**Out of Scope:**
* Graphical User Interfaces (GUI) or interactive 3D viewport rendering.
* Medical diagnostic interpretation or persistent database storage.
* World/physical (RAS/LPS) coordinate transformation matrices — all CSV coordinates are specified directly in voxel index space.
* Trilinear or higher-order interpolation (nearest-neighbor rounding is used per specification).
* Plane geometries other than isosceles triangles and isosceles trapezoids.

### 2.4 Milestones & Review Gates
| Gate | Milestone | Exit Outcome |
| :--- | :--- | :--- |
| **SRR** | System Requirements Review | [docs/SRS.md](docs/SRS.md) baselined with testable `FR-1..9`, `NFR-1..5`, and Use Cases `UC-01..04`. |
| **PDR** | Preliminary Design Review | [docs/SDD.md](docs/SDD.md) architecture, 6-component decomposition, and `ADR-01..04` approved. |
| **CDR** | Critical Design Review | [docs/EDD.md](docs/EDD.md) vectorized algorithm and [docs/STP.md](docs/STP.md) test plan traced to requirements. |
| **TRR & Demo** | Test Readiness & Final Acceptance | All 15 STD test cases (`TC-01..15`) pass; `Ex0.py` demo achieves **435.3 FPS** on $500^3$ volume. |

### 2.5 Acceptance Criteria
1. **CLI Contract:** `python Ex0.py <file.nrrd> <file.csv> <file.mp4>` exits with `0` on valid inputs and produces a playable 30 FPS `.mp4` whose frame count equals the number of CSV plane rows.
2. **Performance Floor & Target:** Pure projection throughput on a $500^3$ `uint8` volume exceeds the mandatory **30 FPS** floor and meets the **100+ FPS** target (`NFR-1`).
3. **Fault Tolerance:** Malformed CLI arguments (`exit 1`), invalid NRRD/CSV data (`exit 2`), or encoding errors (`exit 3`) terminate cleanly with a diagnostic message on `stderr` and leave no partial `.mp4` file on disk (`NFR-3`).
4. **Verification:** 100% of automated tests in `pytest` (`TC-01`–`TC-15`) pass.

### 2.6 Assumptions & Roles
* **Assumptions:** Input CSV coordinates are in discrete voxel indices; host machine has Python 3.10+ (or Docker) and sufficient RAM for one $500^3$ volume ($\le 500\text{ MB}$).
* **Roles:** Project Lead / Architect / Developer / QA executed under the course hybrid gate-and-iteration workflow.

---

## 3. Quick Start: Install and Run

### Option A: Local Python Environment (Python 3.10+)
```bash
git clone <repository-url>
cd NRRD-to-Video-Slicer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Option B: Docker Compose
```bash
docker compose build
docker compose run --rm app python Ex0.py data/croissant.nrrd data/croissant_sweep.csv results/demo_output.mp4
```

---

## 4. Usage Example (CLI Demo)

Run the main entry point [`Ex0.py`](Ex0.py) with three positional arguments (`<file.nrrd> <file.csv> <file.mp4>`):

```bash
# Generate a 60-frame sweep video from a 500x500x500 volume
python Ex0.py data/croissant.nrrd data/croissant_sweep.csv results/demo_output.mp4

# Run on the 4-plane classroom sample trajectory
python Ex0.py data/MRHead_1.nrrd data/sample_planes.csv results/sample_planes_output.mp4
```

* **CSV Format:** 13 comma-separated columns (`Number of Point, x1,y1,z1, x2,y2,z2, x3,y3,z3, x4,y4,z4`), where column 1 is `3` (triangle: $a, b, c$) or `4` (trapezoid: $a', b, a'', c$).
* **Exit Codes:** `0` = Success, `1` = CLI/path error, `2` = Invalid NRRD volume or CSV plane geometry, `3` = MP4 encoding error.

---

## 5. Configuration & Environment

* **Runtime:** Python 3.10+ (tested on Python 3.11 / 3.12 across macOS, Linux, and Docker `aarch64`/`x86_64`).
* **Dependencies ([`requirements.txt`](requirements.txt)):**
  * `numpy>=1.24.0` — Vectorized spatial grid broadcasting and array masking.
  * `pynrrd>=1.0.0` — Reading 3D `.nrrd` medical/volumetric headers and rasters.
  * `opencv-python-headless>=4.8.0` — Encoding `.mp4` (`mp4v`) video streams.
  * `pytest>=7.4.0` — Automated test and benchmark execution.

---

## 6. Running the Tests & Benchmarks

```bash
# Run the full unit, integration, CLI demo, and benchmark test suite
pytest

# Run the 500^3 volume FPS throughput benchmark with console output
pytest -v -s tests/test_benchmark_fps.py

# Reproduce the full classroom dataset experiment and regenerate results/EXPERIMENT.md
python -m src.run_experiment
```

---

## 7. Project Structure & Documentation (`/docs`)

Following the course Software Engineering documentation chain, each engineering phase is documented in its dedicated specification under [`/docs`](docs/):

| Document | Role in Chain | Key Question Answered |
| :--- | :--- | :--- |
| **[docs/SRS.md](docs/SRS.md)** | **Software Requirements Specification** | *What must the system do?* (FRs, NFRs, External Interfaces, Use Cases `UC-01..04`) |
| **[docs/SDD.md](docs/SDD.md)** | **Software Design Document** | *How is the system structured?* (Component architecture, Class diagram, Deployment, ADRs) |
| **[docs/EDD.md](docs/EDD.md)** | **Engineering Design Document** | *How is each part built?* (Detailed projection algorithm, NumPy vectorization, Sequence & State diagrams, Edge cases) |
| **[docs/STP.md](docs/STP.md)** | **Software Test Plan & Description** | *How do we prove it works?* (Classroom & synthetic datasets, Test strategy, Risk register, Test cases `TC-01..15`) |
| **[results/EXPERIMENT.md](results/EXPERIMENT.md)** | **Experimental Evaluation Report** | *What are the measured results?* (435–1741 FPS benchmarks and demo video verification) |

```text
NRRD-to-Video-Slicer/
├── Ex0.py                     # CLI entry point: python Ex0.py <file.nrrd> <file.csv> <file.mp4>
├── README.md                  # Repository overview, SOW scope, quick start, and doc index
├── docs/                      # Software Engineering Documentation Chain
│   ├── SRS.md                 # Software Requirements Specification & Use Cases
│   ├── SDD.md                 # Software Design Document (Architecture & ADRs)
│   ├── EDD.md                 # Engineering Design Document (Detailed Algorithm & Flows)
│   └── STP.md                 # Software Test Plan, Datasets & Test Descriptions (STD)
├── src/                       # Modular OOP source package
│   ├── app_controller.py      # Execution orchestrator & CLI error mapping
│   ├── volume_data.py         # NRRD ingestion, validation & read-only matrix holder
│   ├── plane.py               # Plane ABC, TrianglePlane & TrapezoidPlane geometry
│   ├── plane_parser.py        # 13-column CSV reader & plane factory
│   ├── projection_engine.py   # Stateless vectorized 3D-to-2D projection core
│   ├── video_exporter.py      # Global vmax normalization, canvas padding & MP4 writer
│   ├── exceptions.py          # Domain exception hierarchy (SlicerError subclasses)
│   └── run_experiment.py      # Classroom dataset benchmark runner
├── tests/                     # Automated pytest suite (unit, CLI integration, FPS benchmark)
├── data/                      # Classroom NRRD volumes & CSV plane trajectories
└── results/                   # Output MP4 demo video & EXPERIMENT.md report
```

---

## 8. How to Contribute (Docs-as-Code & Definition of Done)

1. **Branch & Pull Request:** Create a feature/fix branch and open a Pull Request against `main`.
2. **Docs-as-Code:** Any change to system behavior, CLI interfaces, or component design must update the corresponding specification in [`/docs`](docs/) (`SRS.md`, `SDD.md`, `EDD.md`, `STP.md`) in the same commit/PR.
3. **Definition of Done:** A change is complete only when all unit, CLI integration, and benchmark tests pass (`pytest`) and requirement traceability in [docs/SRS.md](docs/SRS.md) and [docs/STP.md](docs/STP.md) remains 100% green.

---

## 9. License & Contact

Developed for **Introduction to Software Engineering (Intro2SE)** — School of Computer Science, Ariel University.
