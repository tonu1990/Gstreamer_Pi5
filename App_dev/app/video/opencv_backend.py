from typing import Tuple, Callable, Optional
from pathlib import Path
import os
import cv2
from PySide6.QtCore import QThread
from loguru import logger

from app.video.base import VideoBackend
from app.video.capture_worker import CaptureWorker

from collections import deque
import time

class OpenCVBackend(VideoBackend):
    """
    Windows development backend using OpenCV.
    Step 3: preview
    Step 4: recording (MP4 if available; fallback otherwise)
    """
    def __init__(self, device_index: int = 0):
        self._active = False
        self._recording = False
        self._device_index = device_index

        self._thread: Optional[QThread] = None
        self._worker: Optional[CaptureWorker] = None

        self._writer: Optional[cv2.VideoWriter] = None
        self._record_path: Optional[str] = None
        self._fps: int = 30
        self._ts = deque(maxlen=120)

    def start_preview(self, resolution: Tuple[int, int], fps: int) -> None:
        if self._active:
            logger.info("[OpenCVBackend] Preview already active.")
            return

        w, h = resolution
        self._fps = fps if fps > 0 else 30
        logger.info("[OpenCVBackend] start_preview res=%sx%s fps=%s device=%s", w, h, self._fps, self._device_index)

        self._thread = QThread()
        self._worker = CaptureWorker(self._device_index, w, h, self._fps)
        self._worker.moveToThread(self._thread)

        # Internal hook to write frames when recording
        self._worker.frameReady.connect(self._on_frame_internal)

        # Lifecycle
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()
        self._active = True

    def on_frame(self, slot_callable: Callable[[object], None]):
        if self._worker:
            self._worker.frameReady.connect(slot_callable)

    def on_error(self, slot_callable: Callable[[str], None]):
        if self._worker:
            self._worker.error.connect(slot_callable)

    # --- Recording controls ---

    def start_recording(self, output_path: str) -> None:
        if not self._active:
            raise RuntimeError("Preview not active")
        if self._recording:
            logger.info("[OpenCVBackend] Already recording.")
            return

        self._record_path = output_path
        self._writer = None  # lazy-open on first frame (knows true WxH)
        self._recording = True
        logger.info("[OpenCVBackend] Recording → %s", self._record_path)

    def stop_recording(self) -> None:
        if not self._recording:
            return
        self._recording = False
        if self._writer:
            try:
                self._writer.release()
            except Exception:
                pass
        self._writer = None
        logger.info("[OpenCVBackend] Recording stopped.")

    def stop_all(self) -> None:
        self.stop_recording()
        if self._worker:
            self._worker.stop()
        if self._thread:
            self._thread.quit()
            self._thread.wait(1500)
        self._worker = None
        self._thread = None
        self._active = False

    # --- Internal helpers ---

    def _on_frame_internal(self, frame_bgr):
        # 1) record arrival time
        self._ts.append(time.perf_counter())

        # 2) lazy-open writer using measured fps
        if self._recording and self._writer is None:
            fps_guess = self._estimate_fps()
            self._open_writer_for_frame(frame_bgr, fps_hint=fps_guess)

        # 3) write when recording
        if self._recording and self._writer is not None:
            try:
                self._writer.write(frame_bgr)
            except Exception as e:
                logger.error("VideoWriter.write failed: {}", e)

    def _estimate_fps(self) -> int:
        """Compute an integer FPS from recent frame timestamps; fallback to requested FPS."""
        if len(self._ts) >= 15:
            dt = self._ts[-1] - self._ts[0]
            if dt > 0:
                fps = (len(self._ts) - 1) / dt
                # snap to common rates to avoid weird headers
                for target in (30, 25, 24, 20, 15, 12, 10):
                    if abs(fps - target) < 2.0:
                        return target
                return max(1, int(round(fps)))
        return max(1, self._fps)


    def _open_writer_for_frame(self, frame_bgr, fps_hint=None):
        if not self._record_path:
            logger.error("No record path set.")
            return
        h, w = frame_bgr.shape[:2]
        fps = fps_hint or self._fps or 30

        ext = os.path.splitext(self._record_path)[1].lower()
        # Prefer mp4v on Windows to avoid OpenH264 noise; avc1 second
        if ext == ".mp4":
            candidates = ["mp4v", "avc1"]
        else:
            candidates = ["XVID", "MJPG"]

        for cc in candidates:
            fourcc = cv2.VideoWriter_fourcc(*cc)
            wr = cv2.VideoWriter(self._record_path, fourcc, fps, (w, h))
            if wr.isOpened():
                self._writer = wr
                logger.info("Opened VideoWriter {} @ {}x{} {}fps", cc, w, h, fps)
                return

        logger.error("Failed to open VideoWriter for {} (tried {}).", self._record_path, candidates)
        self._writer = None
