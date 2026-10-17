# main.py – autostart of RadZilla M5 (copy to /flash/main.py).
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# Runs after boot.py when the UIFlow boot option is 0. Hold button A while
# switching on to skip RadZilla (e.g. to work with Thonny).
# Back to the UIFlow menu: in the Thonny shell
#   import esp32; n=esp32.NVS("uiflow"); n.set_u8("boot_option",1); n.commit()
import sys
import time

import M5
from M5 import BtnA

M5.begin()
skip = False
t0 = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), t0) < 300:      # short look at button A
    M5.update()
    if BtnA.isPressed():
        skip = True
        break
    time.sleep_ms(20)

if skip:
    print("RadZilla autostart skipped (button A held)")
else:
    if "/flash" not in sys.path:
        sys.path.insert(0, "/flash")
    from radzilla import app
    app.run()
