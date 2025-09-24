#!/usr/bin/env python3
import sys
import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')

from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import Qt  # ← Important import!
from gi.repository import Gst, GstVideo, GLib

# Initialize GStreamer
Gst.init(sys.argv)

class VideoWidget(QWidget):
    """Custom widget to display GStreamer video"""
    def __init__(self):
        super().__init__()
        self.setFixedSize(320,240)
        self.setStyleSheet("background-color: black;")  # Black background for video area

class CameraApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Edge AI Camera System - PySide6")
        self.setFixedSize(350, 320)  # Very compact! 
        
        # GStreamer pipeline
        self.pipeline = None
        self.is_playing = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create video display area
        self.video_widget = VideoWidget()
        layout.addWidget(self.video_widget)
        
        # Create buttons
        self.preview_button = QPushButton("Start Preview")
        self.record_button = QPushButton("Start Recording")
        self.record_button.setEnabled(False)
        
        layout.addWidget(self.preview_button)
        layout.addWidget(self.record_button)
        
        # Connect signals
        self.preview_button.clicked.connect(self.toggle_preview)
        self.record_button.clicked.connect(self.toggle_recording)
 
        
    def toggle_preview(self):
        """Start or stop the camera preview"""
        if not self.is_playing:
            self.start_preview()
        else:
            self.stop_preview()
    
    def start_preview(self):
        """Start the camera preview"""
        print("Starting camera preview...")
        
        # Create pipeline
        self.pipeline = Gst.Pipeline.new("camera-pipeline")
        
        # Create elements
        source = Gst.ElementFactory.make("v4l2src", "source")
        caps_filter = Gst.ElementFactory.make("capsfilter", "capsfilter")
        convert = Gst.ElementFactory.make("videoconvert", "convert")
        sink = Gst.ElementFactory.make("autovideosink", "sink")
        
        if not all([source, caps_filter, convert, sink]):
            print("ERROR: Could not create GStreamer elements")
            return
        
        # Configure elements
        source.set_property("device", "/dev/video0")
        caps = Gst.Caps.from_string("video/x-raw,width=640,height=480")
        caps_filter.set_property("caps", caps)
        
        # Add to pipeline
        for element in [source, caps_filter, convert, sink]:
            self.pipeline.add(element)
        
        # Link elements (using your successful approach)
        if not source.link(caps_filter):
            print("ERROR: Could not link source to capsfilter")
            return
        if not caps_filter.link(convert):
            print("ERROR: Could not link capsfilter to convert")
            return
        if not convert.link(sink):
            print("ERROR: Could not link convert to sink")
            return
        
        # Set up bus monitoring
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::error", self.on_error)
        bus.connect("message::eos", self.on_eos)
        
        # Start pipeline
        self.pipeline.set_state(Gst.State.PLAYING)
        self.is_playing = True
        
        # Update UI
        self.preview_button.setText("Stop Preview")
        self.record_button.setEnabled(True)
        print("Camera preview started successfully")
    
    def stop_preview(self):
        """Stop the camera preview"""
        print("Stopping camera preview...")
        
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
        
        self.is_playing = False
        self.preview_button.setText("Start Preview")
        self.record_button.setEnabled(False)
        print("Camera preview stopped")
    
    def toggle_recording(self):
        """Placeholder for recording functionality"""
        print("Recording functionality will be added in next step")
    
    def on_error(self, bus, message):
        """Handle GStreamer errors"""
        error, debug = message.parse_error()
        print(f"GStreamer ERROR: {error.message}")
        if debug:
            print(f"Debug: {debug}")
        self.stop_preview()
    
    def on_eos(self, bus, message):
        """Handle end-of-stream"""
        print("End of stream reached")
        self.stop_preview()

def main():
    app = QApplication(sys.argv)
    
    window = CameraApp()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()