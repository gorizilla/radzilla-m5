# splash.py – start screen: atom (radiation symbol as core, three orbits,
# green electrons), "RadZilla", version, copyright; jingle with LED
# animation and vibration on every Geiger click. A tap skips it.
#
# LEDs (own task, steady 25 ms steps, independent of drawing): three dim
# green dots circle the 10 LEDs with the electrons; every click flashes all
# LEDs and fades out (~150 ms), colour green -> yellow -> orange -> red over
# the jingle; after the last click red, then a soft fade-out.
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
FRAME_MS = 40                        # atom: ~25 frames per second
LAG_MS = 250                         # LEDs: max. delay behind the jingle

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


def _led_frame(c, el, ci, clicks, fstart):
    """LED colours at el ms; ci = clicks already played, fstart = el at
    which the flash of the latest click started."""
    n = len(clicks)
    last = clicks[-1] if n else 0
    leds = [(0, 0, 0)] * 10
    if el < last:                                    # three dots circle with the atom
        pos = (el * DEG_PER_MS / 36.0) % 10          # 36° per LED
        gr = c.LED_GREEN
        for k in range(3):
            p = (pos + k * 10 / 3) % 10
            i = int(p)
            f = p - i
            for j, w in ((i, 1 - f), ((i + 1) % 10, f)):
                a = 0.35 * w
                old = leds[j]
                leds[j] = (max(old[0], int(gr[0] * a)), max(old[1], int(gr[1] * a)),
                           max(old[2], int(gr[2] * a)))
    if ci:
        d = el - fstart
        col = _ramp(c, (ci - 1) / max(1, n - 1))
        if ci == n:                                  # last click: red, hold, fade out
            k = 1.0 if d < c.SPLASH_HOLD_MS else max(0.0, 1 - (d - c.SPLASH_HOLD_MS) / c.SPLASH_FADE_MS)
        else:
            k = max(0.0, 1 - d / c.SPLASH_FLASH_MS)
        if k > 0:
            leds = [(int(b[0] + (col[0] - b[0]) * k), int(b[1] + (col[1] - b[1]) * k),
                     int(b[2] + (col[2] - b[2]) * k)) for b in leds]
    return leds


async def _led_task(dev, c, t0):
    """LED animation on its own clock: if the task is held up (drawing,
    Bluetooth), it continues where it stopped (max. 40 ms per step) instead
    of skipping, so no flash is lost; it never lags more than LAG_MS behind
    the jingle. One click per step, every click gets its own flash."""
    clicks = c.SPLASH_CLICKS
    n = len(clicks)
    ci, fstart = 0, 0
    vel = 0                                          # virtual elapsed ms
    last = time.ticks_ms()
    vib_off = None
    while True:
        now = time.ticks_ms()
        vel += min(time.ticks_diff(now, last), 40)
        last = now
        real = time.ticks_diff(now, t0)
        if real - vel > LAG_MS:
            vel = real - LAG_MS
        if ci < n and vel >= clicks[ci]:             # next click: flash + vibration
            ci += 1
            fstart = vel
            if c.VIB_ON:
                dev.vibrate(c.SPLASH_VIB_LEVEL)
                vib_off = vel + c.SPLASH_VIB_MS
        if vib_off is not None and vel >= vib_off:
            vib_off = None
            dev.vibrate(0)
        if c.LED_ON:
            dev.leds(_led_frame(c, vel, ci, clicks, fstart))
        await asyncio.sleep_ms(25)


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
            _seg(g, pts[i], pts[i + 1])


def _seg(g, p0, p1):
    x0, y0 = p0
    x1, y1 = p1
    g.drawLine(x0, y0, x1, y1, ORBIT)
    g.drawLine(x0, y0 + 1, x1, y1 + 1, ORBIT)


def _repair_orbits(g, orbits, spots):
    """Redraw only the orbit segments near erased electrons."""
    r = E_R + 3
    for pts in orbits:
        for i in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[i], pts[i + 1]
            for x, y in spots:
                if min(x0, x1) - r <= x <= max(x0, x1) + r and \
                        min(y0, y1) - r <= y <= max(y0, y1) + r:
                    _seg(g, pts[i], pts[i + 1])
                    break


def _near_core(spots):
    lim = (14 * SCALE + E_R + 2) ** 2
    return any((x - CX) ** 2 + (y - CY) ** 2 <= lim for x, y in spots)


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
    old = []
    t0 = time.ticks_ms()
    led = asyncio.create_task(_led_task(dev, c, t0))
    try:
        while not _skip[0]:
            el = time.ticks_diff(time.ticks_ms(), t0)
            if el >= c.SPLASH_MS:
                break
            # electrons: erase old, repair the orbits there, draw new; the
            # core only when an electron was / is in front of it
            for x, y in old:
                g.fillCircle(x, y, E_R + 1, BG)
            if old:
                _repair_orbits(g, orbits, old)
            await asyncio.sleep_ms(0)                # let the LEDs run
            new = []
            for k, (rot, speed) in enumerate(ORBITS):
                new.append(_pos(rot, (el * DEG_PER_MS * speed + k * 120) % 360))
            for x, y in new:
                g.fillCircle(x, y, E_R, ELECTRON)
            if _near_core(old + new):
                _draw_core(g)                        # core in front of the orbits
            old = new
            await asyncio.sleep_ms(FRAME_MS)
    finally:
        led.cancel()
        if _skip[0]:
            dev.stop_sound()
        dev.leds([(0, 0, 0)] * 10)
        dev.vibrate(0)
        data = None
        _active[0] = False
