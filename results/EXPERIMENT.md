# Experimental Evaluation & Benchmark Report

## 1. Test Environment
* **Runtime Environment:** Docker Container (`python:3.11.17-slim`, `Linux-7.0.14-linuxkit-aarch64-with-glibc2.41`)
* **NumPy Version:** `2.4.6`
* **OpenCV Version:** `5.0.0`

## 2. Dataset & Performance Results ([docs/SRS.md](../docs/SRS.md) NFR-1, [docs/STP.md](../docs/STP.md) TC-15)

Pure projection throughput is measured as the median of 3 runs (after 1 warm-up pass), excluding disk I/O and video encoding, alongside full end-to-end CLI execution time (`python Ex0.py <file.nrrd> <file.csv> <file.mp4>`):

| Volume File | Voxel Type | Dimensions ($sx, sy, sz$) | Global `vmax` | CSV Planes | NRRD Load Time | Pure Projection Speed | Total End-to-End Time |
|---|---|---|---|---|---|---|---|
| `croissant.nrrd` | `uint8` | `(500, 500, 500)` | `255` | 60 | 0.68 s | **435.3 FPS** (2.30 ms) | 0.92 s |
| `onion.nrrd` | `uint8` | `(256, 256, 130)` | `232` | 4 | 0.20 s | **871.0 FPS** (1.15 ms) | 0.20 s |
| `biscuit_cake.nrrd` | `uint16` | `(256, 256, 130)` | `3986` | 4 | 0.16 s | **876.8 FPS** (1.14 ms) | 0.16 s |
| `swiss_roll.nrrd` | `uint32` | `(256, 256, 130)` | `186330` | 4 | 0.16 s | **810.9 FPS** (1.23 ms) | 0.18 s |
| `MRHead_1.nrrd` | `uint16` | `(256, 256, 130)` | `279` | 135 | 0.16 s | **1741.5 FPS** (0.57 ms) | 0.28 s |

## 3. Output Video Verification ([`results/demo_output.mp4`](demo_output.mp4))
* **Command Executed:** `python Ex0.py data/croissant.nrrd data/croissant_sweep.csv results/demo_output.mp4`
* **Encoded Frame Count:** `60` frames (matches 60 CSV plane rows: 30 trapezoids + 30 triangles)
* **Uniform Canvas Resolution:** `514 × 500` pixels ($H_{\max} \times W_{\max}$, `FR-7`)
* **Playback Frame Rate:** `30.0 FPS` (`mp4v` codec, `FR-9`)
* **File Size:** `1,819,106` bytes
* **Classroom Sample Trajectory Verification (`data/sample_planes.csv`):** 4 frames verified in `0.78 s` on `data/croissant.nrrd` (including out-of-volume negative coordinates and the `Row 4: 4.12%` non-isosceles warning).
