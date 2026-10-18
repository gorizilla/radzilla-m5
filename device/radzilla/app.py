# app.py – RadZilla M5 main program: connects the RadiaCode, runs alarms,
# dose, trend and log, handles input and draws the pages.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# ⚠ Experimental – not a safety device. See NOTICE.md.
#
# Pages: RATE (µSv/h large), CPS (CPS large), DOSE (15-min dose + extra dose
# today), SET (WiFi, time, log). Colour of symbol, ring and value by alarm
# state: green normal, yellow HIGH, red DANGER, grey no data.
#
# Input: double tap / swipe on the display = next / previous page,
#        A = previous, C = next, B = DOSE page,
#        B held = Bluetooth to the RadiaCode off / on (on after a restart),
#        radiation symbol held 2 s = RadiaCode ticker (CPS) / spectrum reset (RATE).
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
from radzilla import fx
from radzilla.core import timesync, wificfg
from radzilla.ui import gfx, splash


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
def fmt3(v):
    """3 significant digits: 0.12 / 9.87 / 12.5 / 125 (up to 999)."""
    if v < 9.995:
        return "%.2f" % v
    if v < 99.95:
        return "%.1f" % v
    return "%d" % int(v + 0.5)


def fmt_usv(v):
    """Dose rate -> (text, unit); from 1000 µSv/h in mSv/h."""
    if v < 999.5:
        return fmt3(v), "uSv/h"
    return fmt3(min(v / 1000, 999)), "mSv/h"


def fmt_cps(v):
    """Count rate -> (text, unit); 100..9999 as integer, from 10000 in kCPS."""
    if v < 99.95:
        return fmt3(v), "CPS"
    if v < 9999.5:
        return "%d" % int(v + 0.5), "CPS"
    return fmt3(min(v / 1000, 999)), "kCPS"


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
    v.rc_connected = S.connected
    v.batt_pct, v.batt_mode = BATT
    v.batt_col = gfx.GREEN if (v.batt_mode != "bat" or v.batt_pct is None or v.batt_pct > 20) else gfx.RED
    if v.batt_pct is None:
        v.batt_txt = "--"
    elif v.batt_mode == "chg":
        v.batt_txt = "~%d%%" % v.batt_pct
    else:
        v.batt_txt = "%d%%" % v.batt_pct
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
    usv_s, usv_u = fmt_usv(S.usv) if fresh else ("--", "uSv/h")
    cps_s, cps_u = fmt_cps(S.cps) if fresh else ("--", "CPS")
    v.ring_frac = ring_frac(S.usv) if fresh else 0.0
    if S.page == st.PAGE_CPS:
        v.big, v.big_label, v.big_unit = cps_s, "COUNT RATE", cps_u
        v.sub_label, v.sub_val = usv_u, usv_s
        v.trend = trend.get(S, C, trend.CPS) if fresh else None
    else:
        v.big, v.big_label, v.big_unit = usv_s, "DOSE RATE", usv_u
        v.sub_label, v.sub_val = cps_u, cps_s
        v.trend = trend.get(S, C, trend.USV) if fresh else None
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

    v.wifi = [s for s, _ in NETS]
    v.log_on = C.LOG_ON
    v.wifi_max = C.WIFI_MAX
    if SYNC["busy"]:
        v.sync_txt, v.sync_col = "SYNCING ...", gfx.YELLOW
    elif SYNC["msg"]:
        v.sync_txt, v.sync_col = SYNC["msg"], gfx.RED
    elif SYNC["last"]:
        lt = SYNC["last"]
        v.sync_txt, v.sync_col = "OK %02d.%02d. %02d:%02d" % (lt[2], lt[1], lt[3], lt[4]), gfx.GREEN
    elif valid:
        v.sync_txt, v.sync_col = "CLOCK OK", gfx.GREY
    else:
        v.sync_txt, v.sync_col = "NOT SYNCED", gfx.RED

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
FX = None
DIAG = {"draws": 0, "last_ms": 0, "max_ms": 0}
BATT = [None, "bat"]                    # device battery (pct, mode), read every BAT_READ_S


