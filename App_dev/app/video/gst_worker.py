# App_dev/app/video/gst_worker.py
import numpy as np
from PySide6.QtCore import QObject, Signal, Slot
import gi
gi.require_version("Gst", "1.0")
gi.require_version("GObject", "2.0")
from gi.repository import Gst, GLib

class GstCaptureWorker(QObject):
    frameReady = Signal(object)   # numpy BGR frame
    error = Signal(str)
    finished = Signal()

    def __init__(self, width: int, height: int, fps: int,
                 prefer_libcamera: bool = True, device_index: int = 0):
        super().__init__()
        self.width = width
        self.height = height
        self.fps = fps
        self.prefer_libcamera = prefer_libcamera
        self.device_index = device_index
        self._loop: GLib.MainLoop | None = None
        self._pipeline = None
        self._appsink = None

    @Slot()
    def run(self):
        try:
            Gst.init(None)
            desc = self._build_pipeline_desc()
            self._pipeline = Gst.parse_launch(desc)

            self._appsink = self._pipeline.get_by_name("appsink0")
            if self._appsink is None:
                self.error.emit("appsink not found in pipeline.")
                self.finished.emit()
                return

            self._appsink.connect("new-sample", self._on_new_sample)

            bus = self._pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self._on_bus_message)

            self._pipeline.set_state(Gst.State.PLAYING)
            self._loop = GLib.MainLoop()
            self._loop.run()
        except Exception as e:
            self.error.emit(f"GStreamer init error: {e}")
        finally:
            if self._pipeline:
                self._pipeline.set_state(Gst.State.NULL)
            self.finished.emit()

    def stop(self):
        if self._loop and self._loop.is_running():
            try:
                self._loop.quit()
            except Exception:
                pass

    # ---- internals ----

    def _build_pipeline_desc(self) -> str:
        """
        Preview to appsink as BGR:
          (libcamerasrc|v4l2src) ! video/x-raw,width=...,height=...,framerate=... !
          videoconvert ! video/x-raw,format=BGR ! appsink
        """
        caps = f"video/x-raw,width={self.width},height={self.height},framerate={self.fps}/1"

        # Prefer libcamera (Bookworm), fallback to v4l2src
        candidates = [
            f"libcamerasrc ! {caps}",
            f"v4l2src device=/dev/video{self.device_index} ! {caps}",
        ] if self.prefer_libcamera else [
            f"v4l2src device=/dev/video{self.device_index} ! {caps}",
            f"libcamerasrc ! {caps}",
        ]

        # Return first that parses; otherwise fallback without caps negotiation
        for src in candidates:
            try:
                Gst.parse_launch(f"{src} ! fakesink")
                return f"{src} ! videoconvert ! video/x-raw,format=BGR ! appsink name=appsink0 emit-signals=true max-buffers=1 drop=true"
            except Exception:
                continue

        return "v4l2src ! videoconvert ! video/x-raw,format=BGR ! appsink name=appsink0 emit-signals=true max-buffers=1 drop=true"

    def _on_bus_message(self, bus, msg):
        mtype = msg.type
        if mtype == Gst.MessageType.ERROR:
            err, debug = msg.parse_error()
            self.error.emit(str(err))
            self.stop()
        elif mtype == Gst.MessageType.EOS:
            self.stop()

    def _on_new_sample(self, sink):
        try:
            sample = sink.emit("pull-sample")
            buf = sample.get_buffer()
            caps = sample.get_caps().get_structure(0)
            w = caps.get_value("width")
            h = caps.get_value("height")
            success, mapinfo = buf.map(Gst.MapFlags.READ)
            if not success:
                return Gst.FlowReturn.ERROR
            try:
                arr = np.frombuffer(mapinfo.data, dtype=np.uint8).reshape((h, w, 3))
                self.frameReady.emit(arr.copy())
            finally:
                buf.unmap(mapinfo)
            return Gst.FlowReturn.OK
        except Exception as e:
            self.error.emit(f"appsink error: {e}")
            return Gst.FlowReturn.ERROR
