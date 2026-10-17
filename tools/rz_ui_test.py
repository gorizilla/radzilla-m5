# rz_ui_test.py – drawing / design test 2 for RadZilla M5 on M5Stack Core2 (UIFlow 2)
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
# NOT part of RadZilla: run it by hand in Thonny (F5). Changes nothing.
#
# Design A1: straight 7-segment digits (with dim "ghost" segments) and a
# self-drawn 5x7 dot-matrix font for all labels.
#   0  fillArc probe     which call variant works (exact error is printed)
#   1  static page       5 s to look at / take a photo
#   2  full redraw       5 s, whole page redrawn per frame (frames/s)
#   3  partial redraw    5 s, only the value and the ring redrawn (frames/s)
#   4  ASCII7 font       built-in pixel font instead of the dot matrix:
#                        4 s static, then 5 s full redraw (frames/s)
# Copy the summary from the shell at the end.
import math
import time
import M5
from M5 import Lcd

W, H = 320, 240
BG = 0x000000
Y = 0xFFC800
YD = 0x6E5600
GHOST = 0x181300
WH = 0xF0F0F0
GR = 0x8C8C8C
DK = 0x262626
GN = 0x28DC5A

results = []


def note(ok, name, detail=""):
    line = "%s %-10s %s" % ("OK  " if ok else "FAIL", name, detail)
    print(line)
    results.append(line)


# ---------- 5x7 dot-matrix font (stored as horizontal runs -> few fillRect calls) -----
_F57 = {
    "0": (" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "),
    "1": ("  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "),
    "2": (" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"),
    "3": ("#####", "   # ", "  #  ", "   # ", "    #", "#   #", " ### "),
    "4": ("   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "),
    "5": ("#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "),
    "6": ("  ## ", " #   ", "#    ", "#### ", "#   #", "#   #", " ### "),
    "7": ("#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "),
    "8": (" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "),
    "9": (" ### ", "#   #", "#   #", " ####", "    #", "   # ", " ##  "),
    "A": (" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"),
    "B": ("#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "),
    "C": (" ### ", "#   #", "#    ", "#    ", "#    ", "#   #", " ### "),
    "D": ("#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "),
    "E": ("#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"),
    "F": ("#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "),
    "G": (" ### ", "#   #", "#    ", "# ###", "#   #", "#   #", " ####"),
    "H": ("#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"),
    "I": (" ### ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "),
    "K": ("#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"),
    "L": ("#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"),
    "M": ("#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"),
    "N": ("#   #", "#   #", "##  #", "# # #", "#  ##", "#   #", "#   #"),
    "O": (" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "),
    "P": ("#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "),
    "R": ("#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"),
    "S": (" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "),
    "T": ("#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "),
    "V": ("#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "),
    "u": ("     ", "     ", "#   #", "#   #", "#   #", "#  ##", " ## #"),
    "v": ("     ", "     ", "#   #", "#   #", "#   #", " # # ", "  #  "),
    "h": ("#    ", "#    ", "# ## ", "##  #", "#   #", "#   #", "#   #"),
    ".": ("     ", "     ", "     ", "     ", "     ", " ##  ", " ##  "),
    ":": ("     ", " ##  ", " ##  ", "     ", " ##  ", " ##  ", "     "),
    "%": ("##   ", "##  #", "   # ", "  #  ", " #   ", "#  ##", "   ##"),
    "/": ("     ", "    #", "   # ", "  #  ", " #   ", "#    ", "     "),
    "-": ("     ", "     ", "     ", "#####", "     ", "     ", "     "),
    " ": ("     ",) * 7,
}


def _runs(rows):
    out = []
    for ry, row in enumerate(rows):
        rx = 0
        while rx < 5:
            if row[rx] == "#":
                n = 1
                while rx + n < 5 and row[rx + n] == "#":
                    n += 1
                out.append((rx, ry, n))
                rx += n
            else:
                rx += 1
    return out


GLYPH = {k: _runs(v) for k, v in _F57.items()}