async def display_task():
    last_min = None
    last_clock = None
    while True:
        now = time.ticks_ms()
        if last_clock is None or time.ticks_diff(now, last_clock) >= 1000:
            last_clock = now                 # check the clock once per second
            t, _ = DEV.now()
            if t[4] != last_min:             # minute changed
                last_min = t[4]
                S.dirty = True
        if S.overlay is not None and time.ticks_diff(S.overlay_until, time.ticks_ms()) <= 0:
            S.dirty = True                   # overlay expired
        if S.modal:                          # a SET dialog owns the display
            await asyncio.sleep_ms(C.REDRAW_MS)
            continue
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
        if S.wake:                           # alarm effect asks to wake the display
            S.wake = False
            LIGHT.wake()
        S.dimmed = LIGHT.dimmed
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


async def rc_request(rc):
    """Run a request from the symbol (one BLE command at a time, from the
    read loop): "ticker" (CPS page) or "spreset" (RATE page). Success:
    one vibration (+ "SP RESET OK"); failure: nothing."""
    req, S.rc_req = S.rc_req, None
    try:
        if req == "ticker":
            ok = await rc.toggle_ticker()
        elif req == "spreset":
            ok = await rc.spectrum_reset()
        else:
            return
    except Exception as e:
        print("RadiaCode %s: %r" % (req, e))
        return
    print("RadiaCode %s: %s" % (req, "ok" if ok else "failed"))
    if ok:
        asyncio.create_task(_vibrate(C.BT_VIB_MS))
        if req == "spreset":
            S.show_overlay(["SP RESET OK"], C.SP_RESET_MSG_MS)


async def power_task():
    """Switch the device off when the battery stays below BAT_OFF_PCT for
    BAT_OFF_HOLD_S (not with the cable; also during an alarm, to protect the
    battery from deep discharge). Warning with countdown, the log is saved."""
    low_since = None
    while True:
        await asyncio.sleep_ms(C.BAT_READ_S * 1000)
        pct, mode = DEV.battery()            # the only place that reads the battery
        if [pct, mode] != BATT:
            BATT[0], BATT[1] = pct, mode
            S.dirty = True
        if mode != "bat" or pct is None or pct >= C.BAT_OFF_PCT:
            low_since = None
            continue
        now = time.ticks_ms()
        if low_since is None:
            low_since = now
        if time.ticks_diff(now, low_since) < C.BAT_OFF_HOLD_S * 1000:
            continue
        print("Battery empty (%d %%) - switching off" % pct)
        from radzilla.ui import setup_rect as dlg
        S.modal = True                       # stops page drawing and taps
        LIGHT.wake()
        asyncio.create_task(_vibrate(C.BT_VIB_MS))
        for n in range(C.BAT_OFF_WARN_S, 0, -1):
            dlg.message(DEV.gfx(), ["AKKU LEER", "AUS IN %d S" % n], gfx.RED)
            await asyncio.sleep_ms(1000)
        t, valid = DEV.now()
        if C.LOG_ON and valid and S.connected and S.fresh(C.RC_STALE_MS):
            LOG.add(t, S.usv, S.cps, S.log_alarm(), S.dose_total)
        LOG.flush()
        DEV.stop_sound()
        DEV.vibrate(0)
        DEV.leds([(0, 0, 0)] * 10)
        DEV.gfx().fillScreen(0)
        DEV.power_off()
        return


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
                if splash.active():          # any touch / button skips the splash
                    if e == "active":
                        splash.skip()
                    continue
                if isinstance(e, tuple) and e[0] == "hold":
                    # large radiation symbol held 2 s: CPS page = RC ticker,
                    # RATE page = restart the RC spectrum (needs a connection)
                    if not S.modal and S.connected and S.bt_on and \
                            PAGES.cps_symbol_at(e[1], e[2]):
                        if S.page == st.PAGE_CPS:
                            S.rc_req = "ticker"
                        elif S.page == st.PAGE_RATE:
                            S.rc_req = "spreset"
                    continue
                if e == "active":
                    LIGHT.wake()
                elif S.modal:                # dialog: only taps, no page change
                    if isinstance(e, tuple):
                        MODAL_Q.append((e[1], e[2]))
                elif isinstance(e, tuple):   # single tap: buttons on the SET page
                    if S.page == st.PAGE_SET:
                        b = PAGES.set_button_at(e[1], e[2])
                        if b:
                            asyncio.create_task(set_action(b))
                elif e == "dtap":
                    if S.page != st.PAGE_SET:
                        set_page(S.page + 1)
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
        await asyncio.sleep_ms(C.INPUT_DIM_MS if LIGHT.dimmed else C.INPUT_MS)


