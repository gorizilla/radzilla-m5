# clicker.py – counter clicks on the CPS page.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# The RadiaCode sends the count rate once per second (no single pulses), so
# the clicks are generated here: every CLICK_CHUNK_MS a WAV of that length
# (16 kHz, 8 bit) with
# randomly spaced clicks (like a real counter) is built in RAM and played in
# the background.
#   search range up to CLICK_LIVE_CPS: clicks 1:1 with the CPS, soft tick,
#     pitch rises slightly with the rate
#   above: denser, louder and harder (CLICK_*_TABLE), max. 70 % volume
#   above DANGER (~300 CPS): every click gets a short tail in the timbre of
#     the DANGER siren, the tails merge into a subtle monotone scream
# Paused while an alarm / pre-warning effect is running.
# On / off: hold the large radiation symbol on the CPS page for 2 s.
import asyncio
import math
import random
import struct
import time

RATE = 16000                # samples per second (8-bit mono)


def _header(n):
    return (b"RIFF" + struct.pack("<I", 36 + n) + b"WAVEfmt " +
            struct.pack("<IHHIIHH", 16, 1, 1, RATE, RATE, 1, 8) +
            b"data" + struct.pack("<I", n))


def table(x, pts):
    """Value for x from a (x, value) table, logarithmic interpolation."""
    if x <= pts[0][0]:
        return pts[0][1]
    for (a, va), (b, vb) in zip(pts, pts[1:]):
        if x <= b:
            return va + (vb - va) * math.log(x / a) / math.log(b / a)
    return pts[-1][1]


def clicks_per_s(cps, c):
    if cps is None or cps <= 0:
        return 0.0
    if cps <= c.CLICK_LIVE_CPS:
        return float(cps)                         # search range: 1:1
    return table(cps, c.CLICK_RATE_TABLE)


def volume(cps, c, dimmed):
    v = table(max(cps or 0, c.CLICK_VOL_TABLE[0][0]), c.CLICK_VOL_TABLE)
    return v * c.CLICK_DIM_FACTOR if dimmed else v


def make_click(cps, c):
    """One click (bytes, 8-bit unsigned) for this count rate."""
    x = max(cps, 3)
    h = table(x, c.CLICK_HARD_TABLE)
    f = table(x, c.CLICK_PITCH_TABLE)
    s = table(x, c.CLICK_SCREAM_TABLE) if x > c.CLICK_SCREAM_TABLE[0][0] else 0.0
    tau = 0.0016 - 0.0010 * h
    noise = 0.5 * h
    n = int(RATE * (tau * 5 + s * 0.012))
    w1 = 2 * math.pi * f / RATE
    ws = 2 * math.pi * c.CLICK_SCREAM_HZ / RATE
    mix = c.CLICK_SCREAM_MIX * s
    out = bytearray(n)
    peak = 0.0
    vals = []
    for i in range(n):
        t = i / RATE
        v = ((1 - noise) * math.sin(w1 * i) + noise * (random.random() * 2 - 1)) * math.exp(-t / tau)
        if mix:
            v += mix * (0.5 * math.sin(ws * i) + 0.5 * math.sin(ws * 1.006 * i)
                        + 0.25 * math.sin(2 * ws * i)) * math.exp(-t / 0.006)
        vals.append(v)
        peak = max(peak, abs(v))
    k = 120 / (peak or 1)
    for i, v in enumerate(vals):
        out[i] = 128 + int(v * k)
    return bytes(out)


class Clicker:
    def __init__(self, dev, cfg):
        self.dev = dev
        self.c = cfg
        self.ms = cfg.CLICK_CHUNK_MS
        self.n = RATE * self.ms // 1000           # samples per chunk
        h = _header(self.n)
        self.silence = b"\x80" * self.n
        self.buf = [bytearray(h + self.silence), bytearray(h + self.silence)]
        self.cur = 0
        self.playing = False

    def _fill(self, b, rate, click):
        mv = memoryview(b)
        mv[44:] = self.silence
        if rate <= 0:
            return 0
        n, t, L, N = 0, 0.0, len(click), self.n
        while True:
            t += -math.log(1.0 - random.random()) / rate
            pos = int(t * RATE)
            if pos >= N:
                return n
            end = min(N, pos + L)
            mv[44 + pos:44 + end] = click[:end - pos]
            n += 1

    async def task(self, S, fx, light, page_cps):
        c = self.c
        nxt = time.ticks_ms()
        while True:
            nxt = time.ticks_add(nxt, self.ms)
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
            cps = S.cps or 0
            b = self.buf[self.cur]
            if self._fill(b, clicks_per_s(cps, c), make_click(cps, c)) == 0 and not self.playing:
                continue
            self.dev.play_wav(b, volume(cps, c, light.dimmed))
            self.playing = True
            self.cur ^= 1                           # fill the other buffer next time
