# state.py – shared state of the RadiaCode monitor (no hardware access).
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
import time

# connection status (shown in the footer while not connected)
ST_START = "START"
ST_SCAN = "SCANNING"
ST_NOTFOUND = "NOT FOUND"
ST_CONNECTING = "CONNECTING"
ST_CONNECTED = "CONNECTED"
ST_DISCONNECTED = "DISCONNECTED"
ST_NO_AIOBLE = "AIOBLE MISSING"

PAGE_RATE, PAGE_CPS, PAGE_DOSE, PAGE_SET = 0, 1, 2, 3
N_PAGES = 4


class State:
    def __init__(self):
        self.status = ST_START
        self.connected = False
        self.name = ""
        self.serial = None
        self.cps = None
        self.usv = None
        self.batt = None            # RadiaCode battery in %
        self.last_ms = None         # time of the last reading
        self.page = PAGE_RATE
        # dose-rate alarm
        self.level = 0              # 0 / 1 HIGH / 2 DANGER
        self.count = 0              # beeps played in the current level
        self.last_beep = None
        # trend
        self.hist = []              # (ticks_ms, usv, cps)
        # dose
        self.dose_hist = []         # (ticks_ms, µSv increment) within the window
        self.dose_total = 0.0       # µSv within the window
        self.extra_total = 0.0      # µSv above background since switching on
        self.last_rd_ms = None      # previous reading (None = gap)
        self.dose_active = False
        self.geiger_armed = True
        # RadiaCode signal
        self.rc_sig_pending = 0
        self.rc_sig_next = 0
        # overlay (device info / notices)
        self.overlay = None         # list of text lines or None
        self.overlay_until = 0
        self.dirty = True

    def fresh(self, stale_ms):
        """True if the last reading is recent enough to be shown."""
        return self.last_ms is not None and \
            time.ticks_diff(time.ticks_ms(), self.last_ms) < stale_ms

    def show_overlay(self, lines, ms):
        self.overlay = lines
        self.overlay_until = time.ticks_add(time.ticks_ms(), ms)
        self.dirty = True

    def log_alarm(self):
        """Alarm code for the log: 2 DANGER > 3 DOSE > 1 HIGH > 0."""
        if self.level == 2:
            return 2
        if self.dose_active:
            return 3
        return self.level
