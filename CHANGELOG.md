# Changelog

All notable changes to this project are documented in this file.

## [2026-11-07] — Documentation Simplification & Cleanup

### Changed
* **[docs/SDD.md](docs/SDD.md):**
  * Added a plain-English **"Big Picture"** summary and end-to-end pipeline overview in `§1`.
  * Rewrote component descriptions (`§2.1`–`§2.6`: `VolumeData`, `Plane` hierarchy, `PlaneParser`, `ProjectionEngine`, `VideoExporter`, and `AppController`) using a consistent **What it does / Inputs → Outputs / Why it's separate** format.
  * Simplified the four inter-module data contracts in `§3` and the architectural decision records (`ADR-01`–`ADR-04`) in `§5` into clear, approachable language while keeping all UML diagrams and traceability links intact.
* **[docs/EDD.md](docs/EDD.md):**
  * Added explicit **Function-by-Function (`In` / `Does` / `Out`) breakdowns** across `§1.1`–`§1.4` covering every class, method, and helper in `Ex0.py` and `src/`.
  * Added a plain-English overview of `ProjectionEngine.project()` at the top of `§2`, simplified the Page 2 pseudocode-ambiguity resolution table (`§2.1`), and annotated all 5 vectorized `NumPy` steps (`§2.4`).
  * Streamlined prose across data layouts (`§3`), execution flows (`§4`), edge-case handling (`§5`), performance budget (`§6`), trade-offs (`§7`), and rollout/benchmarking (`§8`).
* **[docs/SRS.md](docs/SRS.md):**
  * Rewrote the introduction (`§1.1`–`§1.2`), definitions table (`§1.3`), and design constraints (`§2.4`) in clear, intuitive English.
  * Refactored `FR-1`–`FR-9`, `NFR-1`–`NFR-5` (`§3`), and use cases `UC-01`–`UC-04` (`§4.2`) into concise, scannable bullet points while preserving every requirement ID, tolerance threshold, exit code, diagram, and traceability entry.
* **[docs/STP.md](docs/STP.md) & [`tests/`](tests/):**
  * Added a plain-English **Big Picture** summary of the 3-layer testing strategy (`§1`), explained the shared test tricks and `tests/conftest.py` fixtures (`§1.3`–`§1.4`), and simplified the risk register (`R-01`–`R-05` in `§1.6`).
  * Added simple **Sent to / Input / Expected Output** explanations to all 31 test functions across both [`docs/STP.md`](docs/STP.md) (`§2.1`) and every test file docstring in [`tests/`](tests/) (`test_volume_data.py`, `test_plane_geometry.py`, `test_plane_parser.py`, `test_projection_engine.py`, `test_video_exporter.py`, `test_cli_demo.py`, and `test_benchmark_fps.py`).
* **[README.md](README.md):**
  * Verified all SRS links point to [`docs/SRS.md`](docs/SRS.md) and added `CHANGELOG.md` to the repository structure tree.

### Removed
* **`SRS.md` (project root):** Removed the outdated single-file draft `SRS.md` from the root directory in favor of the canonical specification at [`docs/SRS.md`](docs/SRS.md).

