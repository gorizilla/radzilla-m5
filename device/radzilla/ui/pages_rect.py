# pages_rect.py – page layout for rectangular 320x240 displays (Core2).
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# Pure presentation: draws a view model (see app.py, class View) and knows
# nothing about BLE, alarms or hardware. A round display (StopWatch) gets
# its own pages_round.py with the same draw(g, v) / invalidate() interface.
#
# Drawing is done directly on the display (no off-screen canvas: on the
# Core2 a pushed canvas does not reliably reach the display, especially
# with the microSD card on the shared bus – see tools/rz_sd_test2.py).
# To avoid flicker only what changed is redrawn:
#   * page change / overlay end -> whole page once
#   * 7-segment digits, ring, symbol -> painted over completely (no clearing)
#   * small texts -> their field is cleared, then written again
from radzilla.ui import gfx
from radzilla.ui.gfx import (BG, WHITE, GREY, DARK, YELLOW, YELLOW_DIM, BLUE, GREEN, ORANGE)

W, H = 320, 240
TABS = ("RATE", "CPS", "DOSE", "SET")
TAB_X, TAB_STEP, TAB_W, TAB_Y, TAB_H = 8, 56, 52, 29, 20
GAUGE_CX, GAUGE_CY = 82, 131
DOSE_CX = 160
SMALL = dict(w=16, h=34, t=5, gap=4, ndig=3, dots=False)
BIG_RIGHT = 286                         # big value right edge, trend arrow behind it
ARROW_X, ARROW_Y, ARROW_S = 290, 92, 24
TREND_COL = {0: GREY, 1: ORANGE, -1: GREEN}   # stable / rising / falling

_prev = {}              # last drawn value per field
_page = [None]          # page currently on screen
_overlay = [None]       # overlay currently on screen


def invalidate():
    """Force a complete redraw with the next draw()."""
    _page[0] = None


def _changed(key, val):
    if _prev.get(key, _changed) != val:
        _prev[key] = val
        return True
    return False


def _clear(g, x, y, w, h=14):
    g.fillRect(x, y, w, h, BG)


# ---------- static parts (drawn once per page) ---------------------------------------
def _static_chrome(g, v):
    gfx.trefoil(g, 140, 12, 7, YELLOW)
    g.drawRect(234, 5, 23, 14, GREY)                    # device battery outline
    g.fillRect(257, 9, 2, 6, GREY)
    g.drawLine(0, 24, W, 24, DARK)
    for i, t in enumerate(TABS):
        x = TAB_X + i * TAB_STEP
        tx = x + TAB_W // 2
        if i == v.page:
            g.fillRect(x, TAB_Y, TAB_W, TAB_H, YELLOW)
            gfx.text(g, t, tx, TAB_Y + 3, BG, align="center")
        else:
            g.drawRect(x, TAB_Y, TAB_W, TAB_H, YELLOW_DIM)
            gfx.text(g, t, tx, TAB_Y + 3, YELLOW_DIM, align="center")
    g.drawLine(0, 212, W, 212, DARK)


def _static_rate(g, v):
    gfx.brackets(g, 10, 58, 144, 146, YELLOW_DIM)
    gfx.text(g, v.big_label, 168, 60, GREY)
    g.drawLine(168, 158, 312, 158, DARK)
    gfx.text(g, "DOSE 15M", 168, 187, GREY)


def _static_dose(g, v):
    gfx.brackets(g, DOSE_CX - 74, 58, 148, 146, YELLOW_DIM)
    gfx.text(g, "%d MIN" % v.window_min, 8, 62, GREY)
    gfx.text(g, "uSv", 8, 152, GREY)
    gfx.text(g, "OF " + v.d_lim, 8, 178, GREY)
    gfx.text(g, "TODAY", 312, 62, GREY, align="right")
    gfx.text(g, "uSv", 312, 152, GREY, align="right")
    gfx.text(g, "OF " + v.e_lim, 312, 178, GREY, align="right")


# SET page: tap targets (name -> x, y, w, h), used by app.py for hit tests
SET_BUTTONS = {"add": (16, 172, 92, 26), "phone": (114, 172, 92, 26),
               "sync": (212, 172, 92, 26)}