TEXT_MODE = ["matrix"]          # "matrix" = self-drawn, "ascii7" = built-in font


def mtext(g, s, x, y, col, bg=BG, right=False, sc=2):
    w = len(s) * 6 * sc - sc
    if right:
        x -= w
    if TEXT_MODE[0] == "ascii7":
        g.setFont(Lcd.FONTS.ASCII7)
        g.setTextSize(sc)
        g.setTextColor(col, bg)
        g.drawString(s, x, y)
        g.setTextSize(1)
        return w
    for ch in s:
        for rx, ry, n in GLYPH.get(ch, ()):
            g.fillRect(x + rx * sc, y + ry * sc, n * sc, sc, col)
        x += 6 * sc
    return w


# ---------- arcs: probe fillArc, fall back to triangles -----------------------------------
ARC_MODE = [None]               # index of the working fillArc variant, or None


def _arc_variant(i, g, cx, cy, r0, r1, a0, a1, col):
    if i == 0:                   # as is (floats, negative angles allowed)
        g.fillArc(cx, cy, r0, r1, a0, a1, col)
    elif i == 1:                 # integers
        g.fillArc(int(cx), int(cy), int(r0), int(r1), int(a0), int(a1), col)
    else:                        # integers, angles shifted into 0..360+
        s = int(a0) % 360
        g.fillArc(int(cx), int(cy), int(r0), int(r1), s, s + int(a1 - a0), col)


def probe_arc():
    errs = []
    for i in range(3):
        try:
            _arc_variant(i, Lcd, 160, 120, 20, 30, -90, -30, Y)
            ARC_MODE[0] = i
            break
        except Exception as e:
            errs.append("v%d %r" % (i, e))
    Lcd.fillScreen(BG)
    note(ARC_MODE[0] is not None, "fillArc",
         ("variant %d works" % ARC_MODE[0]) if ARC_MODE[0] is not None else "")
    for e in errs:
        print("     ", e)
        results.append("      " + e)


def arc(g, cx, cy, r0, r1, a0, a1, col):
    if ARC_MODE[0] is not None:
        _arc_variant(ARC_MODE[0], g, cx, cy, r0, r1, a0, a1, col)
        return
    steps = max(2, int((a1 - a0) / 6))
    for i in range(steps):
        t0 = math.radians(a0 + (a1 - a0) * i / steps)
        t1 = math.radians(a0 + (a1 - a0) * (i + 1) / steps)
        c0, s0, c1, s1 = math.cos(t0), math.sin(t0), math.cos(t1), math.sin(t1)
        p0 = (int(cx + r1 * c0), int(cy + r1 * s0))
        p1 = (int(cx + r1 * c1), int(cy + r1 * s1))
        p2 = (int(cx + r0 * c1), int(cy + r0 * s1))
        p3 = (int(cx + r0 * c0), int(cy + r0 * s0))
        g.fillTriangle(p0[0], p0[1], p1[0], p1[1], p2[0], p2[1], col)
        g.fillTriangle(p0[0], p0[1], p2[0], p2[1], p3[0], p3[1], col)


def trefoil(g, cx, cy, r, col):
    for a in (90, 210, 330):
        arc(g, cx, cy, int(r * 0.32), r, a - 30, a + 30, col)
    g.fillCircle(cx, cy, max(2, int(r * 0.18)), col)


RING_CX, RING_CY = 82, 131


def ring(g, frac, n=30):
    filled = int(frac * n + 0.5)
    for i in range(n):
        a0 = -90 + i * 12 + 2
        arc(g, RING_CX, RING_CY, 52, 62, a0, a0 + 8, Y if i < filled else DK)