# ---------- WiFi, time sync, SET dialogs ---------------------------------------------------
NETS = []
SYNC = {"busy": False, "msg": None, "last": None, "last_try": None}
MODAL_Q = []
WIFI_LOCK = asyncio.Lock()
LASTSYNC_PATH = "/flash/radzilla/lastsync.txt"


def _load_lastsync():
    try:
        with open(LASTSYNC_PATH) as f:
            s = f.read().strip()
        return (int(s[0:4]), int(s[5:7]), int(s[8:10]), int(s[11:13]), int(s[14:16]), 0)
    except Exception:
        return None


def _save_lastsync(t):
    try:
        with open(LASTSYNC_PATH, "w") as f:
            f.write("%04d-%02d-%02d %02d:%02d\n" % t[:5])
    except OSError as e:
        print("lastsync:", repr(e))


async def do_sync(show=False):
    """Time sync over WiFi. show=True: result as a short overlay."""
    if WIFI_LOCK.locked():
        return
    async with WIFI_LOCK:
        SYNC["busy"] = True
        SYNC["msg"] = None
        SYNC["last_try"] = time.ticks_ms()
        S.dirty = True
        try:
            ok, res = await timesync.sync(DEV, NETS, C.NTP_SERVERS, C.WIFI_TIMEOUT_MS)
        except Exception as e:
            ok, res = False, "SYNC ERROR"
            print("Time sync:", repr(e))
        SYNC["busy"] = False
        if ok:
            SYNC["last"] = res
            _save_lastsync(res)
            print("Time set: %04d-%02d-%02d %02d:%02d:%02d" % res[:6])
        else:
            SYNC["msg"] = res
            print("Time sync failed:", res)
        if show:
            S.show_overlay(["TIME OK" if ok else res], 1500)
        PAGES.invalidate()
        S.dirty = True


async def sync_task():
    """Sync after the splash and then every SYNC_INTERVAL_H hours."""
    if C.SYNC_AT_START and NETS:
        await do_sync()
    while True:
        await asyncio.sleep_ms(60000)
        lt = SYNC["last_try"]
        if NETS and (lt is None or time.ticks_diff(time.ticks_ms(), lt) >= C.SYNC_INTERVAL_H * 3600000):
            await do_sync()


async def get_tap(timeout_ms):
    """Next tap (x, y) for a dialog, or None after timeout_ms."""
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < timeout_ms:
        if MODAL_Q:
            return MODAL_Q.pop(0)
        await asyncio.sleep_ms(20)
    return None


def _scan():
    import network
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    best = {}
    try:
        for r in sta.scan():
            try:
                ssid = r[0].decode()
            except Exception:
                continue
            if ssid and (ssid not in best or r[3] > best[ssid]):
                best[ssid] = r[3]
    finally:
        sta.active(False)
    return sorted(best.items(), key=lambda x: -x[1])


async def set_action(name):
    global NETS
    if name == "log":                    # log on / off, not stored (on after a restart)
        C.LOG_ON = not C.LOG_ON
        if not C.LOG_ON:
            LOG.flush()
        S.dirty = True
        return
    if name == "sync":
        if not NETS:
            S.show_overlay(["NO NETWORK SAVED"], 1500)
            return
        await do_sync(show=True)
        return
    if S.modal or WIFI_LOCK.locked():
        return
    from radzilla.ui import setup_rect as dlg
    g = DEV.gfx()
    S.modal = True
    MODAL_Q.clear()
    new = None
    try:
        async with WIFI_LOCK:
            if name == "add":
                dlg.message(g, ["SCANNING ..."])
                await asyncio.sleep_ms(50)
                nets = _scan()
                ssid = await dlg.choose_network(g, nets, get_tap)
                if ssid:
                    pw = await dlg.keyboard(g, "PASSWORD " + ssid, get_tap)
                    if pw is not None:
                        new = (ssid, pw)
            elif name == "phone":
                new = await _phone_setup(g, dlg)
        if new:
            NETS = wificfg.add(NETS, new[0], new[1], C.WIFI_MAX)
            dlg.message(g, ["SAVED", new[0][:22]], gfx.GREEN)
            await asyncio.sleep_ms(1200)
    except Exception as e:
        print("SET dialog:", repr(e))
    finally:
        S.modal = False
        MODAL_Q.clear()
        PAGES.invalidate()
        S.dirty = True
    if new:
        await do_sync(show=True)


