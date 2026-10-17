# rz_start.py – starts RadZilla M5.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# Stage 1: open this file in Thonny and press F5 (the folder "radzilla" must
# be uploaded to /flash first, see docs/SETUP.md). Stop with the Stop button.
# Later this file becomes /flash/main.py for the autostart.
import sys

if "/flash" not in sys.path:
    sys.path.insert(0, "/flash")

from radzilla import app

app.run()
