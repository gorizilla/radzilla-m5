# pages_rect.py – page layout for rectangular 320x240 displays (Core2).
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# Pure presentation: draws a view model (see app.py, class View) and knows
# nothing about BLE, alarms or hardware. A round display (StopWatch) gets
# its own pages_round.py with the same draw(g, v) interface.
from radzilla.ui import gfx
from radzilla.ui.gfx import (BG, WHITE, GREY, DARK, YELLOW, YELLOW_DIM, GREEN, BLUE)

W, H = 320, 240
TABS = ("RATE", "CPS", "DOSE", "SET")
TAB_X, TAB_STEP, TAB_W, TAB_Y, TAB_H = 8, 56, 52, 29, 20
GAUGE_CX, GAUGE_CY = 82, 131


def _chrome(g, v):
    """Status bar, tabs, state label and footer (same on all pages)."""
    # status bar
    gfx.text(g, v.time_str, 8, 5, WHITE)
    gfx.trefoil(g, 140, 12, 7, YELLOW)
    gfx.text(g, v.rc_txt, 152, 5, GREY)
    g.drawRect(234, 5, 23, 14, GREY)                    # device battery
    g.fillRect(257, 9, 2, 6, GREY)
    if v.batt_pct is not None:
        fw = max(1, min(19, int(19 * v.batt_pct / 100 + 0.5)))
        g.fillRect(236, 7, fw, 10, v.batt_col)
        gfx.text(g, "%d%%" % v.batt_pct, 312, 5, GREY, align="right")
    else:
        gfx.text(g, "--", 312, 5, GREY, align="right")
    g.drawLine(0, 24, W, 24, DARK)
    # tabs
    for i, t in enumerate(TABS):
        x = TAB_X + i * TAB_STEP
        tx = x + TAB_W // 2
        if i == v.page:
            g.fillRect(x, TAB_Y, TAB_W, TAB_H, YELLOW)
            gfx.text(g, t, tx, TAB_Y + 3, BG, align="center")
        else:
            g.drawRect(x, TAB_Y, TAB_W, TAB_H, YELLOW_DIM)
            gfx.text(g, t, tx, TAB_Y + 3, YELLOW_DIM, align="center")
    gfx.text(g, v.state_txt, 312, TAB_Y + 3, v.state_col, align="right")
    # footer
    g.drawLine(0, 212, W, 212, DARK)
    gfx.text(g, v.footer_l[:13], 8, 220, v.footer_l_col)
    gfx.text(g, v.footer_r, 312, 220, v.footer_r_col, align="right")


def _rate_page(g, v):
    """RATE (µSv/h large) and CPS (CPS large) share one layout."""
    gfx.brackets(g, 10, 58, 144, 146, YELLOW_DIM)
    gfx.seg_ring(g, GAUGE_CX, GAUGE_CY, 52, 62, v.ring_frac, v.main_col)
    gfx.trefoil(g, GAUGE_CX, GAUGE_CY, 40, v.main_col)
    gfx.text(g, v.big_label, 168, 60, GREY)
    gfx.seg_number(g, v.big, 314, 80, v.main_col)
    gfx.text(g, v.big_unit, 168, 138, GREY)
    gfx.text(g, v.trend, 312, 138, GREY, align="right")
    g.drawLine(168, 158, 312, 158, DARK)
    gfx.text(g, v.sub_label, 168, 165, GREY)
    gfx.text(g, v.sub_val, 312, 165, v.sub_col, align="right")
    gfx.text(g, "DOSE 15M", 168, 187, GREY)
    gfx.text(g, v.d_pct_txt + "%", 312, 187, v.d_col, align="right")


def _dose_page(g, v):
    cx, cy = 160, GAUGE_CY
    gfx.brackets(g, cx - 74, 58, 148, 146, YELLOW_DIM)
    gfx.seg_ring(g, cx, cy, 56, 66, v.d_frac, v.d_col)
    gfx.seg_ring(g, cx, cy, 42, 50, v.e_frac, BLUE, n=24)
    gfx.trefoil(g, cx, cy, 28, v.d_col)
    small = dict(w=16, h=34, t=5, gap=4, ndig=3, dots=False)
    # left: 15-min window
    gfx.text(g, "%d MIN" % v.window_min, 8, 62, GREY)
    gfx.seg_number(g, v.d_pct_txt, 70, 86, v.d_col, **small)
    gfx.text(g, "%", 72, 106, v.d_col)
    gfx.text(g, v.d_usv, 8, 134, WHITE)
    gfx.text(g, "uSv", 8, 152, GREY)
    gfx.text(g, "OF " + v.d_lim, 8, 178, GREY)
    # right: extra dose today
    gfx.text(g, "TODAY", 312, 62, GREY, align="right")
    gfx.seg_number(g, v.e_pct_txt, 298, 86, BLUE, **small)
    gfx.text(g, "%", 312, 106, BLUE, align="right")
    gfx.text(g, v.e_usv, 312, 134, WHITE, align="right")
    gfx.text(g, "uSv", 312, 152, GREY, align="right")
    gfx.text(g, "OF " + v.e_lim, 312, 178, GREY, align="right")


def _set_page(g, v):
    gfx.brackets(g, 10, 58, 300, 146, YELLOW_DIM)
    gfx.text(g, "SETTINGS", 160, 80, YELLOW, align="center")
    gfx.text(g, "COMING IN STAGE 3", 160, 110, GREY, align="center")
    gfx.text(g, "WIFI  BT  LIGHT  MENU", 160, 134, GREY, align="center")
    gfx.text(g, "RADZILLA M5 " + v.version.upper(), 160, 172, GREY, align="center")


def _overlay(g, lines):
    """Box in the middle for device info and short notices."""
    lines = [s[:22] for s in lines[:4]]
    bw = max(gfx.text_width(s) for s in lines) + 32
    bh = len(lines) * 22 + 22
    x, y = (W - bw) // 2, 118 - bh // 2
    g.fillRect(x, y, bw, bh, BG)
    g.drawRect(x, y, bw, bh, YELLOW)
    gfx.brackets(g, x - 5, y - 5, bw + 10, bh + 10, YELLOW)
    for i, s in enumerate(lines):
        gfx.text(g, s, W // 2, y + 13 + i * 22, YELLOW if i == 0 else WHITE, align="center")


def draw(g, v):
    g.fillScreen(BG)
    _chrome(g, v)
    if v.page == 2:
        _dose_page(g, v)
    elif v.page == 3:
        _set_page(g, v)
    else:
        _rate_page(g, v)
    if v.overlay:
        _overlay(g, v.overlay)
