# gfx.py – drawing helpers for design A1: 5x7 dot-matrix font, 7-segment
# digits with dim "ghost" segments, ring segments and the radiation symbol.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# Works on any graphics object with fillRect, fillTriangle, fillCircle and
# (optionally) fillArc – the UIFlow Lcd or a canvas. All fonts and symbols are
# drawn by RadZilla itself, so they scale to other displays.
import math

# colours (24-bit RGB)
BG = 0x000000
WHITE = 0xF0F0F0
GREY = 0x8C8C8C          # labels
DARK = 0x262626          # empty ring segments, lines
GHOST = 0x181300         # unlit 7-segment segments
YELLOW = 0xFFC800        # theme colour (tabs) / HIGH
YELLOW_DIM = 0x6E5600    # inactive tabs, corner brackets
GREEN = 0x28DC5A         # normal
ORANGE = 0xFF8C00        # dose ring warning stage
RED = 0xFF3030           # DANGER / DOSE
BLUE = 0x3C96FF          # extra dose today

# ---------- 5x7 dot-matrix font -------------------------------------------------------
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
    "J": ("  ###", "   # ", "   # ", "   # ", "   # ", "#  # ", " ##  "),
    "K": ("#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"),
    "L": ("#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"),
    "M": ("#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"),
    "N": ("#   #", "#   #", "##  #", "# # #", "#  ##", "#   #", "#   #"),
    "O": (" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "),
    "P": ("#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "),
    "Q": (" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"),
    "R": ("#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"),
    "S": (" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "),
    "T": ("#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "),
    "U": ("#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "),
    "V": ("#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "),
    "W": ("#   #", "#   #", "#   #", "# # #", "# # #", "# # #", " # # "),
    "X": ("#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"),
    "Y": ("#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "),
    "Z": ("#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"),
    "u": ("     ", "     ", "#   #", "#   #", "#   #", "#  ##", " ## #"),
    "v": ("     ", "     ", "#   #", "#   #", "#   #", " # # ", "  #  "),
    "h": ("#    ", "#    ", "# ## ", "##  #", "#   #", "#   #", "#   #"),
    "k": ("#    ", "#    ", "#  # ", "# #  ", "##   ", "# #  ", "#  # "),
    "m": ("     ", "     ", "## # ", "# # #", "# # #", "#   #", "#   #"),
    ".": ("     ", "     ", "     ", "     ", "     ", " ##  ", " ##  "),
    ",": ("     ", "     ", "     ", "     ", " ##  ", "  #  ", " #   "),
    ":": ("     ", " ##  ", " ##  ", "     ", " ##  ", " ##  ", "     "),
    "%": ("##   ", "##  #", "   # ", "  #  ", " #   ", "#  ##", "   ##"),
    "/": ("     ", "    #", "   # ", "  #  ", " #   ", "#    ", "     "),
    "-": ("     ", "     ", "     ", "#####", "     ", "     ", "     "),
    "+": ("     ", "  #  ", "  #  ", "#####", "  #  ", "  #  ", "     "),
    "!": ("  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "     ", "  #  "),
    "?": (" ### ", "#   #", "    #", "   # ", "  #  ", "     ", "  #  "),
    " ": ("     ",) * 7,
}


def _runs(rows):
    """Glyph -> list of horizontal runs (x, y, length): few fillRect calls."""
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


_GLYPH = {k: _runs(v) for k, v in _F57.items()}
del _F57


def text_width(s, sc=2):
    return len(s) * 6 * sc - sc if s else 0


def text(g, s, x, y, col, sc=2, align="left"):
    """Dot-matrix text. sc = pixel size (2 -> 10x14 px per character).
    Lower-case letters without a glyph are drawn in upper case."""
    w = text_width(s, sc)
    if align == "right":
        x -= w
    elif align == "center":
        x -= w // 2
    for ch in s:
        runs = _GLYPH.get(ch)
        if runs is None:
            runs = _GLYPH.get(ch.upper(), _GLYPH["?"])
        for rx, ry, n in runs:
            g.fillRect(x + rx * sc, y + ry * sc, n * sc, sc, col)
        x += 6 * sc
    return w


# ---------- arcs ----------------------------------------------------------------------------
_HAS_ARC = [True]