SET_LABELS = {"add": "+ WIFI", "phone": "PHONE", "sync": "SYNC"}


def set_button_at(x, y):
    for name, (bx, by, bw, bh) in SET_BUTTONS.items():
        if bx <= x < bx + bw and by - 6 <= y < by + bh + 6:
            return name
    return None


def _static_set(g, v):
    gfx.brackets(g, 10, 58, 300, 146, YELLOW_DIM)
    gfx.text(g, "WIFI", 22, 64, GREY)
    gfx.text(g, "TIME", 22, 148, GREY)
    for name, (x, y, w, h) in SET_BUTTONS.items():
        g.drawRect(x, y, w, h, YELLOW)
        gfx.text(g, SET_LABELS[name], x + w // 2, y + 6, YELLOW, align="center")


def _dyn_set(g, v):
    if _changed("wifi", tuple(v.wifi)):
        _clear(g, 22, 82, 284, 60)
        if not v.wifi:
            gfx.text(g, "NO NETWORK SAVED", 22, 84, GREY)
        for i, ssid in enumerate(v.wifi[:3]):
            gfx.text(g, ssid[:23], 22, 84 + i * 19, WHITE)
        if len(v.wifi) > 3:
            gfx.text(g, "+%d" % (len(v.wifi) - 3), 306, 122, GREY, align="right")
    if _changed("wcount", len(v.wifi)):
        _clear(g, 230, 64, 76)
        gfx.text(g, "%d/%d" % (len(v.wifi), v.wifi_max), 306, 64, GREY, align="right")
    if _changed("sync", (v.sync_txt, v.sync_col)):
        _clear(g, 76, 148, 230)
        gfx.text(g, v.sync_txt[:19], 306, 148, v.sync_col, align="right")


# ---------- dynamic parts (redrawn on change) ---------------------------------------------
def _dyn_chrome(g, v):
    if _changed("time", v.time_str):
        _clear(g, 8, 5, 60)
        gfx.text(g, v.time_str, 8, 5, WHITE)
    if _changed("rc", v.rc_txt):
        _clear(g, 152, 5, 80)
        gfx.text(g, v.rc_txt, 152, 5, GREY)
    if _changed("batt", (v.batt_pct, v.batt_col)):
        g.fillRect(236, 7, 19, 10, BG)
        _clear(g, 262, 5, 50)
        if v.batt_pct is not None:
            g.fillRect(236, 7, max(1, min(19, int(19 * v.batt_pct / 100 + 0.5))), 10, v.batt_col)
            gfx.text(g, "%d%%" % v.batt_pct, 312, 5, GREY, align="right")
        else:
            gfx.text(g, "--", 312, 5, GREY, align="right")
    if _changed("state", (v.state_txt, v.state_col)):
        _clear(g, 230, TAB_Y + 3, 82)
        gfx.text(g, v.state_txt, 312, TAB_Y + 3, v.state_col, align="right")
    if _changed("foot_l", (v.footer_l, v.footer_l_col)):
        _clear(g, 8, 220, 156)
        gfx.text(g, v.footer_l[:13], 8, 220, v.footer_l_col)
    if _changed("foot_r", (v.footer_r, v.footer_r_col)):
        _clear(g, 206, 220, 106)
        gfx.text(g, v.footer_r, 312, 220, v.footer_r_col, align="right")


def _dyn_rate(g, v):
    if _changed("ring", (v.ring_frac_seg, v.main_col)):
        gfx.seg_ring(g, GAUGE_CX, GAUGE_CY, 52, 62, v.ring_frac, v.main_col)
    if _changed("sym", v.main_col):
        gfx.trefoil(g, GAUGE_CX, GAUGE_CY, 40, v.main_col)
    if _changed("big", (v.big, v.main_col)):
        gfx.seg_number(g, v.big, BIG_RIGHT, 80, v.main_col, w=22, gap=6)
    if _changed("trend", v.trend):
        g.fillRect(ARROW_X, ARROW_Y, ARROW_S + 1, ARROW_S + 1, BG)
        if v.trend is not None:
            gfx.arrow(g, ARROW_X, ARROW_Y, ARROW_S, v.trend, TREND_COL[v.trend])
    if _changed("unit", v.big_unit):
        _clear(g, 168, 138, 60)
        gfx.text(g, v.big_unit, 168, 138, GREY)
    if _changed("sublabel", v.sub_label):
        _clear(g, 168, 165, 60)
        gfx.text(g, v.sub_label, 168, 165, GREY)
    if _changed("sub", (v.sub_val, v.sub_col)):
        _clear(g, 236, 165, 76)
        gfx.text(g, v.sub_val, 312, 165, v.sub_col, align="right")
    if _changed("dpct", (v.d_pct_txt, v.d_col)):
        _clear(g, 264, 187, 48)
        gfx.text(g, v.d_pct_txt + "%", 312, 187, v.d_col, align="right")


def _dyn_dose(g, v):
    if _changed("dring", (v.d_frac_seg, v.d_col)):
        gfx.seg_ring(g, DOSE_CX, GAUGE_CY, 56, 66, v.d_frac, v.d_col)
    if _changed("dsym", v.d_col):
        gfx.trefoil(g, DOSE_CX, GAUGE_CY, 28, v.d_col)
    if _changed("ering", v.e_frac_seg):
        gfx.seg_ring(g, DOSE_CX, GAUGE_CY, 42, 50, v.e_frac, BLUE, n=24)
    if _changed("dnum", (v.d_pct_txt, v.d_col)):
        gfx.seg_number(g, v.d_pct_txt, 70, 86, v.d_col, **SMALL)
        gfx.text(g, "%", 72, 106, v.d_col)
    if _changed("enum", v.e_pct_txt):
        gfx.seg_number(g, v.e_pct_txt, 298, 86, BLUE, **SMALL)
        gfx.text(g, "%", 312, 106, BLUE, align="right")
    if _changed("dusv", v.d_usv):
        _clear(g, 8, 134, 74)
        gfx.text(g, v.d_usv, 8, 134, WHITE)
    if _changed("eusv", v.e_usv):
        _clear(g, 238, 134, 74)
        gfx.text(g, v.e_usv, 312, 134, WHITE, align="right")


def _overlay_box(g, lines):
    lines = [s[:22] for s in lines[:4]]
    bw = max(gfx.text_width(s) for s in lines) + 32
    bh = len(lines) * 22 + 22
    x, y = (W - bw) // 2, 118 - bh // 2
    g.fillRect(x - 6, y - 6, bw + 12, bh + 12, BG)
    g.drawRect(x, y, bw, bh, YELLOW)
    gfx.brackets(g, x - 5, y - 5, bw + 10, bh + 10, YELLOW)
    for i, s in enumerate(lines):
        gfx.text(g, s, W // 2, y + 13 + i * 22, YELLOW if i == 0 else WHITE, align="center")


# ---------- entry point ----------------------------------------------------------------------
def draw(g, v):
    # number of filled segments decides whether a ring must be redrawn
    v.ring_frac_seg = int(min(1.0, v.ring_frac) * 30 + 0.5)
    v.d_frac_seg = int(min(1.0, v.d_frac) * 30 + 0.5)
    v.e_frac_seg = int(min(1.0, v.e_frac) * 24 + 0.5)

    if v.overlay and _page[0] == v.page:            # info box on top, page frozen
        if v.overlay != _overlay[0]:
            _overlay[0] = v.overlay
            _overlay_box(g, v.overlay)
        return
    if _overlay[0] is not None and not v.overlay:   # overlay just ended
        _overlay[0] = None
        _page[0] = None

    if v.page != _page[0]:                          # whole page once
        _page[0] = v.page
        _prev.clear()
        g.fillScreen(BG)
        _static_chrome(g, v)
        if v.page == 2:
            _static_dose(g, v)
        elif v.page == 3:
            _static_set(g, v)
        else:
            _static_rate(g, v)

    _dyn_chrome(g, v)
    if v.page == 2:
        _dyn_dose(g, v)
    elif v.page in (0, 1):
        _dyn_rate(g, v)
    else:
        _dyn_set(g, v)
    if v.overlay:                                   # page was rebuilt below an overlay
        _overlay[0] = v.overlay
        _overlay_box(g, v.overlay)
