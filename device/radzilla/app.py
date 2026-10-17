# app.py – RadZilla M5 main program: connects the RadiaCode, runs alarms,
# dose, trend and log, handles input and draws the pages.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# ⚠ Experimental – not a safety device. See NOTICE.md.
#
# Pages: RATE (µSv/h large), CPS (CPS large), DOSE (15-min dose + extra dose
# today), SET (stage 3). Colour of symbol, ring and value by alarm state:
# green normal, yellow HIGH, red DANGER, grey no data.
#
# Input: double tap / swipe on the display = next / previous page,
#        A = previous, C = next, B = DOSE page,
#        B held = Bluetooth to the RadiaCode off / on (on after a restart).
#
# All parts run as cooperative asyncio tasks – nothing may block for long.
import asyncio
import math
import sys
import time

from radzilla import config as C
from radzilla.core import state as st
from radzilla.core import trend, dose, alarms
from radzilla.core.logger import Logger
from radzilla.ui import gfx


def _load_device():
    if C.DEVICE == "core2":
        from radzilla.devices.core2 import Device
    else:
        raise ValueError("unknown DEVICE %r in config.py" % C.DEVICE)
    return Device(C)


def _load_pages(layout):
    if layout == "rect":
        from radzilla.ui import pages_rect as pages
    else:
        raise ValueError("no page layout %r yet" % layout)
    return pages


S = st.State()
DEV = None
LOG = None
PAGES = None


# ---------- formatting ---------------------------------------------------------------
def fmt_val(v):
    """Value for 4 seven-segment digits: 0.12 / 12.5 / 125 / 9999."""
    if v < 10:
        return "%.2f" % v
    if v < 100:
        return "%.1f" % v
    return "%d" % min(9999, int(v + 0.5))


def fmt_pct(p):
    return "%d" % min(999, int(p + 0.5))


def ring_frac(usv):
    """Dose rate on a logarithmic scale RING_MIN_USV .. RING_MAX_USV -> 0..1."""
    if not usv or usv <= C.RING_MIN_USV:
        return 0.0
    lo, hi = math.log10(C.RING_MIN_USV), math.log10(C.RING_MAX_USV)
    return min(1.0, (math.log10(usv) - lo) / (hi - lo))


LEVEL_COL = (gfx.GREEN, gfx.YELLOW, gfx.RED)
DOSE_COL = (gfx.GREEN, gfx.YELLOW, gfx.ORANGE, gfx.RED)


class View:
    """Everything the page layout needs, as plain values."""
    pass


def build_view():
    v = View()
    fresh = S.fresh(C.RC_STALE_MS)
    t, valid = DEV.now()
    v.time_str = "%02d:%02d" % (t[3], t[4]) if valid else "--:--"
    v.rc_txt = "RC %d%%" % S.batt if (S.connected and S.batt is not None) else "RC --"
    v.batt_pct, chg = DEV.battery()
    v.batt_col = gfx.GREEN if (chg or v.batt_pct is None or v.batt_pct > 20) else gfx.RED
    v.page = S.page
    v.version = C.VERSION

    # state label (top right): DANGER > DOSE > HIGH > LIVE / NO RC
    if not S.bt_on:
        v.state_txt, v.state_col = "BT OFF", gfx.GREY
    elif not fresh:
        v.state_txt, v.state_col = "NO RC", gfx.GREY
    elif S.level == 2:
        v.state_txt, v.state_col = "DANGER", gfx.RED
    elif S.dose_active:
        v.state_txt, v.state_col = "DOSE", gfx.RED
    elif S.level == 1:
        v.state_txt, v.state_col = "HIGH", gfx.YELLOW
    else:
        v.state_txt, v.state_col = "LIVE", gfx.GREEN

    v.main_col = LEVEL_COL[S.level] if fresh else gfx.GREY
    usv_s = fmt_val(S.usv) if fresh else "--"
    cps_s = fmt_val(S.cps) if fresh else "--"
    v.ring_frac = ring_frac(S.usv) if fresh else 0.0
    if S.page == st.PAGE_CPS:
        v.big, v.big_label, v.big_unit = cps_s, "COUNT RATE", "CPS"
        v.sub_label, v.sub_val = "uSv/h", usv_s
        v.trend = trend.text(trend.get(S, C, trend.CPS) if fresh else None)
    else:
        v.big, v.big_label, v.big_unit = usv_s, "DOSE RATE", "uSv/h"
        v.sub_label, v.sub_val = "CPS", cps_s
        v.trend = trend.text(trend.get(S, C, trend.USV) if fresh else None)
    v.sub_col = gfx.WHITE if fresh else gfx.GREY

    # dose
    p, e = dose.pct(S, C), dose.extra_pct(S, C)
    v.d_frac, v.e_frac = p / 100, e / 100
    v.d_pct_txt, v.e_pct_txt = fmt_pct(p), fmt_pct(e)
    v.d_col = DOSE_COL[dose.stage(S, C)]
    v.d_usv, v.e_usv = "%.2f" % S.dose_total, "%.2f" % S.extra_total
    v.d_lim, v.e_lim = "%g" % C.DOSE_LIMIT_USV, "%g" % C.DAILY_BUDGET_USV
    v.window_min = C.DOSE_WINDOW_MIN

    # footer: device / connection status left, log status right
    if S.connected:
        v.footer_l, v.footer_l_col = (S.serial or S.name or "CONNECTED"), gfx.GREY
    else:
        v.footer_l = S.status
        v.footer_l_col = gfx.RED if S.status == st.ST_NO_AIOBLE else gfx.GREY
    txt, ok = LOG.status(valid)
    v.footer_r, v.footer_r_col = txt, gfx.GREY if ok else gfx.RED

    v.overlay = None
    if S.overlay is not None:
        if time.ticks_diff(S.overlay_until, time.ticks_ms()) > 0:
            v.overlay = S.overlay
        else:
            S.overlay = None
    return v


