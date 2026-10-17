# core2.py – hardware layer for the M5Stack Core2 (UIFlow 2 firmware).
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# Everything hardware-specific lives here, so another device (e.g. the
# M5Stack StopWatch) only needs its own module with the same interface:
#
#   W, H, LAYOUT                 display size and page layout ("rect" / "round")
#   gfx()                        graphics object to draw on (off-screen canvas)
#   show()                       push the finished frame to the display
#   set_brightness(v)            0..255
#   battery()                    (percent or None, charging True/False/None)
#   now()                        ((Y, M, D, h, m, s), valid)
#   set_volume(pct), tone(hz, ms)
#   accel()                      (x, y, z) in g or None
#   sd_mounted                   True if the microSD card is usable
#   poll()                       list of input events, see EV_*
import os
import time

import M5
from M5 import Lcd

EV_NEXT = "next"            # next page (double tap, swipe left, C)
EV_PREV = "prev"            # previous page (swipe right, A)
EV_DOSE = "dose"            # B: DOSE page
EV_HOLD_B = "hold_b"        # B held: time sync
EV_ACTIVE = "active"        # any touch / button: wakes the display


class Device:
    NAME = "core2"
    W, H = 320, 240
    LAYOUT = "rect"
    TOUCH_H = 240           # touches below this y are the A/B/C buttons

    def __init__(self, cfg):
        self.c = cfg
        M5.begin()
        Lcd.setTextSize(1)              # reset leftovers from other programs
        self.lcd = Lcd
        Lcd.fillScreen(0x000000)        # first LCD access initialises the shared SPI bus
        self.sd_mounted = self._mount_sd()     # before the canvas, like the hardware test
        self.canvas = None
        try:
            self.canvas = Lcd.newCanvas(self.W, self.H, 16)
        except Exception as e:
            print("core2: no canvas (%r), drawing directly" % e)
        self._vol = None
        # touch gesture state
        self._down = None               # (t, x, y) at touch start
        self._last = None               # last (x, y) while touching
        self._last_tap = None
        self._b_held = False
        from M5 import BtnB
        try:
            BtnB.setHoldThresh(cfg.B_HOLD_MS)
        except Exception:
            pass

    # ---------- display ----------
    def gfx(self):
        return self.canvas if self.canvas is not None else Lcd

    def show(self):
        if self.canvas is not None:
            self.canvas.push(0, 0)

    def set_brightness(self, v):
        try:
            Lcd.setBrightness(int(v))
        except Exception as e:
            print("core2: brightness:", repr(e))

    # ---------- power / time ----------
    def battery(self):
        from M5 import Power
        pct = chg = None
        try:
            pct = int(Power.getBatteryLevel())
        except Exception:
            pass
        try:
            chg = bool(Power.isCharging())
        except Exception:
            pass
        return pct, chg

    def now(self):
        t = time.localtime()
        return t[:6], t[0] >= 2025

    # ---------- sound / motion ----------
    def set_volume(self, pct):
        if pct == self._vol:
            return
        self._vol = pct
        from M5 import Speaker
        try:
            Speaker.setVolume(int(255 * max(0, min(100, pct)) / 100))
        except Exception as e:
            print("core2: volume:", repr(e))

    def tone(self, hz, ms):
        from M5 import Speaker
        try:
            Speaker.tone(int(hz), int(ms))
        except Exception as e:
            print("core2: tone:", repr(e))

    def accel(self):
        from M5 import Imu
        try:
            return Imu.getAccel()
        except Exception:
            return None

    # ---------- microSD ----------
    def _mount_sd(self):
        """microSD via the UIFlow driver. slot=2 is SPI3 (VSPI) - the bus of
        the display - and is shared with it. Never use slot=3 (second bus on
        the same pins, takes the lines away from the display). The message
        "[Errno 22] EINVAL" printed by the driver is harmless."""
        try:
            if "sd" in os.listdir("/"):
                return True
        except OSError:
            pass
        try:
            from hardware import sdcard
            sdcard.SDCard(slot=2, width=1, sck=18, miso=38, mosi=23, cs=4,
                          freq=self.c.SD_FREQ)
            if "sd" in os.listdir("/"):
                return True
        except Exception as e:
            print("core2: SD: %r" % e)
        print("core2: no microSD card - logging to flash")
        return False

    # ---------- input ----------
    def poll(self):
        """Call every ~20 ms. Returns a list of EV_* events."""
        from M5 import BtnA, BtnB, BtnC
        M5.update()
        ev = []
        now = time.ticks_ms()
        # touch screen: double tap / swipe (only the display area)
        try:
            n = M5.Touch.getCount()
            x, y = (M5.Touch.getX(), M5.Touch.getY()) if n else (0, 0)
        except Exception:
            n, x, y = 0, 0, 0
        if n and y < self.TOUCH_H:
            if self._down is None:
                self._down = (now, x, y)
                ev.append(EV_ACTIVE)
            self._last = (x, y)
        elif self._down is not None:                       # released
            t0, x0, y0 = self._down
            x1, y1 = self._last or (x0, y0)
            dx, dy = x1 - x0, y1 - y0
            dur = time.ticks_diff(now, t0)
            self._down = None
            if abs(dx) >= self.c.SWIPE_PX and abs(dx) > abs(dy):
                ev.append(EV_NEXT if dx < 0 else EV_PREV)
                self._last_tap = None
            elif dur <= self.c.TAP_MAX_MS and abs(dx) < self.c.TAP_MOVE_PX \
                    and abs(dy) < self.c.TAP_MOVE_PX:
                if self._last_tap is not None and \
                        time.ticks_diff(now, self._last_tap) <= self.c.DOUBLE_TAP_MS:
                    ev.append(EV_NEXT)
                    self._last_tap = None
                else:
                    self._last_tap = now
        # buttons A / B / C (touch areas below the display)
        if BtnA.wasPressed():
            ev += [EV_ACTIVE, EV_PREV]
        if BtnC.wasPressed():
            ev += [EV_ACTIVE, EV_NEXT]
        if BtnB.wasPressed():
            ev.append(EV_ACTIVE)
            self._b_held = False
        try:
            if BtnB.wasHold():
                self._b_held = True
                ev.append(EV_HOLD_B)
        except Exception:
            pass
        if BtnB.wasReleased():
            if not self._b_held:
                ev.append(EV_DOSE)
            self._b_held = False
        return ev
