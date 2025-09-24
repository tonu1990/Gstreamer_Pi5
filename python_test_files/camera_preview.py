#!/usr/bin/env python3
import sys
import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

Gst.init(sys.argv)

loop = GLib.MainLoop()
pipeline = Gst.Pipeline()

# 1. CREATE ELEMENTS FOR USB CAMERA PREVIEW
# v4l2src for the camera, videoconvert for format conversion, and the sink.
source = Gst.ElementFactory.make("v4l2src", "camera-source")
convert = Gst.ElementFactory.make("videoconvert", "converter")
sink = Gst.ElementFactory.make("autovideosink", "display-sink")

# 2. SET PROPERTIES ON THE SOURCE ELEMENT
# This is how we pass parameters, like the device and caps.
source.set_property("device", "/dev/video0")

# 3. CREATE A CAPABILITIES (CAPS) FILTER
# This forces the camera to use our desired resolution.
caps_filter = Gst.ElementFactory.make("capsfilter", "caps-filter")
caps = Gst.Caps.from_string("video/x-raw,width=640,height=480")
caps_filter.set_property("caps", caps)

# Check for element creation success
elements = [pipeline, source, caps_filter, convert, sink]
if not all(elements):
    print("ERROR: Could not create all elements")
    sys.exit(1)

# 4. ADD ALL ELEMENTS TO THE PIPELINE
for element in [source, caps_filter, convert, sink]:
    pipeline.add(element)

# 5. LINK THE ELEMENTS IN A CHAIN
# The chain is now: source -> caps_filter -> convert -> sink
   
if not source.link(caps_filter):
    print("ERROR: Could not link source to capsfilter")
    sys.exit(1)
            
if not caps_filter.link(convert):
    print("ERROR: Could not link capsfilter to convert")
    sys.exit(1)
            
if not convert.link(sink):
    print("ERROR: Could not link convert to sink")
    sys.exit(1)

# Start the pipeline
pipeline.set_state(Gst.State.PLAYING)
print("Camera preview is playing. Press Ctrl+C to stop.")

try:
    loop.run()
except KeyboardInterrupt:
    print("\nInterrupted by user.")
finally:
    pipeline.set_state(Gst.State.NULL)
    print("Pipeline stopped.")