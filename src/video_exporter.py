"""Presentation layer for normalizing, padding, and encoding 2D slices into an MP4 video (SRS §3.5, FR-7..FR-9)."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
import cv2
import numpy as np

from src.exceptions import EncodingError

DEFAULT_FPS: float = 30.0
DEFAULT_CODEC: str = "mp4v"


class VideoExporter:
    """Normalizes 2D frames to uint8, centers them on a uniform black canvas, and writes an MP4 stream."""

    def __init__(
        self,
        output_path: str | Path,
        canvas_height: int,
        canvas_width: int,
        vmax: int,
        fps: float = DEFAULT_FPS,
        codec: str = DEFAULT_CODEC,
    ) -> None:
        if canvas_height < 1 or canvas_width < 1:
            raise EncodingError(
                f"Invalid video canvas dimensions ({canvas_height}, {canvas_width}); must be >= 1x1."
            )
        self._output_path = Path(output_path)
        self._canvas_height = int(canvas_height)
        self._canvas_width = int(canvas_width)
        self._vmax = int(vmax)
        self._fps = float(fps)
        self._codec = codec
        self._writer: cv2.VideoWriter | None = None
        self._frames_written: int = 0

    @property
    def canvas_shape(self) -> tuple[int, int]:
        """Canvas dimensions (H_max, W_max)."""
        return self._canvas_height, self._canvas_width

    @property
    def frames_written(self) -> int:
        """Number of frames written to the stream so far."""
        return self._frames_written

    @staticmethod
    def normalize_frame(frame: np.ndarray, vmax: int) -> np.ndarray:
        """Scale a 2D frame to uint8 [0, 255] using the global volume maximum vmax (FR-8).

        - uint8 frames are returned as uint8 without rescaling.
        - uint16/uint32 frames use v_8 = round(v * 255 / vmax), or all-zeros if vmax <= 0.
        """
        if frame.dtype == np.uint8:
            return np.ascontiguousarray(frame, dtype=np.uint8)

        if vmax <= 0:
            return np.zeros(frame.shape, dtype=np.uint8)

        scaled = np.rint(frame.astype(np.float64) * (255.0 / float(vmax)))
        return np.clip(scaled, 0, 255).astype(np.uint8)

    @staticmethod
    def pad_frame(frame: np.ndarray, canvas_height: int, canvas_width: int) -> np.ndarray:
        """Center a 2D uint8 frame of shape (N, W) on a black (0) canvas of shape (H_max, W_max) (FR-7)."""
        n_rows, n_cols = frame.shape
        if n_rows > canvas_height or n_cols > canvas_width:
            raise EncodingError(
                f"Frame shape ({n_rows}, {n_cols}) exceeds canvas shape ({canvas_height}, {canvas_width})."
            )
        if n_rows == canvas_height and n_cols == canvas_width:
            return np.ascontiguousarray(frame, dtype=np.uint8)

        canvas = np.zeros((canvas_height, canvas_width), dtype=np.uint8)
        row_offset = (canvas_height - n_rows) // 2
        col_offset = (canvas_width - n_cols) // 2
        canvas[row_offset : row_offset + n_rows, col_offset : col_offset + n_cols] = frame
        return canvas

    def open(self) -> None:
        """Initialize the OpenCV VideoWriter stream."""
        fourcc = cv2.VideoWriter_fourcc(*self._codec)
        # OpenCV VideoWriter expects frameSize as (width, height)
        frame_size = (self._canvas_width, self._canvas_height)
        try:
            writer = cv2.VideoWriter(
                str(self._output_path),
                fourcc,
                self._fps,
                frame_size,
                isColor=True,
            )
        except Exception as exc:
            raise EncodingError(f"Failed to initialize video writer for '{self._output_path}': {exc}") from exc

        if not writer.isOpened():
            writer.release()
            raise EncodingError(
                f"Unable to open MP4 video stream at '{self._output_path}' with codec '{self._codec}'."
            )
        self._writer = writer

    def write_frame(self, frame: np.ndarray) -> np.ndarray:
        """Normalize, center-pad, and encode a single 2D frame into the MP4 stream (FR-7..FR-9).

        Returns:
            The 2D uint8 padded canvas frame of shape (H_max, W_max) that was written.
        """
        if self._writer is None or not self._writer.isOpened():
            raise EncodingError("Cannot write frame: VideoExporter stream is not open.")

        normalized = self.normalize_frame(frame, self._vmax)
        padded = self.pad_frame(normalized, self._canvas_height, self._canvas_width)

        # Convert single-channel grayscale uint8 (H, W) into 3-channel grayscale BGR for universal mp4v support
        bgr_frame = cv2.cvtColor(padded, cv2.COLOR_GRAY2BGR)
        try:
            self._writer.write(bgr_frame)
        except Exception as exc:
            raise EncodingError(f"Failed to write video frame: {exc}") from exc

        self._frames_written += 1
        return padded

    def close(self) -> None:
        """Flush and release the underlying video writer handle."""
        if self._writer is not None:
            try:
                self._writer.release()
            finally:
                self._writer = None

    def __enter__(self) -> VideoExporter:
        self.open()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
        if exc_type is not None and self._output_path.exists():
            try:
                self._output_path.unlink()
            except OSError:
                pass
