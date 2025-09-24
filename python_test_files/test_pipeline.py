#!/usr/bin/env python3
import sys
import gi

# Tell the GI repository to require GStreamer version 1.0
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Initialize the GStreamer library
Gst.init(sys.argv)

# Create the main loop. This is what keeps the application running.
loop = GLib.MainLoop()

# 1. CREATE THE PIPELINE
# This is the most important object. It will contain all the elements.
pipeline = Gst.Pipeline()

# 2. CREATE THE ELEMENTS
# We'll create a simple test pattern -> display pipeline.
source = Gst.ElementFactory.make("videotestsrc", "test-source")
sink = Gst.ElementFactory.make("autovideosink", "display-sink")

# 3. CHECK IF ELEMENTS WERE CREATED SUCCESSFULLY
if not pipeline or not source or not sink:
    print("ERROR: Could not create all elements")
    sys.exit(1)

# 4. ADD ELEMENTS TO THE PIPELINE
# The elements must be added to the pipeline before they can be linked.
pipeline.add(source)
pipeline.add(sink)

# 5. LINK THE ELEMENTS TOGETHER
# This is the equivalent of the '!' in gst-launch-1.0
if not source.link(sink):
    print("ERROR: Could not link source to sink")
    sys.exit(1)

# 6. START THE PIPELINE
# This sets the pipeline's state to PLAYING, which starts data flow.
pipeline.set_state(Gst.State.PLAYING)
print("Pipeline is playing. Press Ctrl+C to stop.")

try:
    # 7. RUN THE MAIN LOOP
    # This keeps the script alive, processing messages from the pipeline.
    loop.run()
except KeyboardInterrupt:
    print("\nInterrupted by user.")
finally:
    # 8. CLEAN UP ON EXIT
    # Stop the pipeline and free resources.
    pipeline.set_state(Gst.State.NULL)
    print("Pipeline stopped.")