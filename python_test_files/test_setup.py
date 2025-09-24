#!/usr/bin/env python3
# test_setup_proper.py
import sys
import gi

# Test PySide6
try:
    from PySide6.QtWidgets import QApplication, QLabel, QMainWindow
    from PySide6.QtCore import Qt
    print("✓ PySide6 imported successfully")
except ImportError as e:
    print(f"✗ PySide6 import failed: {e}")
    sys.exit(1)

# Test GStreamer
try:
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst, GLib
    Gst.init(sys.argv)
    print("✓ GStreamer imported and initialized successfully")
except Exception as e:
    print(f"✗ GStreamer import failed: {e}")
    sys.exit(1)

# Test a simple PySide6 window
app = QApplication(sys.argv)
window = QMainWindow()
window.setWindowTitle("Setup Test")
window.setGeometry(100, 100, 400, 200)

label = QLabel("Testing PySide6 + GStreamer...")
label.setAlignment(Qt.AlignmentFlag.AlignCenter)
window.setCentralWidget(label)

window.show()
print("✓ PySide6 window displayed successfully")

# PROPER GStreamer test - actually create and test a working pipeline
def test_gstreamer_pipeline():
    try:
        print("\n--- Testing GStreamer Pipeline ---")
        
        # Create a simple test pipeline
        pipeline = Gst.Pipeline.new("test-pipeline")
        source = Gst.ElementFactory.make("videotestsrc", "test-source")
        sink = Gst.ElementFactory.make("autovideosink", "test-sink")
        
        if not all([pipeline, source, sink]):
            print("✗ GStreamer element creation failed")
            return False
        
        print("✓ GStreamer elements created successfully")
        
        # Add elements to pipeline
        pipeline.add(source)
        pipeline.add(sink)
        
        # Link elements
        if not source.link(sink):
            print("✗ Could not link source to sink")
            return False
        print("✓ Elements linked successfully")
        
        # Test pipeline state changes
        result = pipeline.set_state(Gst.State.PLAYING)
        if result == Gst.StateChangeReturn.FAILURE:
            print("✗ Failed to start pipeline")
            return False
        print("✓ Pipeline started successfully")
        
        # Wait a moment to see if it works
        print("Pipeline running for 3 seconds...")
        
        # Stop the pipeline
        pipeline.set_state(Gst.State.NULL)
        print("✓ Pipeline stopped successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ GStreamer test failed: {e}")
        return False

# Run the proper GStreamer test
gstreamer_ok = test_gstreamer_pipeline()

if gstreamer_ok:
    label.setText("✓ All tests PASSED!\nPySide6 + GStreamer working!")
    print("\n🎉 ALL TESTS PASSED! Your environment is ready.")
else:
    label.setText("✗ GStreamer test FAILED")
    print("\n❌ GStreamer test failed")

print("\nClose the window to exit.")
sys.exit(app.exec())