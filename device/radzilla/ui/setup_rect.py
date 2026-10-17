# setup_rect.py – full-screen dialogs of the SET page for 320x240 displays:
# network list, on-screen keyboard, phone setup screen, short messages.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# The dialogs draw directly and wait for taps through get_tap(timeout_ms),
# an async function from app.py returning (x, y) or None (timeout).
import time

from radzilla.ui import gfx
from radzilla.ui.gfx import BG, WHITE, GREY, DARK, YELLOW, YELLOW_DIM, GREEN, RED

W, H = 320, 240
KEY_W, KEY_H, KEY_Y0, KEY_DY = 30, 32, 60, 35
ROWS = {
    "abc": ("1234567890", "qwertyuiop", "asdfghjkl@", "zxcvbnm.-_"),
    "ABC": ("1234567890", "QWERTYUIOP", "ASDFGHJKL@", "ZXCVBNM.-_"),
    "#+=": ("!\"#$%&'()*", "+,/:;<=>?[", "\\]^`{|}~ ", "          "),
}
# bottom row: (action, label, x, w)
SPECIAL = (("shift", "ABC", 0, 46), ("sym", "#+=", 48, 46), ("space", "SPACE", 96, 90),
           ("del", "DEL", 188, 46), ("ok", "OK", 236, 42), ("cancel", "X", 280, 40))
SPECIAL_Y = KEY_Y0 + 4 * KEY_DY


def _button(g, x, y, w, h, label, col, fill=None):
    if fill is not None:
        g.fillRect(x, y, w, h, fill)
    g.drawRect(x, y, w, h, col)
    gfx.text(g, label, x + w // 2, y + (h - 14) // 2, col, align="center")


def message(g, lines, col=YELLOW):
    """Simple full-screen message (e.g. 'SCANNING ...')."""
    g.fillScreen(BG)
    y = 120 - len(lines) * 12
    for i, s in enumerate(lines):
        gfx.text(g, s, W // 2, y + i * 24, col if i == 0 else WHITE, align="center")


# ---------- network list ------------------------------------------------------------------
async def choose_network(g, nets, get_tap):
    """nets: list of (ssid, rssi) strongest first. Returns ssid or None."""
    nets = nets[:6]
    g.fillScreen(BG)
    gfx.text(g, "CHOOSE WIFI", 8, 6, YELLOW)
    g.drawLine(0, 24, W, 24, DARK)
    if not nets:
        gfx.text(g, "NO NETWORK FOUND", W // 2, 100, RED, align="center")
    for i, (ssid, rssi) in enumerate(nets):
        y = 30 + i * 29
        g.drawRect(4, y, 312, 26, YELLOW_DIM)
        gfx.text(g, ssid[:20], 12, y + 6, WHITE)
        bars = 4 if rssi > -55 else 3 if rssi > -67 else 2 if rssi > -78 else 1
        for b in range(4):
            bh = 4 + b * 4
            g.fillRect(270 + b * 9, y + 21 - bh, 6, bh, GREEN if b < bars else DARK)
    _button(g, 110, 206, 100, 28, "CANCEL", YELLOW)
    while True:
        tap = await get_tap(120000)
        if tap is None:
            return None
        x, y = tap
        if 110 <= x < 210 and y >= 200:
            return None
        i = (y - 30) // 29
        if 0 <= i < len(nets) and y >= 30:
            return nets[i][0]


# ---------- keyboard ---------------------------------------------------------------------------
def _draw_keys(g, mode):
    g.fillRect(0, KEY_Y0 - 2, W, H - KEY_Y0 + 2, BG)
    for r, row in enumerate(ROWS[mode]):
        y = KEY_Y0 + r * KEY_DY
        for c, ch in enumerate(row):
            if ch == " " and mode == "#+=":
                continue
            x = c * 32 + 1
            g.fillRect(x, y, KEY_W, KEY_H, DARK)
            gfx.text(g, ch, x + KEY_W // 2, y + 9, WHITE, align="center")
    for act, label, x, w in SPECIAL:
        active = (act == "shift" and mode == "ABC") or (act == "sym" and mode == "#+=")
        col = BG if active else YELLOW
        _button(g, x, SPECIAL_Y, w, KEY_H, label, col, fill=YELLOW if active else BG)


def _draw_field(g, text, hidden):
    g.fillRect(4, 26, 312, 28, BG)
    g.drawRect(4, 26, 312, 28, YELLOW)
    shown = ("*" * len(text)) if hidden else text
    shown = shown[-24:]
    gfx.text(g, shown + "_", 10, 33, WHITE)


def _key_at(mode, x, y):
    if y >= SPECIAL_Y:
        for act, label, kx, w in SPECIAL:
            if kx <= x < kx + w:
                return act
        return None
    r = (y - KEY_Y0) // KEY_DY
    c = x // 32
    if 0 <= r < 4 and 0 <= c < 10 and y >= KEY_Y0:
        ch = ROWS[mode][r][c]
        if mode == "#+=" and ch == " ":
            return None
        return ch
    return None


async def keyboard(g, title, get_tap, initial="", hidden=False):
    """On-screen keyboard. Returns the text (OK) or None (X / timeout)."""
    text = initial
    mode = "abc"
    g.fillScreen(BG)
    gfx.text(g, title[:26], 6, 6, YELLOW)
    _draw_field(g, text, hidden)
    _draw_keys(g, mode)
    while True:
        tap = await get_tap(180000)
        if tap is None:
            return None
        k = _key_at(mode, tap[0], tap[1])
        if k is None:
            continue
        if k == "cancel":
            return None
        if k == "ok":
            return text
        if k == "del":
            text = text[:-1]
        elif k == "space":
            text += " "
        elif k == "shift":
            mode = "abc" if mode == "ABC" else "ABC"
            _draw_keys(g, mode)
            continue
        elif k == "sym":
            mode = "abc" if mode == "#+=" else "#+="
            _draw_keys(g, mode)
            continue
        elif len(text) < 64:
            text += k
            if mode == "ABC":                  # one capital letter, then lower case
                mode = "abc"
                _draw_keys(g, mode)
        _draw_field(g, text, hidden)


# ---------- phone setup ---------------------------------------------------------------------
def phone_screen(g, ap_name, ap_pw, ip, secs_left):
    g.fillScreen(BG)
    gfx.text(g, "PHONE SETUP", 8, 6, YELLOW)
    g.drawLine(0, 24, W, 24, DARK)
    gfx.text(g, "1 CONNECT PHONE TO WIFI", 10, 36, GREY)
    gfx.text(g, ap_name, 30, 56, WHITE)
    gfx.text(g, "PASSWORD", 10, 82, GREY)
    gfx.text(g, ap_pw, 30, 100, GREEN, sc=3)
    gfx.text(g, "2 OPEN IN THE BROWSER", 10, 132, GREY)
    gfx.text(g, "http://" + ip, 30, 152, WHITE)
    _button(g, 110, 206, 100, 28, "CANCEL", YELLOW)
    phone_countdown(g, secs_left)


def phone_countdown(g, secs_left):
    g.fillRect(10, 180, 300, 14, BG)
    gfx.text(g, "CLOSES IN %d:%02d" % (secs_left // 60, secs_left % 60), W // 2, 180, GREY,
             align="center")


def phone_cancel_hit(tap):
    return tap is not None and 110 <= tap[0] < 210 and tap[1] >= 200
