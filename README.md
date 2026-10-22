# NRRD-to-Video-Slicer

A high-performance, Object-Oriented Python system for extracting 2D plane projections from 3D volumetric NRRD data based on spatial CSV coordinates and compiling them into an MP4 video sequence.

---

## 1. Problem Statement & Mathematical Definition

### Problem Statement
Given a 3D raster data matrix ($M$) representing volumetric data (such as medical MRI scans) and a slicing plane ($P$) in 3D space, the objective is to compute and extract the 2D matrix ($E$ - output image) representing the projection of plane $P$ within the volume $M$. Because the general projection problem is not strictly defined for discrete raster implementation, this project establishes a well-defined, robust, and runtime-efficient software design.

### Formal Definition
* **3D Volumetric Input ($M$):** A 3D matrix of dimensions $sx \times sy \times sz$, where $1 \le sx, sy, sz < 2^{10}$ ($1024$), and coordinates satisfy $0 \le x < sx$, $0 \le y < sy$, $0 \le z < sz$. Each voxel entry $M[x][y][z]$ holds an unsigned integer value ($8, 16,$ or $32\text{-bit}$).
* **Slicing Plane ($P$):** Defined spatially by either:
  * **3 points ($a, b, c$):** Forming an **isosceles triangle** where $dist(a,b) = dist(a,c) = D_{ab}$, and base length $D_{bc} = dist(b,c)$.
  * **4 points ($a', b, a'', c$):** Forming an **isosceles trapezoid** defined by two coplanar vectors of equal length ($\vec{a'b}$ and $\vec{a''c}$).
* **2D Projection Output ($E$):** A 2D matrix of dimensions $\text{round}(D_{ab}) \times \text{round}(D_{bc})$ populated by sampling the 3D volume $M$ along normalized directional vectors across the plane at nearest-neighbor (rounded) voxel indices. Any sampled point $p(x,y,z)$ falling outside the boundaries of $M$ or outside the plane shape is assigned a default value of $v = 0$.

---

## 2. Project Scope & Engineering Goals

While 3D-to-2D plane projection presents an algorithmic challenge, the primary focus of this project is **Software Engineering, Object-Oriented Design (OOD/OOP), code stability, and runtime efficiency**.

### Core Objectives
1. **Modular Architecture (OOD):** Decouple the system into independent, testable components (`VolumeData`, `Plane`, `PlaneParser`, `ProjectionEngine`, `VideoExporter`, and `AppController`) adhering to SOLID principles.
2. **Algorithmic Vectorization & High Performance:** Standard nested loops in Python are too slow for volumetric rendering. To meet and exceed the strict runtime requirements—a minimum of **30+ FPS** and a target of **100+ FPS** on a $500^3$ byte matrix—the projection algorithm is vectorized using `NumPy` spatial grid broadcasting.
3. **End-to-End Pipeline:** Seamlessly read `.nrrd` volumetric datasets and `.csv` trajectory files to generate smooth `.mp4` visual slices.
4. **Comprehensive Testing Strategy:** Ensure mathematical accuracy, boundary safety (out-of-bounds handling), and frame-rate benchmarks through automated unit and integration tests.

---

## 3. System Requirements & Tech Stack
* **Language:** Python 3.10+
* **Core Libraries:**
  * `numpy` – High-speed vectorized matrix and spatial calculations.
  * `pynrrd` – Parsing 3D NRRD volumetric data files.
  * `opencv-python` – Compiling 2D projection matrices into `.mp4` video streams.
  * `pytest` – Automated testing suite.
* **Specification:** Full requirements, architecture, and algorithm details are documented in [SRS.md](SRS.md).

---

## 4. Usage (CLI Demo)

The main execution script (`Ex0.py`) runs via the command line and accepts three positional arguments:

```bash
python Ex0.py <file.nrrd> <file.csv> <file.mp4>
```

Each row in `<file.csv>` has 13 columns (`Number of Point, x1,y1,z1, ..., x4,y4,z4`), where column 1 is `3` (triangle) or `4` (trapezoid).