async def _phone_setup(g, dlg):
    import random
    from radzilla.core import portal
    dlg.message(g, ["SCANNING ..."])
    await asyncio.sleep_ms(50)
    ssids = [s for s, _ in _scan()]
    pw = "".join(str(random.randint(0, 9)) for _ in range(8))
    p = portal.Portal(ssids, pw)
    try:
        await p.start()
    except Exception as e:
        print("portal:", repr(e))
        dlg.message(g, ["PHONE SETUP FAILED"], gfx.RED)
        await asyncio.sleep_ms(1500)
        return None
    t0 = time.ticks_ms()
    last_left = None
    dlg.phone_screen(g, portal.AP_NAME, pw, portal.AP_IP, C.PORTAL_TIMEOUT_S)
    try:
        while p.result is None:
            left = C.PORTAL_TIMEOUT_S - time.ticks_diff(time.ticks_ms(), t0) // 1000
            if left <= 0:
                break
            if left != last_left:
                last_left = left
                dlg.phone_countdown(g, left)
            tap = await get_tap(200)
            if dlg.phone_cancel_hit(tap):
                break
        await asyncio.sleep_ms(500)                # let the phone get the "saved" page
    finally:
        await p.stop()
    return p.result


# ---------- log -----------------------------------------------------------------------------
async def log_task():
    """A line every LOG_INTERVAL_S on the clock (:00, :05, ...) and
    immediately when an alarm starts or ends."""
    last_s = None
    last_alarm = S.log_alarm()
    while True:
        await asyncio.sleep_ms(200)
        alarm = S.log_alarm()
        t, valid = DEV.now()
        sec = (t[3] * 60 + t[4]) * 60 + t[5]
        due = sec % C.LOG_INTERVAL_S == 0 and sec != last_s
        if not due and alarm == last_alarm:
            continue
        if due:
            last_s = sec
        last_alarm = alarm
        if not C.LOG_ON:
            continue
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
              " cpu=%dMHz bat=%s%% %s %smA"
              % (S.page, S.usv, S.cps, S.level, S.dose_total, DIAG["draws"],
                 DIAG["last_ms"], DIAG["max_ms"], gc.mem_free() // 1024,
                 DEV.cpu_mhz(), BATT[0], BATT[1], DEV.bat_ma))
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
                if "cps" in d and d["cps"] == 0 and d["dose_raw"] == 0:
                    del d["cps"]                 # empty record from the RC: keep the last value
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
                if S.rc_req:
                    await rc_request(rc)
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
    global DEV, LOG, PAGES, LIGHT, FX
    DEV = _load_device()
    PAGES = _load_pages(DEV.LAYOUT)
    global NETS
    NETS = wificfg.load()
    SYNC["last"] = _load_lastsync()
    LOG = Logger(C, DEV.sd_mounted)
    BATT[0], BATT[1] = DEV.battery()
    LIGHT = Light()
    FX = fx.FX(DEV, C)
    print("RadZilla M5 v%s on %s, log: %s" % (C.VERSION, DEV.NAME, LOG.dir))
    rc = asyncio.create_task(rc_loop())      # Bluetooth search runs during the splash
    asyncio.create_task(input_task())
    await splash.run(DEV, C, "V" + C.VERSION.upper())
    PAGES.invalidate()
    S.dirty = True
    asyncio.create_task(display_task())
    asyncio.create_task(light_task())
    asyncio.create_task(log_task())
    asyncio.create_task(FX.task())
    asyncio.create_task(alarms.task(FX, S, C))
    asyncio.create_task(sync_task())
    asyncio.create_task(power_task())
    if C.DIAG:
        asyncio.create_task(diag_task())
    await rc


def run():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")
    finally:
        if LOG is not None:
            LOG.flush()                      # save the log buffer
        if DEV is not None:                  # LEDs, vibration and sound off
            try:
                DEV.leds([(0, 0, 0)] * 10)
                DEV.vibrate(0)
                DEV.stop_sound()
            except Exception:
                pass
        asyncio.new_event_loop()
