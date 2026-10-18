# splash.py – start screen: atom (radiation symbol as core, three orbits,
# green electrons), "RadZilla", version, copyright; jingle with LED flashes
# and vibration on every Geiger click. A tap skips it.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# Drawn directly for a 320x240 display; the atom is scaled by SCALE, so a
# round display only needs other positions.
import asyncio
import math
import time

from radzilla.ui import gfx

W, H = 320, 240
CX, CY = 160, 78                    # centre of the atom
SCALE = 2                           # design grid 64x64 -> 128x128 px
YELLOW = 0xFFC800
ORBIT = 0x785A00
ELECTRON = 0x3CE65A
BG = 0x000000
ORBITS = ((0, 1.00), (60, 1.15), (120, 1.30))     # rotation, relative speed
RX, RY = 30 * SCALE, 11 * SCALE
DEG_PER_MS = 0.2                     # electron speed (8° per 40 ms frame)
E_R = 5                              # electron radius

_skip = [False]
_active = [False]


def _ramp(c, f):
    """Colour for 0..1 along green -> yellow -> orange -> red."""
    stops = (c.LED_GREEN, c.LED_YELLOW, c.LED_ORANGE, c.LED_RED)
    f = max(0.0, min(1.0, f)) * (len(stops) - 1)
    i = min(int(f), len(stops) - 2)
    k = f - i
    a, b = stops[i], stops[i + 1]
    return tuple(int(a[j] + (b[j] - a[j]) * k) for j in range(3))


def active():
    return _active[0]


def skip():
    _skip[0] = True


def _orbit_points(rot):
    a = math.radians(rot)
    ca, sa = math.cos(a), math.sin(a)
    pts = []
    for i in range(0, 361, 6):
        t = math.radians(i)
        x, y = RX * math.cos(t), RY * math.sin(t)
        pts.append((int(CX + x * ca - y * sa), int(CY + x * sa + y * ca)))
    return pts


def _pos(rot, deg):
    a, t = math.radians(rot), math.radians(deg)
    x, y = RX * math.cos(t), RY * math.sin(t)
    return (int(CX + x * math.cos(a) - y * math.sin(a)),
            int(CY + x * math.sin(a) + y * math.cos(a)))


def _draw_orbits(g, orbits):
    for pts in orbits:
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            g.drawLine(x0, y0, x1, y1, ORBIT)
            g.drawLine(x0, y0 + 1, x1, y1 + 1, ORBIT)


def _draw_core(g):
    r = 14 * SCALE
    g.fillCircle(CX, CY, r, YELLOW)
    for k in range(3):                               # cut-outs -> radiation symbol
        a = 30 + k * 120
        gfx.arc(g, CX, CY, 0, 11 * SCALE, a - 30, a + 30, BG)
    g.fillCircle(CX, CY, 4 * SCALE, YELLOW)
    g.fillCircle(CX, CY, 2 * SCALE, BG)


def _draw_texts(g, version):
    gfx.text(g, "RadZilla", W // 2, 148, 0xF5F5F5, sc=4, align="center")
    gfx.text(g, version, W // 2, 188, gfx.GREY, align="center")
    gfx.text(g, "(C) 2026 SHIMIZILLA", W // 2, 208, gfx.GREY, align="center")
    gfx.text(g, "TAP = SKIP", W // 2, 230, 0x464646, sc=1, align="center")


async def run(dev, c, version):
    """Show the splash for SPLASH_MS (or until skip())."""
    if not c.SPLASH_ON:
        return
    _active[0] = True
    _skip[0] = False
    g = dev.gfx()
    g.fillScreen(BG)
    orbits = [_orbit_points(rot) for rot, _ in ORBITS]
    _draw_orbits(g, orbits)
    _draw_core(g)
    _draw_texts(g, version)

    data = None
    if c.SPLASH_SOUND_ON:
        try:
            with open("/flash/radzilla/sounds/jingle.wav", "rb") as f:
                data = f.read()
            dev.play_wav(data, c.SPLASH_VOLUME_PCT)
        except Exception as e:
            print("splash: sound:", repr(e))

    clicks = c.SPLASH_CLICKS
    ci = 0
    flash_off = None
    old = []
    t0 = time.ticks_ms()
    try:
        while not _skip[0]:
            el = time.ticks_diff(time.ticks_ms(), t0)
            if el >= c.SPLASH_MS:
                break
            # electrons: erase old, redraw orbits and core, draw new
            for x, y in old:
                g.fillCircle(x, y, E_R + 1, BG)
            if old:
                _draw_orbits(g, orbits)
            new = []
            for k, (rot, speed) in enumerate(ORBITS):
                new.append(_pos(rot, (el * DEG_PER_MS * speed + k * 120) % 360))
            for x, y in new:
                g.fillCircle(x, y, E_R, ELECTRON)
            _draw_core(g)                            # core in front of the orbits
            old = new
            # clicks -> LED flash + vibration
            if ci < len(clicks) and el >= clicks[ci]:
                while ci < len(clicks) and el >= clicks[ci]:
                    ci += 1
                if c.LED_ON:                         # green -> yellow -> orange -> red
                    dev.leds([_ramp(c, (ci - 1) / max(1, len(clicks) - 1))] * 10)
                if c.VIB_ON:
                    dev.vibrate(c.SPLASH_VIB_LEVEL)
                flash_off = el + c.SPLASH_VIB_MS
            if flash_off is not None and el >= flash_off:
                flash_off = None
                dev.leds([(0, 0, 0)] * 10)
                dev.vibrate(0)
            await asyncio.sleep_ms(30)
    finally:
        if _skip[0]:
            dev.stop_sound()
        dev.leds([(0, 0, 0)] * 10)
        dev.vibrate(0)
        data = None
        _active[0] = False
