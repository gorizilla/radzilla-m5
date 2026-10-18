# dose.py – dose of the last DOSE_WINDOW_MIN minutes and extra dose today.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# Counting starts with the connection; gaps without data count as 0.
import time


def add(S, C, usv, now):
    """Add the dose of one reading. The time step is limited to RC_STALE_MS,
    so gaps (disconnect) count as 0."""
    if S.last_rd_ms is None:
        dt = C.RC_POLL_MS
    else:
        dt = min(time.ticks_diff(now, S.last_rd_ms), C.RC_STALE_MS)
    S.last_rd_ms = now
    inc = usv * dt / 3_600_000                  # µSv/h x ms -> µSv
    S.dose_hist.append((now, inc))
    S.dose_total += inc
    S.extra_total += max(0.0, usv - C.BACKGROUND_USV) * dt / 3_600_000
    S.year_usv += inc
    trim(S, C, now)


def trim(S, C, now):
    """Remove readings older than the window from the running sum."""
    w = C.DOSE_WINDOW_MIN * 60_000
    while S.dose_hist and time.ticks_diff(now, S.dose_hist[0][0]) > w:
        S.dose_total -= S.dose_hist.pop(0)[1]
    if not S.dose_hist or S.dose_total < 0:
        S.dose_total = 0.0


def pct(S, C):
    return S.dose_total / C.DOSE_LIMIT_USV * 100 if C.DOSE_LIMIT_USV else 0


def extra_pct(S, C):
    return S.extra_total / C.DAILY_BUDGET_USV * 100 if C.DAILY_BUDGET_USV else 0


def update_alarm(S, C):
    """Dose alarm with hysteresis. Returns True when it has just started."""
    if not C.DOSE_ON:
        new = False
    else:
        lim = C.DOSE_LIMIT_USV
        new = S.dose_total >= lim or \
            (S.dose_active and S.dose_total >= lim * (1 - C.HYSTERESIS))
    if new == S.dose_active:
        return False
    S.dose_active = new
    S.dirty = True
    return new


def stage(S, C):
    """Colour stage of the 15-min ring: 0 green, 1 yellow, 2 orange, 3 red."""
    p = pct(S, C)
    if p >= 100:
        return 3
    if p >= C.RING_WARN_PCT:
        return 2
    if p >= C.RING_FAIR_PCT:
        return 1
    return 0