def arc(g, cx, cy, r0, r1, a0, a1, col):
    """Filled ring sector, angles in degrees (0 = right, clockwise)."""
    if _HAS_ARC[0]:
        try:
            g.fillArc(int(cx), int(cy), int(r0), int(r1), int(a0), int(a1), col)
            return
        except Exception as e:
            print("gfx: fillArc not usable (%r) - using triangles" % e)
            _HAS_ARC[0] = False
    steps = max(2, int((a1 - a0) / 6))
    for i in range(steps):
        t0 = math.radians(a0 + (a1 - a0) * i / steps)
        t1 = math.radians(a0 + (a1 - a0) * (i + 1) / steps)
        c0, s0, c1, s1 = math.cos(t0), math.sin(t0), math.cos(t1), math.sin(t1)
        x0, y0 = int(cx + r1 * c0), int(cy + r1 * s0)
        x1, y1 = int(cx + r1 * c1), int(cy + r1 * s1)
        x2, y2 = int(cx + r0 * c1), int(cy + r0 * s1)
        x3, y3 = int(cx + r0 * c0), int(cy + r0 * s0)
        g.fillTriangle(x0, y0, x1, y1, x2, y2, col)
        g.fillTriangle(x0, y0, x2, y2, x3, y3, col)


def trefoil(g, cx, cy, r, col):
    """Radiation symbol: three 60° blades (one down) and a centre dot."""
    for a in (90, 210, 330):
        arc(g, cx, cy, int(r * 0.32), r, a - 30, a + 30, col)
    g.fillCircle(cx, cy, max(2, int(r * 0.18)), col)


def seg_ring(g, cx, cy, r0, r1, frac, col, n=30, empty=DARK):
    """Ring of n segments, the first frac (0..1) of them filled, from the top."""
    filled = int(min(1.0, max(0.0, frac)) * n + 0.5)
    step = 360 / n
    for i in range(n):
        a0 = -90 + i * step + 2
        arc(g, cx, cy, r0, r1, a0, a0 + step - 4, col if i < filled else empty)


def brackets(g, x, y, w, h, col, ln=10):
    """Corner brackets around a box."""
    for cx, cy, sx, sy in ((x, y, 1, 1), (x + w, y, -1, 1),
                           (x, y + h, 1, -1), (x + w, y + h, -1, -1)):
        g.fillRect(cx if sx > 0 else cx - ln, cy if sy > 0 else cy - 1, ln, 2, col)
        g.fillRect(cx if sx > 0 else cx - 1, cy if sy > 0 else cy - ln, 2, ln, col)


# ---------- trend arrow ------------------------------------------------------------------------
def arrow(g, x, y, s, dirn, col):
    """Arrow in an s x s box: 0 = right (stable), 1 = up, -1 = down."""
    t = s // 4
    h = s // 2
    if dirn == 0:
        g.fillRect(x, y + h - t // 2, s - h, t, col)
        g.fillTriangle(x + h - 1, y + 2, x + s, y + h, x + h - 1, y + s - 2, col)
    elif dirn > 0:
        g.fillRect(x + h - t // 2, y + h - 1, t, s - h + 1, col)
        g.fillTriangle(x + 2, y + h, x + h, y, x + s - 2, y + h, col)
    else:
        g.fillRect(x + h - t // 2, y, t, h + 2, col)
        g.fillTriangle(x + 2, y + h, x + h, y + s, x + s - 2, y + h, col)


# ---------- 7-segment digits -------------------------------------------------------------------
_SEG = {"0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg", "5": "acdfg",
        "6": "acdefg", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", " ": ""}


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

    return (("a", hor(y + ht)), ("g", hor(y + m)), ("d", hor(y + h - ht)),
            ("f", ver(x + ht, y + ht, y + m)), ("e", ver(x + ht, y + m, y + h - ht)),
            ("b", ver(x + w - ht, y + ht, y + m)), ("c", ver(x + w - ht, y + m, y + h - ht)))


def _poly(g, p, col):
    x0, y0 = p[0]
    for i in range(1, len(p) - 1):
        g.fillTriangle(x0, y0, p[i][0], p[i][1], p[i + 1][0], p[i + 1][1], col)


def seg_number(g, s, x_right, y, col, w=26, h=48, t=6, gap=8, ndig=4, dots=True):
    """Right-aligned 7-segment number, e.g. "0.12" or "--". Unused digit
    positions show dim ghost segments like a real LCD."""
    digits, dps = [], []
    for ch in s:
        if ch == ".":
            dps.append(len(digits) - 1)
        else:
            digits.append(ch)
    digits = digits[-ndig:]
    pad = ndig - len(digits)
    digits = [" "] * pad + digits
    dps = [i + pad for i in dps]
    x0 = x_right - ndig * (w + gap)
    for i in range(ndig):
        x = x0 + i * (w + gap)
        on = _SEG.get(digits[i], "")
        for k, p in _seg_polys(x, y, w, h, t):
            _poly(g, p, col if k in on else GHOST)
        if dots:
            dx = x + w + gap // 2 - t // 2
            g.fillRect(dx, y + h - t, t, t, col if i in dps else GHOST)
