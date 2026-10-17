# alarms.py – HIGH / DANGER / DOSE alarms, Geiger pre-warning, RadiaCode signal.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
#   1 HIGH    dose rate >= LEVEL1_USV                       yellow
#   2 DANGER  dose rate >= LEVEL2_USV                       red
#   3 DOSE    dose within DOSE_WINDOW_MIN >= DOSE_LIMIT_USV red
# No acknowledgement: HIGH / DANGER beep ALARMx_MAX_REPEAT times per alarm
# event, DOSE plays once. An alarm ends below threshold x (1 - HYSTERESIS).
# Stage 1 uses simple tones; sirens, LEDs and vibration follow in stage 2.
#
# The sound functions only need dev.tone(freq_hz, ms) and dev.set_volume(pct).
import asyncio
import math
import random
import time

from radzilla.core import dose

SOUND = asyncio.Lock()              # one sound at a time


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


# ---------- sounds -------------------------------------------------------------------
async def beep(dev, C, freq, n, on_ms, pause_ms, wait=False):
    if SOUND.locked() and not wait:
        return
    async with SOUND:
        dev.set_volume(C.ALARM_VOLUME_PCT)
        for i in range(n):
            dev.tone(freq, on_ms)
            await asyncio.sleep_ms(on_ms + (pause_ms if i < n - 1 else 0))


async def geiger(dev, S, C):
    """Random clicks like a Geiger counter (dose pre-warning)."""
    async with SOUND:
        dev.set_volume(C.ALARM_VOLUME_PCT)
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < C.GEIGER_DURATION_MS:
            if S.dose_active:
                return
            dev.tone(C.GEIGER_FREQ_HZ, C.GEIGER_CLICK_MS)
            gap = -math.log(1.0 - random.random()) / C.GEIGER_RATE_HZ
            await asyncio.sleep_ms(C.GEIGER_CLICK_MS + max(5, int(gap * 1000)))


def _cfg(C, lvl):
    if lvl == 1:
        return (C.ALARM1_ON, C.ALARM1_FREQ_HZ, C.ALARM1_BEEPS, C.ALARM1_BEEP_MS,
                C.ALARM1_PAUSE_MS, C.ALARM1_INTERVAL_MS, C.ALARM1_MAX_REPEAT)
    return (C.ALARM2_ON, C.ALARM2_FREQ_HZ, C.ALARM2_BEEPS, C.ALARM2_BEEP_MS,
            C.ALARM2_PAUSE_MS, C.ALARM2_INTERVAL_MS, C.ALARM2_MAX_REPEAT)


async def task(dev, S, C):
    """Dose window upkeep, DOSE sound, Geiger pre-warning, HIGH/DANGER beeps."""
    while True:
        await asyncio.sleep_ms(50)
        now = time.ticks_ms()
        fresh = S.fresh(C.RC_STALE_MS)
        dose.trim(S, C, now)                  # the dose decays also without data
        if dose.update_alarm(S, C) and C.ALARM3_ON and S.level < 2 and fresh:
            asyncio.create_task(beep(dev, C, C.ALARM3_FREQ_HZ, C.ALARM3_BEEPS,
                                     C.ALARM3_BEEP_MS, C.ALARM3_PAUSE_MS, wait=True))
        if C.GEIGER_ON:
            p = dose.pct(S, C)
            if S.geiger_armed and C.RING_WARN_PCT <= p < 100:
                S.geiger_armed = False
                if not SOUND.locked():
                    asyncio.create_task(geiger(dev, S, C))
            elif not S.geiger_armed and p < C.RING_WARN_PCT * (1 - C.HYSTERESIS):
                S.geiger_armed = True

        lvl = S.level
        if lvl == 0 or not fresh:
            continue
        on, freq, n, on_ms, pause, interval, maxrep = _cfg(C, lvl)
        if not on or (maxrep and S.count >= maxrep) or SOUND.locked():
            continue
        if S.last_beep is None or time.ticks_diff(now, S.last_beep) >= interval:
            S.last_beep = now
            S.count += 1
            asyncio.create_task(beep(dev, C, freq, n, on_ms, pause))
