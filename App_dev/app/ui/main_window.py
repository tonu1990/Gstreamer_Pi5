from PySide6.QtWidgets import (
    QMainWindow, QWidget, QPushButton, QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPalette, QColor, QFont, QPixmap

class MainWindow(QMainWindow):
    # Signals emitted on button actions (controller connects to these)
    startPreview = Signal()
    toggleRecord = Signal()
    stopAll = Signal()
    chooseOutputFolder = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Edge Video App — Preview / Record")
        self.setMinimumSize(1000, 600)

        # Central layout
        central = QWidget(self)
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # Video area
        self.videoLabel = QLabel("No signal")
        self.videoLabel.setAlignment(Qt.AlignCenter)
        self.videoLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.videoLabel.setMinimumSize(640, 360)
        font = QFont()
        font.setPointSize(14)
        self.videoLabel.setFont(font)

        pal = self.videoLabel.palette()
        pal.setColor(QPalette.Window, QColor("#111111"))
        pal.setColor(QPalette.WindowText, QColor("#dddddd"))
        self.videoLabel.setAutoFillBackground(True)
        self.videoLabel.setPalette(pal)

        # Controls column
        controls = QVBoxLayout()
        controls.setSpacing(10)

        self.btnStartPreview = QPushButton("Start Preview")
        self.btnToggleRecord = QPushButton("Start Recording")
        self.btnStop = QPushButton("Stop")
        self.btnChooseOutputDir = QPushButton("Choose Output Folder…")

        self.btnToggleRecord.setEnabled(False)  # disabled until preview starts
        self.btnStop.setEnabled(False)

        # Indicators / info
        self.recLabel = QLabel("● REC")
        self.recLabel.setStyleSheet("color: red; font-weight: bold;")
        self.recLabel.setVisible(False)

        self.fpsLabel = QLabel("FPS: —")
        self.outputDirLabel = QLabel("Output: —")
        self.outputDirLabel.setWordWrap(True)

        # Order in the side panel
        controls.addWidget(self.btnStartPreview)
        controls.addWidget(self.btnToggleRecord)
        controls.addWidget(self.btnStop)
        controls.addSpacing(8)
        controls.addWidget(self.btnChooseOutputDir)
        controls.addSpacing(16)
        controls.addWidget(self.recLabel)
        controls.addWidget(self.fpsLabel)
        controls.addWidget(self.outputDirLabel)
        controls.addStretch(1)

        root.addWidget(self.videoLabel, stretch=4)
        root.addLayout(controls, stretch=1)

        # Wire signals
        self.btnStartPreview.clicked.connect(self.startPreview.emit)
        self.btnToggleRecord.clicked.connect(self.toggleRecord.emit)
        self.btnStop.clicked.connect(self.stopAll.emit)
        self.btnChooseOutputDir.clicked.connect(self.chooseOutputFolder.emit)

    # UI state helpers the controller can call
    def set_preview_active(self, active: bool):
        self.btnStartPreview.setEnabled(not active)
        self.btnToggleRecord.setEnabled(active)
        self.btnStop.setEnabled(active)

    def set_recording_state(self, recording: bool):
        self.btnToggleRecord.setText("Stop Recording" if recording else "Start Recording")
        self.recLabel.setVisible(recording)

    def set_status_text(self, text: str):
        self.statusBar().showMessage(text, 3000)  # 3s

    def set_output_dir(self, path: str):
        self.outputDirLabel.setText(f"Output: {path}")
        self.outputDirLabel.setToolTip(path)

    def set_fps(self, fps: float | None):
        if fps is None or fps <= 0:
            self.fpsLabel.setText("FPS: —")
        else:
            self.fpsLabel.setText(f"FPS: {fps:.0f}")

    # Show a frame in the label
    def show_frame(self, qimage):
        if qimage.isNull():
            return
        pix = QPixmap.fromImage(qimage)
        pix = pix.scaled(self.videoLabel.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.videoLabel.setPixmap(pix)
