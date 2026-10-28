"""Execution orchestrator wiring VolumeData, PlaneParser, ProjectionEngine, and VideoExporter (SDD §2.6, EDD §4.1)."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Sequence

from src.exceptions import EncodingError, InputError, SlicerError
from src.plane_parser import PlaneParser
from src.projection_engine import ProjectionEngine
from src.video_exporter import VideoExporter
from src.volume_data import VolumeData


class AppController:
    """Central coordinator managing the 3-phase execution lifecycle and CLI exit codes."""

    @staticmethod
    def validate_cli_args(args: Sequence[str]) -> tuple[Path, Path, Path]:
        """Validate the 3 positional CLI arguments `<file.nrrd> <file.csv> <file.mp4>` (FR-1)."""
        if len(args) != 3:
            raise InputError(
                f"Expected exactly 3 arguments (<file.nrrd> <file.csv> <file.mp4>), got {len(args)}."
            )

        nrrd_path = Path(args[0])
        csv_path = Path(args[1])
        mp4_path = Path(args[2])

        if nrrd_path.suffix.lower() != ".nrrd":
            raise InputError(f"First argument must have a '.nrrd' extension, got '{nrrd_path}'.")
        if csv_path.suffix.lower() != ".csv":
            raise InputError(f"Second argument must have a '.csv' extension, got '{csv_path}'.")
        if mp4_path.suffix.lower() != ".mp4":
            raise InputError(f"Third argument must have a '.mp4' extension, got '{mp4_path}'.")

        if not nrrd_path.is_file():
            raise InputError(f"Input NRRD file does not exist: '{nrrd_path}'.")
        if not csv_path.is_file():
            raise InputError(f"Input CSV file does not exist: '{csv_path}'.")

        parent_dir = mp4_path.parent if str(mp4_path.parent) != "" else Path(".")
        if not parent_dir.is_dir():
            raise InputError(f"Output directory does not exist: '{parent_dir}'.")
        if not os.access(parent_dir, os.W_OK):
            raise InputError(f"Output directory is not writable: '{parent_dir}'.")
        if mp4_path.exists():
            if mp4_path.is_dir():
                raise InputError(f"Output path points to a directory, not a file: '{mp4_path}'.")
            if not os.access(mp4_path, os.W_OK):
                raise InputError(f"Existing output MP4 file is not writable: '{mp4_path}'.")

        return nrrd_path, csv_path, mp4_path

    def run(self, args: Sequence[str]) -> int:
        """Execute the end-to-end projection pipeline and return the CLI exit code (0, 1, 2, or 3)."""
        try:
            # Phase 1: Initialization, Ingestion & Up-Front Validation (EDD §4.1)
            nrrd_path, csv_path, mp4_path = self.validate_cli_args(args)
            volume = VolumeData(nrrd_path)
            parser = PlaneParser()
            planes, warnings = parser.parse(csv_path)

            for warning in warnings:
                print(warning, file=sys.stderr)

            canvas_height = max(plane.height for plane in planes)
            canvas_width = max(plane.width for plane in planes)

            # Phase 2 & 3: Transformation Loop & Finalization (EDD §4.1)
            engine = ProjectionEngine()
            with VideoExporter(
                output_path=mp4_path,
                canvas_height=canvas_height,
                canvas_width=canvas_width,
                vmax=volume.vmax,
            ) as exporter:
                for plane in planes:
                    frame = engine.project(volume.matrix, plane)
                    exporter.write_frame(frame)
                    del frame

                if exporter.frames_written != len(planes):
                    raise EncodingError(
                        f"Expected {len(planes)} encoded frames, wrote {exporter.frames_written}."
                    )

            if not mp4_path.is_file() or mp4_path.stat().st_size == 0:
                raise EncodingError(f"Encoded video file '{mp4_path}' is missing or empty.")

            return 0

        except SlicerError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return exc.exit_code
        except Exception as exc:
            print(f"Unexpected error: {exc}", file=sys.stderr)
            return 1
