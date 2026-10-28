#!/usr/bin/env python3
"""CLI entry point for the 3D Volumetric Plane Projection system (SRS §1.2, FR-1; SDD §2.6).

Usage:
    python Ex0.py <file.nrrd> <file.csv> <file.mp4>
"""

from __future__ import annotations

import sys

from src.app_controller import AppController


def main(argv: list[str] | None = None) -> int:
    """Run the application with the provided command-line arguments and return its exit code."""
    args = sys.argv[1:] if argv is None else argv
    controller = AppController()
    return controller.run(args)


if __name__ == "__main__":
    sys.exit(main())
