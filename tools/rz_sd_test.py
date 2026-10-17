# rz_sd_test.py – microSD + display test for RadZilla M5 on M5Stack Core2 (UIFlow 2)
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# NOT part of RadZilla: run it by hand in Thonny (F5) right after a restart
# of the Core2. Nothing is changed permanently; the test file is deleted.
#
# Background (UIFlow 2 source + M5GFX): the Core2 display uses SPI3 (VSPI).
# hardware.sdcard with slot=2 uses the same bus and shares it with the
# display; slot=3 would be a second bus on the same pins -> never used here.
#
# Steps – each one shows its number large on the display (3 s):
#   1  draw directly on the display               (blue)
#   2  mount the SD card: slot 2, 4 MHz
#   3  draw directly on the display again         (green)
#   4  create a canvas, draw on it, push it       (purple)
#   5  write / read / delete a test file on the SD card
#   6  draw on the canvas and push it again       (orange)
# Tell me from which step on the display stays black. Copy the summary.
import os
import time
import M5
from M5 import Lcd

SD_SLOT = 2
SD_FREQ = 4_000_000
STEP_MS = 3000
W, H = 320, 240

results = []
canvas = None


def note(ok, name, detail=""):
    line = "%s %-8s %s" % ("OK  " if ok else "FAIL", name, detail)
    print(line)
    results.append(line)


def show(g, step, title, bg, push=False):
    g.fillScreen(bg)
    g.setTextColor(0xFFFFFF, bg)
    g.setTextSize(2)
    g.drawString(title, 10, 10)
    g.setTextSize(10)
    g.drawString(str(step), 130, 80)
    g.setTextSize(1)
    if push:
        g.push(0, 0)
    print("step %d: %s" % (step, title))
    time.sleep_ms(STEP_MS)


def step1():
    show(Lcd, 1, "direct", 0x0000A0)
    note(True, "direct1")


def step2():
    from hardware import sdcard
    try:
        sdcard.SDCard(slot=SD_SLOT, width=1, sck=18, miso=38, mosi=23, cs=4, freq=SD_FREQ)
    except Exception as e:
        note(False, "mount", repr(e))
        return
    ok = "sd" in os.listdir("/")
    note(ok, "mount", "slot %d, %d MHz" % (SD_SLOT, SD_FREQ // 1_000_000))


def step3():
    show(Lcd, 3, "direct after SD", 0x006000)
    note(True, "direct2", "did you see the green 3?")


def step4():
    global canvas
    try:
        canvas = Lcd.newCanvas(W, H, 16)
        show(canvas, 4, "canvas", 0x600060, push=True)
        note(True, "canvas1", "did you see the purple 4?")
    except Exception as e:
        note(False, "canvas1", repr(e))


def step5():
    if "sd" not in os.listdir("/"):
        note(False, "file", "SD not mounted")
        return
    path = "/sd/rz_sd_test.txt"
    try:
        with open(path, "w") as f:
            f.write("RadZilla SD test\n")
        with open(path) as f:
            ok = f.read() == "RadZilla SD test\n"
        os.remove(path)
        st = os.statvfs("/sd")
        note(ok, "file", "free %d MB" % (st[0] * st[3] // (1024 * 1024)))
    except Exception as e:
        note(False, "file", repr(e))


def step6():
    if canvas is None:
        note(False, "canvas2", "no canvas")
        return
    try:
        show(canvas, 6, "canvas after file", 0xA05000, push=True)
        note(True, "canvas2", "did you see the orange 6?")
    except Exception as e:
        note(False, "canvas2", repr(e))


def main():
    M5.begin()
    Lcd.setTextSize(1)
    for fn in (step1, step2, step3, step4, step5, step6):
        try:
            fn()
        except Exception as e:
            note(False, fn.__name__, "crash: %r" % e)
    if canvas is not None:
        try:
            canvas.delete()
        except Exception:
            pass
    Lcd.fillScreen(0x000000)
    Lcd.setTextColor(0xFFFFFF, 0x000000)
    Lcd.setTextSize(2)
    Lcd.drawString("Done - see shell", 10, 110)
    Lcd.setTextSize(1)
    print("\n===== RZ SD TEST SUMMARY =====")
    for ln in results:
        print(ln)
    print("==============================")


main()
