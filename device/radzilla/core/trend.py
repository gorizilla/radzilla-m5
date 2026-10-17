# trend.py – rising / falling / stable from the last readings.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# Average of the last TREND_WINDOW_S seconds vs. the window before.
import time

USV, CPS = 1, 2                     # index into the history tuples


def add(S, C, usv, cps):
    now = time.ticks_ms()
    S.hist.append((now, usv, cps))
    keep = 2 * C.TREND_WINDOW_S * 1000 + 2000
    while S.hist and time.ticks_diff(now, S.hist[0][0]) > keep:
        S.hist.pop(0)


def get(S, C, idx):
    """+1 rising, -1 falling, 0 stable, None = not enough data."""
    if not S.hist:
        return None
    min_abs = C.TREND_MIN_USV if idx == USV else C.TREND_MIN_CPS
    now = time.ticks_ms()
    w = C.TREND_WINDOW_S * 1000
    if time.ticks_diff(now, S.hist[0][0]) < 2 * w - 1500:
        return None
    new = [h[idx] for h in S.hist if time.ticks_diff(now, h[0]) <= w]
    old = [h[idx] for h in S.hist if w < time.ticks_diff(now, h[0]) <= 2 * w]
    if not new or not old:
        return None
    a_new = sum(new) / len(new)
    a_old = sum(old) / len(old)
    diff = a_new - a_old
    if abs(diff) >= max(a_old * C.TREND_PCT, min_abs):
        return 1 if diff > 0 else -1
    return 0


def text(t):
    return {None: "-", 0: "STABLE", 1: "RISING", -1: "FALLING"}[t]
