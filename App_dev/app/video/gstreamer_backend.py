from typing import Tuple, Optional, Callable
from loguru import logger
import threading

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst, GLib

from app.video.base import VideoBackend

class GStreamerBackend(VideoBackend):
    """
    Raspberry Pi backend using gst-python.
    Step 6: preview; Step 7b: recording via tee + v4l2h264enc + mp4mux.
    Opens preview in a separate GStreamer window (autovideosink).
    """

    def __init__(self, device: str = "/dev/video0"):
        self._device = device
        self._w = 1280
        self._h = 720
        self._fps = 30

        self._pipeline: Optional[Gst.Element] = None
        self._bus_thread: Optional[threading.Thread] = None
        self._stop_bus = threading.Event()
        self._eos_event = threading.Event()

        self._err_cb: Optional[Callable[[str], None]] = None

        self._active = False
        self._recording = False
        self._output_path: Optional[str] = None

        Gst.init(None)

    # Subscriptions
    def on_error(self, slot_callable: Callable[[str], None]):
        self._err_cb = slot_callable

    def on_frame(self, slot_callable):
        # Not used: we render via autovideosink
        pass

    # --- Public API ---
    def start_preview(self, resolution: Tuple[int, int], fps: int) -> None:
        self._w, self._h = resolution
        self._fps = max(1, fps or 30)
        self._start_pipeline(preview_only=True)

    def start_recording(self, output_path: str) -> None:
        if not self._active:
            # ensure preview caps are known
            self._w = self._w or 1280
            self._h = self._h or 720
            self._fps = self._fps or 30
        self._output_path = output_path
        self._start_pipeline(preview_only=False)
        self._recording = True
        logger.info("Recording to {}", self._output_path)

    def stop_recording(self) -> None:
        if not self._recording:
            return
        logger.info("Stopping recording (EOS + revert to preview-only)")
        self._send_eos_and_wait(timeout_sec=4.0)
        # After EOS, rebuild preview-only
        self._start_pipeline(preview_only=True)
        self._recording = False
        self._output_path = None

    def stop_all(self) -> None:
        self._stop_bus.set()
        if self._bus_thread:
            self._bus_thread.join(timeout=1.0)
            self._bus_thread = None
        if self._pipeline:
            self._pipeline.set_state(Gst.State.NULL)
            self._pipeline = None
        self._active = False
        self._recording = False
        self._output_path = None
        self._eos_event.clear()

    # --- Internals ---
    def _start_pipeline(self, preview_only: bool) -> None:
        # Tear down any existing pipeline first
        self._stop_bus.set()
        if self._bus_thread:
            self._bus_thread.join(timeout=1.0)
            self._bus_thread = None
        if self._pipeline:
            self._pipeline.set_state(Gst.State.NULL)
            self._pipeline = None
        self._eos_event.clear()
        self._stop_bus.clear()

        pipe_str = self._build_preview_pipeline() if preview_only else self._build_record_pipeline()
        logger.info("[GStreamerBackend] Pipeline: {}", pipe_str)

        try:
            pipeline = Gst.parse_launch(pipe_str)
        except GLib.Error as e:
            msg = f"Failed to parse pipeline: {e.message}"
            logger.error(msg)
            if self._err_cb: self._err_cb(msg)
            return

        self._pipeline = pipeline
        ret = self._pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            msg = "Failed to set pipeline PLAYING."
            logger.error(msg)
            if self._err_cb: self._err_cb(msg)
            self._pipeline.set_state(Gst.State.NULL)
            self._pipeline = None
            self._active = False
            return

        # Start bus watcher
        self._bus_thread = threading.Thread(target=self._bus_watch, daemon=True)
        self._bus_thread.start()
        self._active = True

    def _build_preview_pipeline(self) -> str:
        return (
            f"v4l2src device={self._device} ! "
            f"video/x-raw,width={self._w},height={self._h},framerate={self._fps}/1 ! "
            f"videoconvert ! autovideosink sync=false"
        )

    def _build_record_pipeline(self) -> str:
        out = self._output_path or "/data/output/capture.mp4"
        # Note: give elements names so future enhancements can find them if needed
        return (
            f"v4l2src device={self._device} ! "
            f"video/x-raw,width={self._w},height={self._h},framerate={self._fps}/1 ! "
            f"videoconvert ! tee name=t "
            f"t. ! queue ! autovideosink sync=false "
            f"t. ! queue ! v4l2h264enc ! h264parse ! mp4mux faststart=true name=mux ! "
            f"filesink location=\"{out}\" name=fsink"
        )

    def _send_eos_and_wait(self, timeout_sec: float = 4.0):
        if not self._pipeline:
            return
        bus = self._pipeline.get_bus()
        self._eos_event.clear()
        # Send EOS to the whole pipeline (both branches). This will end preview briefly.
        ok = self._pipeline.send_event(Gst.Event.new_eos())
        if not ok:
            logger.warning("Failed to send EOS; forcing NULL state.")
            self._pipeline.set_state(Gst.State.NULL)
            return

        # Wait for EOS message processed by bus thread
        if not self._eos_event.wait(timeout=timeout_sec):
            logger.warning("Timed out waiting for EOS; forcing NULL state.")
        # Ensure pipeline is stopped
        self._pipeline.set_state(Gst.State.NULL)
        self._pipeline = None

    def _bus_watch(self):
        if not self._pipeline:
            return
        bus = self._pipeline.get_bus()
        while not self._stop_bus.is_set():
            msg = bus.timed_pop_filtered(
                200 * Gst.MILLISECOND,
                Gst.MessageType.ERROR | Gst.MessageType.EOS | Gst.MessageType.WARNING | Gst.MessageType.STATE_CHANGED
            )
            if msg is None:
                continue
            mtype = msg.type
            if mtype == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                text = f"GStreamer ERROR: {err.message} (debug: {debug})"
                logger.error(text)
                if self._err_cb: self._err_cb(text)
                self.stop_all()
                break
            elif mtype == Gst.MessageType.WARNING:
                err, debug = msg.parse_warning()
                logger.warning("GStreamer WARN: {} (debug: {})", err.message, debug)
            elif mtype == Gst.MessageType.EOS:
                logger.info("GStreamer EOS received.")
                self._eos_event.set()
                break
            elif mtype == Gst.MessageType.STATE_CHANGED:
                # Could log state transitions for debugging
                pass
