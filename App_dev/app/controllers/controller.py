from __future__ import annotations

import os
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from loguru import logger
from PySide6.QtCore import Slot, QTimer
from PySide6.QtWidgets import QFileDialog

from app.ui.main_window import MainWindow
from app.config.settings import AppSettings
from app.utils.image import numpy_bgr_to_qimage
from app.utils.fs import ensure_dir

# Always available on Windows dev
from app.video.opencv_backend import OpenCVBackend

# GStreamer backend may not import on Windows (no gi). Handle gracefully.
try:
    from app.video.gstreamer_backend import GStreamerBackend  # Step 6 implementation
except Exception as _imp_err:
    GStreamerBackend = None  # type: ignore
    logger.debug("GStreamer backend not available here: {}", _imp_err)


class AppController:
    """
    Chooses the video backend at runtime:
      - VIDEO_BACKEND=opencv      -> OpenCVBackend (Windows dev)
      - VIDEO_BACKEND=gstreamer   -> GStreamerBackend (Pi 5 prod), if available
    On Step 6 (Pi): GStreamer preview opens in a separate GST window, so no frames
    arrive to the UI; FPS display is disabled in that mode.
    """

    def __init__(self, window: MainWindow):
        self.window = window
        self.is_previewing = False
        self.is_recording = False

        self.settings = AppSettings()

        self.backend = None  # type: ignore
        self._using_gst = False  # tracks if current session uses the GStreamer backend

        # Live FPS calc (OpenCV path only)
        self._frame_times = deque(maxlen=120)
        self._fps_timer = QTimer()
        self._fps_timer.setInterval(1000)  # 1s
        self._fps_timer.timeout.connect(self._update_fps)

        # Connect UI signals
        self.window.startPreview.connect(self.on_start_preview)
        self.window.toggleRecord.connect(self.on_toggle_recording)
        self.window.stopAll.connect(self.on_stop_all)
        self.window.chooseOutputFolder.connect(self.on_choose_output_folder)

        # Initial UI info
        self.window.set_output_dir(str(Path(self.settings.output_dir)))
        self.window.set_status_text("Ready.")

    # === Button handlers ===
    def on_start_preview(self):
        if self.is_previewing:
            self.window.set_status_text("Preview already running.")
            return

        # Decide backend
        want_gst = self.settings.video_backend.lower() == "gstreamer"
        can_gst = GStreamerBackend is not None

        if want_gst and can_gst:
            # On Pi, typical camera is /dev/video0; map CAMERA_INDEX -> device path
            device = f"/dev/video{self.settings.camera_index}"
            try:
                self.backend = GStreamerBackend(device=device)
                self._using_gst = True
                backend_name = f"GStreamer ({device})"
            except Exception as e:
                logger.exception("Failed to init GStreamer backend, falling back to OpenCV: {}", e)
                self.backend = OpenCVBackend(device_index=self.settings.camera_index)
                self._using_gst = False
                backend_name = "OpenCV (fallback)"
        else:
            # Windows dev path or when gst not available
            self.backend = OpenCVBackend(device_index=self.settings.camera_index)
            self._using_gst = False
            backend_name = "OpenCV"

        w, h = self.settings.width_height
        fps = self.settings.fps

        try:
            # Start preview
            self.backend.start_preview((w, h), fps)
            # Both backends expose on_error; on_frame is meaningful only for OpenCV path
            self.backend.on_error(self._on_error)
            if not self._using_gst:
                # OpenCV path emits frames to UI
                self.backend.on_frame(self._on_frame)
        except Exception as e:
            logger.exception(e)
            self.window.set_status_text(f"Failed to start preview: {e}")
            return

        # FPS timer only when frames flow into the UI (OpenCV path)
        self._frame_times.clear()
        if not self._using_gst:
            self._fps_timer.start()
            self.window.set_fps(None)
        else:
            # No frames into the label in Step 6; set hint
            self.window.set_fps(None)

        self.is_previewing = True
        self.window.set_preview_active(True)
        if self._using_gst:
            self.window.set_status_text(
                f"Preview {w}x{h}@{fps} started ({backend_name}). A GStreamer window should be visible."
            )
        else:
            self.window.set_status_text(f"Preview {w}x{h}@{fps} started ({backend_name}).")

    def on_toggle_recording(self):
        if not self.is_previewing:
            self.window.set_status_text("Start Preview first.")
            return

        if not self.is_recording:
            out_dir = Path(self.settings.output_dir)
            ensure_dir(out_dir)
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            out_path = out_dir / f"capture-{ts}.mp4"

            try:
                self.backend.start_recording(str(out_path))
            except NotImplementedError as e:
                # Step 6 GStreamer backend doesn't implement recording yet
                self.window.set_status_text("Recording on Pi (GStreamer) not enabled yet. (Step 7b adds tee + H.264)")
                logger.info("Recording not implemented on this backend yet: {}", e)
                return
            except Exception as e:
                self.window.set_status_text(f"Failed to start recording: {e}")
                return

            self.is_recording = True
            self.window.set_recording_state(True)
            self.window.set_status_text(f"Recording → {out_path}")
        else:
            try:
                self.backend.stop_recording()
            except Exception as e:
                self.window.set_status_text(f"Failed to stop recording: {e}")
                return

            self.is_recording = False
            self.window.set_recording_state(False)
            self.window.set_status_text("Recording stopped.")

    def on_stop_all(self):
        if self.backend:
            self.backend.stop_all()
        had_anything = self.is_previewing or self.is_recording
        self.is_previewing = False
        self.is_recording = False
        self.window.set_preview_active(False)
        self.window.set_recording_state(False)
        self._fps_timer.stop()
        self.window.set_fps(None)
        self.window.set_status_text("Stopped." if had_anything else "Nothing to stop.")

    def on_choose_output_folder(self):
        start_dir = str(Path(self.settings.output_dir).resolve())
        chosen = QFileDialog.getExistingDirectory(self.window, "Choose Output Folder", start_dir)
        if chosen:
            self.settings.output_dir = chosen
            self.window.set_output_dir(chosen)
            self.window.set_status_text("Output folder set.")

    # === Backend callbacks ===
    @Slot(object)
    def _on_frame(self, frame_bgr):
        # Only called on OpenCV backend
        self._frame_times.append(time.perf_counter())
        qimg = numpy_bgr_to_qimage(frame_bgr)
        self.window.show_frame(qimg)

    @Slot(str)
    def _on_error(self, message: str):
        logger.error(message)
        self.window.set_status_text(message)

    def _update_fps(self):
        # Only meaningful when frames are flowing into the UI (OpenCV path)
        if self._using_gst:
            self.window.set_fps(None)
            return
        if len(self._frame_times) < 2:
            self.window.set_fps(None)
            return
        dt = self._frame_times[-1] - self._frame_times[0]
        if dt <= 0:
            self.window.set_fps(None)
            return
        fps = (len(self._frame_times) - 1) / dt
        self.window.set_fps(fps)