# ---------- display & brightness ---------------------------------------------------------
class Light:
    def __init__(self):
        self.last_active = time.ticks_ms()
        self.dimmed = False
        DEV.set_brightness(C.BRIGHTNESS)

    def wake(self):
        self.last_active = time.ticks_ms()
        if self.dimmed:
            self.dimmed = False
            DEV.set_brightness(C.BRIGHTNESS)

    def check(self):
        if C.DIM_ON and not self.dimmed and \
                time.ticks_diff(time.ticks_ms(), self.last_active) >= C.DIM_AFTER_S * 1000:
            self.dimmed = True
            DEV.set_brightness(C.DIM_BRIGHTNESS)


LIGHT = None
DIAG = {"draws": 0, "last_ms": 0, "max_ms": 0}


async def display_task():
    last_min = None
    while True:
        t, _ = DEV.now()
        if t[4] != last_min:                 # clock changed
            last_min = t[4]
            S.dirty = True
        if S.overlay is not None and time.ticks_diff(S.overlay_until, time.ticks_ms()) <= 0:
            S.dirty = True                   # overlay expired
        if S.dirty:
            S.dirty = False
            t0 = time.ticks_ms()
            try:
                PAGES.draw(DEV.gfx(), build_view())
                DEV.show()
            except Exception as e:
                print("Draw error:")
                sys.print_exception(e)
            dt = time.ticks_diff(time.ticks_ms(), t0)
            DIAG["draws"] += 1
            DIAG["last_ms"] = dt
            DIAG["max_ms"] = max(DIAG["max_ms"], dt)
        await asyncio.sleep_ms(C.REDRAW_MS)


async def light_task():
    """Auto-dim; picking the device up wakes the display."""
    prev = None
    while True:
        await asyncio.sleep_ms(200)
        LIGHT.check()
        if not C.WAKE_ON_PICKUP:
            continue
        a = DEV.accel()
        if a is None:
            continue
        if prev is not None and LIGHT.dimmed:
            d = math.sqrt(sum((a[i] - prev[i]) ** 2 for i in range(3)))
            if d >= C.PICKUP_G:
                LIGHT.wake()
        prev = a


# ---------- input -------------------------------------------------------------------------
def set_page(p):
    S.page = p % st.N_PAGES
    S.dirty = True


async def _vibrate(ms):
    DEV.vibrate(C.BT_VIB_LEVEL)
    await asyncio.sleep_ms(ms)
    DEV.vibrate(0)


def toggle_bt():
    """B held: Bluetooth to the RadiaCode off / on (on again after a restart).
    While off there are no readings, no alarms and no log."""
    S.bt_on = not S.bt_on
    print("Bluetooth", "on" if S.bt_on else "off")
    S.show_overlay(["BLUETOOTH ON" if S.bt_on else "BLUETOOTH OFF"], 1500)
    asyncio.create_task(_vibrate(C.BT_VIB_MS))


async def input_task():
    while True:
        try:
            for e in DEV.poll():
                if e == "active":
                    LIGHT.wake()
                elif e == "next":
                    set_page(S.page + 1)
                elif e == "prev":
                    set_page(S.page - 1)
                elif e == "dose":
                    set_page(st.PAGE_DOSE)
                elif e == "hold_b":
                    toggle_bt()
        except Exception as e:
            print("Input error:", repr(e))
        await asyncio.sleep_ms(20)


# ---------- log -----------------------------------------------------------------------------
async def log_task():
    while True:
        await asyncio.sleep_ms(C.LOG_INTERVAL_S * 1000)
        t, valid = DEV.now()
        if valid and S.connected and S.fresh(C.RC_STALE_MS):
            was = LOG.full, LOG.error
            LOG.add(t, S.usv, S.cps, S.log_alarm(), S.dose_total)
            if (LOG.full, LOG.error) != was:
                S.dirty = True


