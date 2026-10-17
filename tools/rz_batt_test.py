# rz_batt_test.py – shows the battery / power readings of the Core2 on the display.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# NOT part of RadZilla: start it with F5 in Thonny, then unplug the USB cable –
# the program keeps running on the battery and updates the values every
# second. Plug the cable in again to compare. Stop: button A (or reset).
# Changes nothing.
import time
import M5
from M5 import Lcd, Power, BtnA


def val(name):
    try:
        return getattr(Power, name)()
    except Exception as e:
        return "ERR"


M5.begin()
Lcd.setTextSize(1)
Lcd.fillScreen(0x000000)
rows = (("VBUS", "getVBUSVoltage"), ("CHARGING", "isCharging"),
        ("VBAT", "getBatteryVoltage"), ("CURRENT", "getBatteryCurrent"),
        ("LEVEL", "getBatteryLevel"))
Lcd.setTextColor(0xFFC800, 0x000000)
Lcd.setTextSize(2)
Lcd.drawString("BATTERY TEST  (A = stop)", 8, 6)
while True:
    M5.update()
    if BtnA.wasPressed():
        break
    y = 44
    line = []
    for label, fn in rows:
        v = val(fn)
        line.append("%s=%s" % (label, v))
        Lcd.setTextColor(0x8C8C8C, 0x000000)
        Lcd.drawString(label, 10, y)
        Lcd.setTextColor(0xFFFFFF, 0x000000)
        Lcd.drawString(("%s" % (v,) + "          ")[:12], 150, y)
        y += 34
    print(" ".join(line))
    time.sleep_ms(1000)
Lcd.fillScreen(0x000000)
Lcd.drawString("stopped", 10, 110)
