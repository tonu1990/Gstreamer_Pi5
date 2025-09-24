#!/usr/bin/env python3
import sys
import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Initialize GStreamer
Gst.init(sys.argv)

class CameraApp:
    def __init__(self):
        self.pipeline = None
        self.loop = GLib.MainLoop()
        self.setup_pipeline()
        
    def setup_pipeline(self):
        """Create and configure the pipeline"""
        # Create the pipeline and elements
        self.pipeline = Gst.Pipeline.new("camera-pipeline")
        
        source = Gst.ElementFactory.make("v4l2src", "camera-source")
        caps_filter = Gst.ElementFactory.make("capsfilter", "caps-filter")
        convert = Gst.ElementFactory.make("videoconvert", "converter")
        sink = Gst.ElementFactory.make("autovideosink", "display-sink")
        
        # Verify element creation
        if not all([source, caps_filter, convert, sink]):
            print("ERROR: Could not create all elements")
            sys.exit(1)
            
        # Configure elements
        source.set_property("device", "/dev/video0")
        caps = Gst.Caps.from_string("video/x-raw,width=640,height=480")
        caps_filter.set_property("caps", caps)
        
        # Add elements to pipeline
        for element in [source, caps_filter, convert, sink]:
            self.pipeline.add(element)
        
        # Link elements one by one (as you discovered works best!)
        if not source.link(caps_filter):
            print("ERROR: Could not link source to capsfilter")
            sys.exit(1)
        if not caps_filter.link(convert):
            print("ERROR: Could not link capsfilter to convert")
            sys.exit(1)
        if not convert.link(sink):
            print("ERROR: Could not link convert to sink")
            sys.exit(1)
        
        # === CRITICAL NEW PART: CONNECT SIGNAL HANDLERS ===
        # Connect the error signal to our callback function
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()  # Enable signal monitoring
        bus.connect("message::error", self.on_error)
        bus.connect("message::eos", self.on_eos)
        bus.connect("message::warning", self.on_warning)
        
        print("Pipeline created successfully with signal handlers")
    
    def on_error(self, bus, message):
        """Called when an error occurs"""
        error, debug = message.parse_error()
        print(f"ERROR: {error.message}")
        if debug:
            print(f"Debug info: {debug}")
        print("Stopping pipeline...")
        self.loop.quit()
    
    def on_eos(self, bus, message):
        """Called when end-of-stream is reached"""
        print("End of stream reached")
        self.loop.quit()
    
    def on_warning(self, bus, message):
        """Called when a warning occurs"""
        warning, debug = message.parse_warning()
        print(f"WARNING: {warning.message}")
        if debug:
            print(f"Debug info: {debug}")
    
    def run(self):
        """Start the application"""
        try:
            # Start the pipeline
            self.pipeline.set_state(Gst.State.PLAYING)
            print("Camera preview is running. Press Ctrl+C to stop.")
            
            # Run the main loop
            self.loop.run()
            
        except KeyboardInterrupt:
            print("\nInterrupted by user.")
        finally:
            # Cleanup
            self.pipeline.set_state(Gst.State.NULL)
            print("Pipeline stopped.")

# Create and run the application
if __name__ == "__main__":
    app = CameraApp()
    app.run()