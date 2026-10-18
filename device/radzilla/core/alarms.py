# alarms.py – HIGH / DANGER / DOSE alarms, Geiger pre-warning, RadiaCode signal.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
#   1 HIGH    dose rate >= LEVEL1_USV                       yellow
#   2 DANGER  dose rate >= LEVEL2_USV                       red
#   3 DOSE    dose within DOSE_WINDOW_MIN >= DOSE_LIMIT_USV red
# No acknowledgement: HIGH beeps ALARM1_MAX_REPEAT times per alarm event,
# DANGER and DOSE play their siren once. An alarm ends below threshold x (1 - HYSTERESIS).
# Sound, LEDs and vibration are played by fx.py.
import asyncio
import math
import time

from radzilla import fx as fx_mod
from radzilla.core import dose


def new_level(C, usv, cur):
    """Alarm level with hysteresis."""
    h = 1 - C.HYSTERESIS
    if usv >= C.LEVEL2_USV or (cur == 2 and usv >= C.LEVEL2_USV * h):
        return 2
    if usv >= C.LEVEL1_USV or (cur >= 1 and usv >= C.LEVEL1_USV * h):
        return 1
    return 0


def update_level(S, C):
    """Returns the new level if an alarm started or escalated, else None."""
    new = new_level(C, S.usv, S.level) if S.usv is not None else 0
    if new == S.level:
        return None
    started = new > S.level
    S.count = 0
    S.last_beep = None
    S.level = new
    S.dirty = True
    if started:
        queue_rc_signal(S, C, new)
        return new
    return None


# ---------- heartbeat colour -------------------------------------------------------
def _mix(a, b, k):
    k = max(0.0, min(1.0, k))
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def _logk(v, a, b):
    return math.log(v / a) / math.log(b / a)


def heart_color(C, usv, level, dose_active):
    """Colour of the heartbeat run for the dose rate (logarithmic)."""
    if level == 2 or dose_active:
        return C.LED_RED
    if usv is None or usv <= C.HB_GREEN_USV:
        return C.LED_GREEN
    if level == 1 or usv >= C.LEVEL1_USV:
        k = _logk(max(usv, C.LEVEL1_USV), C.LEVEL1_USV, C.LEVEL2_USV)
        if k < 0.6:
            return _mix(C.LED_YELLOW, C.LED_ORANGE, k / 0.6)
        return _mix(C.LED_ORANGE, C.HB_NEAR_RED, (k - 0.6) / 0.4)
    if usv <= C.HB_WARN_USV:
        return _mix(C.LED_GREEN, C.HB_LIME, _logk(usv, C.HB_GREEN_USV, C.HB_WARN_USV))
    return _mix(C.HB_LIME, C.HB_PRE, _logk(usv, C.HB_WARN_USV, C.LEVEL1_USV * 0.995))


# ---------- RadiaCode signal ------------------------------------------------------
def queue_rc_signal(S, C, level):
    if not C.RC_SIGNAL_ON:
        return
    n = C.RC_SIGNAL_DANGER_COUNT if level == 2 else C.RC_SIGNAL_HIGH_COUNT
    S.rc_sig_pending = max(0, int(n))
    S.rc_sig_next = time.ticks_ms()


async def play_rc_signal(S, C, rc):
    """Called from the read loop (one BLE command at a time)."""
    if S.rc_sig_pending <= 0 or time.ticks_diff(time.ticks_ms(), S.rc_sig_next) < 0:
        return
    S.rc_sig_pending -= 1
    S.rc_sig_next = time.ticks_add(time.ticks_ms(), C.RC_SIGNAL_GAP_MS)
    try:
        if not await rc.play_signal():
            print("RadiaCode: signal rejected")
            S.rc_sig_pending = 0
    except Exception as e:
        print("RadiaCode signal:", repr(e))
        S.rc_sig_pending = 0


async def task(fx, S, C):
    """Dose window upkeep and the alarm effects (sound, LEDs, vibration):
    HIGH beep + yellow run every ALARM1_INTERVAL_MS (max. ALARM1_MAX_REPEAT),
    DANGER siren once per event, DOSE siren once per event, Geiger pre-warning
    at RING_WARN_PCT. Heartbeat run in the colour of the dose rate: every
    HEARTBEAT_S normally, every HEARTBEAT_ALARM_S during an alarm once its
    signals are over."""
    last_heart = time.ticks_ms()
    danger_done = False
    while True:
        await asyncio.sleep_ms(50)
        now = time.ticks_ms()
        fresh = S.fresh(C.RC_STALE_MS)
        dose.trim(S, C, now)                  # the dose decays also without data
        if dose.update_alarm(S, C) and C.ALARM3_ON and S.level < 2 and fresh:
            fx.dose()
            last_heart = now
            S.wake = True
        if C.GEIGER_ON:
            p = dose.pct(S, C)
            if S.geiger_armed and C.RING_WARN_PCT <= p < 100:
                S.geiger_armed = False
                if not fx.busy(fx_mod.P_GEIGER):
                    fx.geiger()
            elif not S.geiger_armed and p < C.RING_WARN_PCT * (1 - C.HYSTERESIS):
                S.geiger_armed = True

        lvl = S.level
        if lvl < 2:
            danger_done = False
        signals_over = True                   # alarm beeps / sirens finished
        if lvl == 2 and fresh and C.ALARM2_ON and not danger_done:
            danger_done = True
            fx.danger()
            last_heart = now
        elif lvl == 1 and fresh and C.ALARM1_ON:
            more = not (C.ALARM1_MAX_REPEAT and S.count >= C.ALARM1_MAX_REPEAT)
            if more and not fx.busy(fx_mod.P_HIGH) and \
                    (S.last_beep is None or time.ticks_diff(now, S.last_beep) >= C.ALARM1_INTERVAL_MS):
                S.last_beep = now
                S.count += 1
                fx.high()
                last_heart = now
            if more:
                signals_over = False
        alarm = lvl > 0 or S.dose_active
        if fresh and S.connected and signals_over and not fx.busy(fx_mod.P_GEIGER):
            iv = C.HEARTBEAT_ALARM_S if alarm else C.HEARTBEAT_S
            if time.ticks_diff(now, last_heart) >= iv * 1000:
                last_heart = now
                if C.HEARTBEAT_WHEN_DIM or not S.dimmed:
                    fx.heartbeat(heart_color(C, S.usv, lvl, S.dose_active))
