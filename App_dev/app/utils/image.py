# App_dev/app/utils/image.py
import cv2
from PySide6.QtGui import QImage

def numpy_bgr_to_qimage(frame) -> QImage:
    """Convert a BGR uint8 HxWx3 frame to QImage (RGB)."""
    if frame is None:
        return QImage()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    bytes_per_line = ch * w
    # .copy() to own the memory (safe once cv2 releases the buffer)
    return QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