# ---------- 7-segment digits -----------------------------------------------------------------
SEG = {"0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg", "5": "acdfg",
       "6": "acdefg", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", " ": ""}
DIG_W, DIG_H, DIG_T, DIG_GAP, DIG_N = 26, 48, 6, 8, 4


def _seg_polys(x, y, w, h, t):
    m = h // 2
    ht = t // 2
    gp = 1

    def hor(yy):
        return ((x + ht + gp, yy), (x + t + gp, yy - ht), (x + w - t - gp, yy - ht),
                (x + w - ht - gp, yy), (x + w - t - gp, yy + ht), (x + t + gp, yy + ht))

    def ver(xx, y0, y1):
        return ((xx, y0 + gp), (xx + ht, y0 + ht + gp), (xx + ht, y1 - ht - gp),
                (xx, y1 - gp), (xx - ht, y1 - ht - gp), (xx - ht, y0 + ht + gp))

    return {"a": hor(y + ht), "g": hor(y + m), "d": hor(y + h - ht),
            "f": ver(x + ht, y + ht, y + m), "e": ver(x + ht, y + m, y + h - ht),
            "b": ver(x + w - ht, y + ht, y + m), "c": ver(x + w - ht, y + m, y + h - ht)}


def _poly(g, p, col):            # convex polygon as triangle fan
    x0, y0 = p[0]
    for i in range(1, len(p) - 1):
        g.fillTriangle(x0, y0, p[i][0], p[i][1], p[i + 1][0], p[i + 1][1], col)


def seg_number(g, s, x_right, y):
    digits, dots = [], []
    for ch in s:
        if ch == ".":
            dots.append(len(digits) - 1)
        else:
            digits.append(ch)
    pad = DIG_N - len(digits)
    digits = [" "] * pad + digits
    dots = [i + pad for i in dots]
    x0 = x_right - DIG_N * (DIG_W + DIG_GAP)
    for i in range(DIG_N):
        x = x0 + i * (DIG_W + DIG_GAP)
        on = SEG.get(digits[i], "")
        for k, p in _seg_polys(x, y, DIG_W, DIG_H, DIG_T).items():
            _poly(g, p, Y if k in on else GHOST)
        dx = x + DIG_W + DIG_GAP // 2 - 3
        g.fillRect(dx, y + DIG_H - DIG_T, DIG_T, DIG_T, Y if i in dots else GHOST)


VAL_X, VAL_Y = 166, 80                       # value area (for the partial redraw)
VAL_W = DIG_N * (DIG_W + DIG_GAP)


# ---------- page -------------------------------------------------------------------------------
def page_static(g):
    g.fillScreen(BG)
    # status bar
    mtext(g, "14:32", 8, 5, WH)
    trefoil(g, 140, 12, 7, Y)
    mtext(g, "RC 92%", 152, 5, GR)
    g.drawRect(234, 5, 23, 14, GR)
    g.fillRect(257, 9, 2, 6, GR)
    g.fillRect(236, 7, 15, 10, GN)
    mtext(g, "87%", 312, 5, GR, right=True)
    g.drawLine(0, 24, W, 24, DK)
    # tabs
    for i, t in enumerate(("RATE", "CPS", "DOSE", "SET")):
        x = 8 + i * 60
        tx = x + 28 - (len(t) * 12 - 2) // 2
        if i == 0:
            g.fillRect(x, 29, 56, 20, Y)
            mtext(g, t, tx, 32, BG, bg=Y)
        else:
            g.drawRect(x, 29, 56, 20, YD)
            mtext(g, t, tx, 32, YD)
    mtext(g, "LIVE", 312, 32, GN, right=True)
    # gauge frame
    bx, by, bw, bh, ln = 10, 58, 144, 146, 10
    for cx, cy, sx, sy in ((bx, by, 1, 1), (bx + bw, by, -1, 1),
                           (bx, by + bh, 1, -1), (bx + bw, by + bh, -1, -1)):
        g.fillRect(cx if sx > 0 else cx - ln, cy if sy > 0 else cy - 1, ln, 2, YD)
        g.fillRect(cx if sx > 0 else cx - 1, cy if sy > 0 else cy - ln, 2, ln, YD)
    trefoil(g, RING_CX, RING_CY, 40, Y)
    # labels and secondary values
    mtext(g, "DOSE RATE", 168, 60, GR)
    mtext(g, "uSv/h", 168, 138, GR)
    mtext(g, "STABLE", 312, 138, GR, right=True)
    g.drawLine(168, 158, 312, 158, DK)
    mtext(g, "CPS", 168, 165, GR)
    mtext(g, "5.41", 312, 165, WH, right=True)
    mtext(g, "DOSE 15M", 168, 187, GR)
    mtext(g, "12%", 312, 187, GN, right=True)
    # footer
    g.drawLine(0, 212, W, 212, DK)
    mtext(g, "RC-102-002462", 8, 220, GR)
    mtext(g, "LOG SD", 312, 220, GR, right=True)


def page_full(g, value, frac):
    page_static(g)
    ring(g, frac)
    seg_number(g, value, 314, VAL_Y)


def value_of(p):
    v = 0.12 + 9.0 * p
    return "%.2f" % v


# ---------- tests ----------------------------------------------------------------------------
def make_canvas(w, h):
    try:
        return Lcd.newCanvas(w, h, 16)
    except Exception as e:
        note(False, "canvas", repr(e))
        return None


def free_canvas(c):
    if c is not None:
        try:
            c.delete()
        except Exception:
            pass


def part_static():
    page_full(Lcd, "0.12", 0.1)
    print("static page: look at it / take a photo (5 s)")
    time.sleep_ms(5000)
    note(True, "static", "shown 5 s")


def part_full(name):
    c = make_canvas(W, H)
    g = c if c is not None else Lcd
    frames = 0
    t0 = time.ticks_ms()
    try:
        while time.ticks_diff(time.ticks_ms(), t0) < 5000:
            p = time.ticks_diff(time.ticks_ms(), t0) / 5000
            page_full(g, value_of(p), p)
            if c is not None:
                c.push(0, 0)
            frames += 1
        fps = frames * 1000 / time.ticks_diff(time.ticks_ms(), t0)
        note(True, name, "%s, %.1f frames/s" % ("canvas" if c else "direct", fps))
    except Exception as e:
        note(False, name, repr(e))
    finally:
        free_canvas(c)


def part_partial():
    page_static(Lcd)
    ring(Lcd, 0)
    c = make_canvas(VAL_W, DIG_H)
    frames = 0
    t0 = time.ticks_ms()
    try:
        while time.ticks_diff(time.ticks_ms(), t0) < 5000:
            p = time.ticks_diff(time.ticks_ms(), t0) / 5000
            if c is not None:                  # value off-screen, pushed at once
                c.fillScreen(BG)
                seg_number(c, value_of(p), VAL_W, 0)
                c.push(314 - VAL_W, VAL_Y)
            else:
                seg_number(Lcd, value_of(p), 314, VAL_Y)
            ring(Lcd, p)                       # segments only change colour -> no flicker
            frames += 1
        fps = frames * 1000 / time.ticks_diff(time.ticks_ms(), t0)
        note(True, "partial", "%s, %.1f frames/s" % ("canvas" if c else "direct", fps))
    except Exception as e:
        note(False, "partial", repr(e))
    finally:
        free_canvas(c)


def part_ascii7():
    TEXT_MODE[0] = "ascii7"
    try:
        page_full(Lcd, "0.12", 0.1)
        print("ASCII7 font: look at it / take a photo (4 s)")
        time.sleep_ms(4000)
        part_full("ascii7")
    except Exception as e:
        note(False, "ascii7", repr(e))
    finally:
        TEXT_MODE[0] = "matrix"


def main():
    M5.begin()
    Lcd.setTextSize(1)                        # reset leftovers from earlier tests
    probe_arc()
    for name, fn in (("static", part_static), ("full", lambda: part_full("full")),
                     ("partial", part_partial), ("ascii7", part_ascii7)):
        try:
            fn()
        except Exception as e:
            note(False, name, "crash: %r" % e)
    print("\n===== RZ UI TEST 2 SUMMARY =====")
    for ln in results:
        print(ln)
    print("================================")


main()
