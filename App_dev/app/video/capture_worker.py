# App_dev/app/video/capture_worker.py
from PySide6.QtCore import QObject, Signal, Slot
import cv2
import time

class CaptureWorker(QObject):
    frameReady = Signal(object)   # emits a NumPy BGR frame
    error = Signal(str)
    finished = Signal()

    def __init__(self, device_index: int, width: int, height: int, fps: int):
        super().__init__()
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps
        self._running = False

    @Slot()
    def run(self):
        # Prefer DirectShow on Windows; fallback to MSMF if needed
        cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(self.device_index, cv2.CAP_MSMF)

        if not cap.isOpened():
            self.error.emit("Could not open camera device.")
            self.finished.emit()
            return

        # Try to set caps (not all cams honor these)
        if self.width > 0:  cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.width)
        if self.height > 0: cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        if self.fps > 0:    cap.set(cv2.CAP_PROP_FPS,          self.fps)

        target_delay = 1.0 / self.fps if self.fps > 0 else 0.0
        self._running = True

        while self._running:
            ok, frame = cap.read()
            if not ok or frame is None:
                self.error.emit("Failed to read frame from camera.")
                break
            self.frameReady.emit(frame)
            #if target_delay > 0:
            #    time.sleep(target_delay * 0.6)  # mild pacing without stalling

        cap.release()
        self.finished.emit()

    def stop(self):
        self._running = False
