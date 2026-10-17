# core2.py – hardware layer for the M5Stack Core2 (UIFlow 2 firmware).
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# Everything hardware-specific lives here, so another device (e.g. the
# M5Stack StopWatch) only needs its own module with the same interface:
#
#   W, H, LAYOUT                 display size and page layout ("rect" / "round")
#   gfx()                        graphics object to draw on
#   show()                       finish a frame (no-op when drawing directly)
#   set_brightness(v)            0..255
#   battery()                    (percent or None, "bat" / "chg" / "full")
#   power_off()                  switch the device off
#   now()                        ((Y, M, D, h, m, s), valid)
#   set_volume(pct), tone(hz, ms)
#   vibrate(level)               vibration motor 0..255
#   leds(colors)                 LED bar(s), list of (r, g, b)
#   play_wav(data, pct), stop_sound()  WAV from RAM, plays in the background
#   accel()                      (x, y, z) in g or None
#   sd_mounted                   True if the microSD card is usable
#   poll()                       list of input events, see EV_*
#   set_utc(unix)                set the clock (UTC)
import os
import time

import M5
from M5 import Lcd

EV_NEXT = "next"            # next page (swipe right, C)
EV_DTAP = "dtap"            # double tap on the display (next page)
EV_TAP = "tap"              # single tap: (EV_TAP, x, y) – buttons on the SET page
EV_PREV = "prev"            # previous page (swipe left, A)
EV_DOSE = "dose"            # B: DOSE page
EV_HOLD_B = "hold_b"        # B held: Bluetooth off / on
EV_ACTIVE = "active"        # any touch / button: wakes the display


_LIPO = ((4200, 100), (4100, 90), (4000, 80), (3900, 65), (3800, 50), (3750, 40),
         (3700, 30), (3650, 20), (3600, 10), (3500, 5), (3300, 0))


def _lipo_pct(mv):
    """Rough LiPo charge level from the resting voltage (mV)."""
    if mv >= _LIPO[0][0]:
        return 100
    for (v1, p1), (v0, p0) in zip(_LIPO, _LIPO[1:]):
        if mv >= v0:
            return int(p0 + (p1 - p0) * (mv - v0) / (v1 - v0) + 0.5)
    return 0


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
        self.sd_mounted = self._mount_sd()
        self._vol = None
        self._bat_mv = None
        import machine
        self._led_pin = machine.Pin(25, machine.Pin.OUT)
        try:
            from M5 import Speaker
            Speaker.begin()
        except Exception:
            pass
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
        # Direct drawing: a pushed canvas does not reliably reach the Core2
        # display (tools/rz_sd_test2.py), so the pages redraw only changes.
        return Lcd

    def show(self):
        pass

    def set_brightness(self, v):
        try:
            Lcd.setBrightness(int(v))
        except Exception as e:
            print("core2: brightness:", repr(e))

    # ---------- power / time ----------
    def battery(self):
        """(percent or None, mode). mode: "bat" on battery, "chg" charging,
        "full" cable in and charged.

        Measured on the Core2 (UIFlow 2.5.3): the USB voltage reads ~5.1 V
        also without cable (internal 5 V boost) -> not usable; the battery
        current is +mA with the cable and -mA on battery. The level is
        computed from the battery voltage corrected by current x internal
        resistance (UIFlow's getBatteryLevel() already shows 100 % at 4.12 V)."""
        from M5 import Power

        def call(name):
            try:
                return getattr(Power, name)()
            except Exception:
                return None

        charging = bool(call("isCharging"))
        ma = call("getBatteryCurrent")
        mv = call("getBatteryVoltage")
        cable = charging or (ma is not None and ma > -self.c.BAT_CABLE_MA)
        if cable and not charging:
            self._bat_mv = None
            return 100, "full"
        if mv is None:
            pct = call("getBatteryLevel")
            return (int(pct) if pct is not None else None), ("chg" if cable else "bat")
        if mv < 100:                                     # volts -> mV
            mv *= 1000
        rest = mv - (ma or 0) * self.c.BAT_RINT_MOHM / 1000   # resting voltage
        if self._bat_mv is None or abs(rest - self._bat_mv) > 150:
            self._bat_mv = rest
        else:
            self._bat_mv += 0.2 * (rest - self._bat_mv)      # smooth
        return _lipo_pct(self._bat_mv), ("chg" if cable else "bat")

    def power_off(self):
        """Switch the whole device off (power button switches it on again)."""
        from M5 import Power
        try:
            Power.powerOff()
        except Exception as e:
            print("core2: powerOff:", repr(e))

    def now(self):
        """German local time from the clock (which runs in UTC):
        ((Y, M, D, h, m, s), valid). Valid only after a time sync."""
        from radzilla.core import timesync
        try:
            import machine
            r = machine.RTC().datetime()        # UIFlow: UTC (Y, M, D, wd, h, m, s, us)
            utc = (r[0], r[1], r[2], r[4], r[5], r[6])
        except Exception:
            utc = time.gmtime()[:6]
        if utc[0] < 2025:
            return utc, False
        return timesync.berlin_from_unix(timesync.unix_from_utc(utc))[:6], True

    def set_utc(self, unix):
        """Set system time and the battery-backed BM8563 (UIFlow's
        machine.RTC().datetime() writes both) to UTC."""
        from radzilla.core import timesync
        import machine
        days, rem = divmod(unix, 86400)
        y, m, d = timesync.civil_from_days(days)
        wd = (days + 3) % 7                      # 0 = Monday
        machine.RTC().datetime((y, m, d, wd, rem // 3600, (rem % 3600) // 60, rem % 60, 0))

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

    def vibrate(self, level):
        """Vibration motor 0..255 (0 = off)."""
        from M5 import Power
        try:
            Power.setVibration(int(level))
        except Exception as e:
            print("core2: vibration:", repr(e))

    def leds(self, colors, level_pct=None):
        """10 SK6812 LEDs of the M5GO Bottom2 (G25), colours (r, g, b) 0..255,
        scaled by level_pct (default LED_LEVEL_PCT). Numbered clockwise,
        0..4 one side, 5..9 other side."""
        k = (self.c.LED_LEVEL_PCT if level_pct is None else level_pct) / 100
        buf = bytearray()
        for r, g, b in colors:
            buf += bytes((int(g * k), int(r * k), int(b * k)))   # GRB order
        try:
            import machine
            machine.bitstream(self._led_pin, 0, (400, 850, 800, 450), buf)
        except Exception as e:
            print("core2: leds:", repr(e))

    def play_wav(self, data, vol_pct):
        """Play WAV data from RAM in the background (keep data referenced)."""
        from M5 import Speaker
        self.set_volume(vol_pct)
        try:
            Speaker.playWav(data, 1, 0, True)
        except Exception as e:
            print("core2: playWav:", repr(e))

    def stop_sound(self):
        from M5 import Speaker
        try:
            Speaker.stop()
        except Exception:
            pass

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
                ev.append(EV_NEXT if dx > 0 else EV_PREV)     # swipe right = next page
                self._last_tap = None
            elif dur <= self.c.TAP_MAX_MS and abs(dx) < self.c.TAP_MOVE_PX \
                    and abs(dy) < self.c.TAP_MOVE_PX:
                ev.append((EV_TAP, x0, y0))               # single tap with position
                if self._last_tap is not None and \
                        time.ticks_diff(now, self._last_tap) <= self.c.DOUBLE_TAP_MS:
                    ev.append(EV_DTAP)
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