async def diag_task():
    import gc
    while True:
        await asyncio.sleep_ms(5000)
        print("DIAG page=%d usv=%s cps=%s lvl=%d dose=%.3f draws=%d draw=%dms (max %d) free=%dKB"
              % (S.page, S.usv, S.cps, S.level, S.dose_total, DIAG["draws"],
                 DIAG["last_ms"], DIAG["max_ms"], gc.mem_free() // 1024))
        DIAG["max_ms"] = 0


# ---------- RadiaCode ------------------------------------------------------------------------
def _set_status(text, connected=False):
    S.status = text
    S.connected = connected
    S.dirty = True


async def _show_info(rc, name):
    """Read serial number and firmware (read only) and show them briefly."""
    lines = [name.split("#")[0]]
    S.serial = None
    try:
        S.serial = await rc.serial_number()
        lines.append(S.serial)
    except Exception as e:
        print("RadiaCode serial:", repr(e))
    try:
        lines.append("FW " + await rc.fw_version())
    except Exception as e:
        print("RadiaCode firmware:", repr(e))
    print("RadiaCode info:", " | ".join(lines))
    if C.RC_SHOW_INFO:
        S.show_overlay(lines, C.RC_INFO_MS)


def _bt_radio(on):
    """Switch the Bluetooth radio itself (aioble switches it on again when
    it scans)."""
    try:
        import bluetooth
        bluetooth.BLE().active(on)
    except Exception as e:
        print("Bluetooth radio:", repr(e))


async def rc_loop():
    """Find the RadiaCode, connect, read every RC_POLL_MS, reconnect on loss."""
    try:
        from radzilla.core import radiacode
    except ImportError:
        _set_status(st.ST_NO_AIOBLE)
        print("aioble is not installed - see docs/SETUP.md")
        while True:
            await asyncio.sleep_ms(10000)

    while True:
        if not S.bt_on:                          # switched off with B held
            _bt_radio(False)
            S.level = 0                          # alarms start anew after BT on
            S.last_ms = None
            S.last_rd_ms = None
            _set_status(st.ST_BT_OFF)
            while not S.bt_on:
                await asyncio.sleep_ms(200)
            continue
        rc = None
        try:
            _set_status(st.ST_SCAN)
            dev, name = await radiacode.find(C.RC_NAME, C.RC_NAME_PREFIX, C.RC_SCAN_MS)
            if not S.bt_on:
                continue
            if dev is None:
                _set_status(st.ST_NOTFOUND)
                await asyncio.sleep_ms(C.RC_RECONNECT_MS)
                continue
            _set_status(st.ST_CONNECTING)
            S.name = name
            rc = await radiacode.RadiaCode.connect(dev)
            print("RadiaCode connected:", name)
            S.hist = []
            S.rc_sig_pending = 0
            await _show_info(rc, name)
            _set_status(st.ST_CONNECTED, True)
            while rc.is_connected() and S.bt_on:
                d = await rc.read_data()
                if "cps" in d:
                    S.cps = d["cps"]
                    S.usv = d["dose_raw"] * C.RC_DOSE_FACTOR
                    S.last_ms = time.ticks_ms()
                    trend.add(S, C, S.usv, S.cps)
                    dose.add(S, C, S.usv, S.last_ms)
                if "batt" in d:
                    S.batt = d["batt"]
                if alarms.update_level(S, C):
                    LIGHT.wake()                 # alarm started / escalated
                await alarms.play_rc_signal(S, C, rc)
                S.dirty = True
                await asyncio.sleep_ms(C.RC_POLL_MS)
        except Exception as e:
            print("RadiaCode:", repr(e))
        if rc:
            await rc.disconnect()
        S.last_rd_ms = None                      # gap: no dose is counted
        if not S.bt_on:
            continue
        _set_status(st.ST_DISCONNECTED)
        await asyncio.sleep_ms(C.RC_RECONNECT_MS)


# ---------- start -----------------------------------------------------------------------------
async def main():
    global DEV, LOG, PAGES, LIGHT
    DEV = _load_device()
    PAGES = _load_pages(DEV.LAYOUT)
    LOG = Logger(C, DEV.sd_mounted)
    LIGHT = Light()
    print("RadZilla M5 v%s on %s, log: %s" % (C.VERSION, DEV.NAME, LOG.dir))
    asyncio.create_task(display_task())
    asyncio.create_task(input_task())
    asyncio.create_task(light_task())
    asyncio.create_task(log_task())
    asyncio.create_task(alarms.task(DEV, S, C))
    if C.DIAG:
        asyncio.create_task(diag_task())
    await rc_loop()


def run():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")
    finally:
        if LOG is not None:
            LOG.flush()                      # save the log buffer
        asyncio.new_event_loop()
