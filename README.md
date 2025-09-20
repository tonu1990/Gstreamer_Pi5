# SampleProject_Gstreamer — Starter (Step 1 & 2)

This is a **modular Python starter** for your GStreamer-based video app, designed to run on Windows during development and later extend to Raspberry Pi 5 with a GStreamer backend.

**What’s included (Step 1 & Step 2 only):**
- A PySide6 window with three buttons: **Start Preview**, **Start/Stop Recording**, **Stop**.
- No camera yet — button clicks log messages and update UI state.
- A clean module layout prepared for:
  - `OpenCVBackend` (Windows dev)
  - `GStreamerBackend` (Pi 5 prod)
  - Future YOLO/ONNX Runtime inference

## Quickstart

1) Create & activate a virtual environment (Windows PowerShell):
```powershell
cd <project-root>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

2) Run the app (UI only for now):
```powershell
python run_app.py
```

3) Where things live
```
App_dev/
  app/
    ui/               # UI widgets and windows
    controllers/      # Button logic & state machine
    video/            # Backends (stubs for now)
    config/           # Settings and environment
    utils/            # Helpers
```

## Config

Copy `.env.example` to `.env` (optional). Defaults are fine for now.

Later we’ll add:
- `VIDEO_BACKEND=opencv` (Windows) or `gstreamer` (Pi)
- `MODEL_PATH` for the YOLO model
- Resolution/FPS/output path

## Next steps

- Step 3: Implement **OpenCVBackend** for preview on Windows.
- Step 4: Add recording to MP4 (OpenCV on Windows).
- Step 5+: Switch backend to GStreamer on Pi, then add YOLO inference.
