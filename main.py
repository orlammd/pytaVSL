#!/usr/bin/python

"""This is the main file of pytaVSL, and aims to provide a VJing and lights-projector-virtualisation tool.

Images are loaded as textures, which then are mapped onto slides (canvases - 8 of them).
"""

import time, glob, threading
import pi3d
import liblo

from six.moves import queue

# Setup display and initialiser pi3d
DISPLAY = pi3d.Display.create(background=(0.0, 0.0, 0.0, 1.0), frames_per_second=18)
shader = pi3d.Shader("uv_flat")
CAMERA = pi3d.Camera(is_3d=false)

# Loading files in the queue
iFiles = glob.glob("pix/*.*")
nFi = len(iFiles)
fileQ = queue.Queue()

# Slides
nSli = 8
