# rz_sd_test2.py – canvas + microSD test 2 for RadZilla M5 on M5Stack Core2 (UIFlow 2)
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# NOT part of RadZilla: run it by hand in Thonny (F5) right after a restart
# of the Core2. Nothing is changed permanently; the test file is deleted.
#
# Test 1 showed: SD (slot 2) works, direct drawing works, but a canvas pushed
# after mounting the SD card does not reach the display. Variants:
#   0   canvas before SD                                  (white "0")
#   A   canvas created BEFORE mounting, pushed after      (purple "A")
#   B   push framed by Lcd.startWrite() / endWrite()      (orange "B")
#   C   SD unmounted + released again, then push          (cyan "C")
#   C2  mount -> write -> unmount once more, then push    (cyan "C2")
#   D   direct drawing as a final check                   (green "D")
# The SD card is mounted with machine.SDCard(slot=2) - exactly what UIFlow's
# hardware.sdcard does internally - so the test can release it again.
# Tell me which letters you saw. Copy the summary.
import os
import time
import machine
import M5
from M5 import Lcd

SD_FREQ = 4_000_000
STEP_MS = 3000
W, H = 320, 240

results = []
sd = None


def note(ok, name, detail=""):
    line = "%s %-6s %s" % ("OK  " if ok else "FAIL", name, detail)
    print(line)
    results.append(line)


def draw(g, label, title, bg):
    g.fillScreen(bg)
    g.setTextColor(0xFFFFFF if bg != 0xFFFFFF else 0x000000, bg)
    g.setTextSize(2)
    g.drawString(title, 10, 10)
    g.setTextSize(10)
    g.drawString(label, 110, 80)
    g.setTextSize(1)


def wait(label, title):
    print("step %s: %s" % (label, title))
    time.sleep_ms(STEP_MS)


def mount():
    global sd
    sd = machine.SDCard(slot=2, width=1, sck=18, miso=38, mosi=23, cs=4, freq=SD_FREQ)
    os.mount(sd, "/sd")


def release():
    global sd
    os.umount("/sd")
    sd.deinit()
    sd = None


def file_test():
    path = "/sd/rz_sd_test2.txt"
    with open(path, "w") as f:
        f.write("RadZilla\n")
    with open(path) as f:
        ok = f.read() == "RadZilla\n"
    os.remove(path)
    return ok


def main():
    M5.begin()
    Lcd.setTextSize(1)
    c = Lcd.newCanvas(W, H, 16)

    draw(c, "0", "canvas, no SD yet", 0xFFFFFF)
    c.push(0, 0)
    note(True, "0", "white 0?")
    wait("0", "canvas before SD")

    try:
        mount()
        note(True, "mount", "free %d MB" % (os.statvfs("/sd")[0] * os.statvfs("/sd")[3] // 1048576))
    except Exception as e:
        note(False, "mount", repr(e))

    try:
        draw(c, "A", "canvas made before SD", 0x600060)
        c.push(0, 0)
        note(True, "A", "purple A?")
    except Exception as e:
        note(False, "A", repr(e))
    wait("A", "variant A")

    try:
        draw(c, "B", "startWrite/endWrite", 0xA05000)
        Lcd.startWrite()
        c.push(0, 0)
        Lcd.endWrite()
        note(True, "B", "orange B?")
    except Exception as e:
        note(False, "B", repr(e))
    wait("B", "variant B")

    try:
        ok = file_test() if sd else False
        release()
        draw(c, "C", "SD released", 0x006070)
        c.push(0, 0)
        note(True, "C", "cyan C? (file %s)" % ok)
    except Exception as e:
        note(False, "C", repr(e))
    wait("C", "variant C")

    try:
        mount()
        ok = file_test()
        release()
        draw(c, "C2", "mount-write-release", 0x006070)
        c.push(0, 0)
        note(True, "C2", "cyan C2? (file %s)" % ok)
    except Exception as e:
        note(False, "C2", repr(e))
    wait("C2", "variant C2")

    try:
        c.delete()
    except Exception:
        pass
    draw(Lcd, "D", "direct, end", 0x006000)
    note(True, "D", "green D?")
    wait("D", "direct")

    print("\n===== RZ SD TEST 2 SUMMARY =====")
    for ln in results:
        print(ln)
    print("================================")


main()
