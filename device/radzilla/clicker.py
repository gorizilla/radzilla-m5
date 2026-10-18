# clicker.py – quiet counter clicks on the CPS page.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# The RadiaCode sends the count rate once per second (no single pulses), so
# the clicks are generated here: every second a 1 s WAV with randomly spaced
# clicks (like a real counter) is built in RAM and played in the background.
# Click rate: 1:1 up to 5 CPS, above logarithmic up to 60 clicks/s
# (CLICK_TABLE). Paused while an alarm / pre-warning effect is running.
# On / off: hold the large radiation symbol on the CPS page for 2 s.
import asyncio
import math
import random
import struct
import time

RATE = 8000                 # samples per second (8-bit mono)
N = RATE                    # 1 s
CLICK = bytes((255, 0, 235, 30, 205, 70, 175, 100, 155, 115, 140, 122, 133, 126))


def _header():
    return (b"RIFF" + struct.pack("<I", 36 + N) + b"WAVEfmt " +
            struct.pack("<IHHIIHH", 16, 1, 1, RATE, RATE, 1, 8) +
            b"data" + struct.pack("<I", N))


def clicks_per_s(cps, table):
    """Click rate for a count rate (table of (CPS, clicks/s), log interpolation)."""
    if cps is None or cps <= 0:
        return 0.0
    c0, r0 = table[0]
    if cps <= c0:
        return cps * r0 / c0
    for (c1, r1) in table[1:]:
        if cps <= c1:
            f = math.log(cps / c0) / math.log(c1 / c0)
            return r0 + (r1 - r0) * f
        c0, r0 = c1, r1
    return float(table[-1][1])


class Clicker:
    def __init__(self, dev, cfg):
        self.dev = dev
        self.c = cfg
        h = _header()
        self.silence = b"\x80" * N
        self.buf = [bytearray(h + self.silence), bytearray(h + self.silence)]
        self.cur = 0
        self.playing = False

    def _fill(self, b, rate):
        mv = memoryview(b)
        mv[44:] = self.silence
        if rate <= 0:
            return 0
        n, t, L = 0, 0.0, len(CLICK)
        while True:
            t += -math.log(1.0 - random.random()) / rate
            pos = int(t * RATE)
            if pos + L > N:
                return n
            mv[44 + pos:44 + pos + L] = CLICK
            n += 1

    async def task(self, S, fx, light, page_cps):
        c = self.c
        nxt = time.ticks_ms()
        while True:
            nxt = time.ticks_add(nxt, 1000)
            d = time.ticks_diff(nxt, time.ticks_ms())
            if d < 0:                               # fell behind: restart timing
                nxt, d = time.ticks_ms(), 0
            await asyncio.sleep_ms(d)
            on = (S.click_on and S.page == page_cps and S.bt_on and S.connected
                  and S.fresh(c.RC_STALE_MS) and not S.modal and not fx.busy(fx.P_GEIGER))
            if not on:
                if self.playing:
                    self.playing = False
                    if not fx.busy(fx.P_GEIGER):
                        self.dev.stop_sound()
                continue
            b = self.buf[self.cur]
            if self._fill(b, clicks_per_s(S.cps, c.CLICK_TABLE)) == 0 and not self.playing:
                continue
            self.dev.play_wav(b, c.CLICK_DIM_VOLUME_PCT if light.dimmed else c.CLICK_VOLUME_PCT)
            self.playing = True
            self.cur ^= 1                           # fill the other buffer next time
