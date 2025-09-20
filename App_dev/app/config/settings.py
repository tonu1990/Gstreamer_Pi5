import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class AppSettings:
    video_backend: str = os.getenv("VIDEO_BACKEND", "opencv")
    model_path: str = os.getenv("MODEL_PATH", "./models/current.onnx")
    output_dir: str = os.getenv("OUTPUT_DIR", "./output")
    resolution: str = os.getenv("RESOLUTION", "1280x720")
    fps: int = int(os.getenv("FPS", "30"))
    camera_index: int = int(os.getenv("CAMERA_INDEX", "0"))

    @property
    def width_height(self):
        try:
            w, h = self.resolution.lower().split("x")
            return int(w), int(h)
        except Exception:
            return 1280, 720
