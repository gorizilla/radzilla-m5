# config.py – all settings of RadZilla M5.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# All values can be changed freely. Upload the file and restart RadZilla.
# ⚠ Experimental: thresholds and conversion factor are not calibrated –
#   see NOTICE.md. Not a safety device.

VERSION = "2.0.0-dev1"
DEVICE = "core2"            # hardware module in devices/ (later also "stopwatch")
DIAG = False                # True: print a status line to the shell every 5 s

# --- Display -------------------------------------------------------------------
BRIGHTNESS = 150            # 0..255
DIM_ON = True               # dim after DIM_AFTER_S without any action
DIM_AFTER_S = 90
DIM_BRIGHTNESS = 40
WAKE_ON_PICKUP = True       # picking the device up wakes the display (motion sensor)
PICKUP_G = 0.15             # change of acceleration that counts as "picked up"
REDRAW_MS = 100             # check for redraws this often

# --- Touch / buttons -----------------------------------------------------------
# Double tap on the display or swipe = next / previous page,
# A = previous page, C = next page, B = DOSE page,
# B held = Bluetooth to the RadiaCode off / on (always on after a restart)
TAP_MAX_MS = 250            # a tap is shorter than this ...
TAP_MOVE_PX = 20            # ... and moves less than this
DOUBLE_TAP_MS = 400         # max. gap between the two taps of a double tap
SWIPE_PX = 60               # min. horizontal movement of a swipe
B_HOLD_MS = 2000            # B held this long = Bluetooth off / on
BT_VIB_LEVEL = 200          # confirmation vibration (0..255) ...
BT_VIB_MS = 150             # ... and its length

# --- RadiaCode -----------------------------------------------------------------
# Empty = first device whose name starts with RC_NAME_PREFIX.
# Fixed name e.g. "RadiaCode-102#RC-102-012345"
RC_NAME = ""
RC_NAME_PREFIX = "RadiaCode"
RC_SCAN_MS = 5000           # scan time per attempt
RC_RECONNECT_MS = 5000      # pause before the next attempt
RC_POLL_MS = 1000           # read interval
RC_STALE_MS = 5000          # no new values for this long -> show "--"
RC_SHOW_INFO = True         # show name, serial number and firmware after connecting
RC_INFO_MS = 2000           # ... for this long
RC_DOSE_FACTOR = 10000.0    # raw dose rate -> µSv/h (compare with the RadiaCode display!)

# --- Alarm thresholds (µSv/h) --------------------------------------------------
LEVEL1_USV = 0.28           # HIGH   – about 2x local background
LEVEL2_USV = 10.0           # DANGER – immediate alarm
HYSTERESIS = 0.10           # an alarm ends only below threshold x 0.9 (also dose alarm)
# Alarms need no acknowledgement. Several at once: DANGER > DOSE > HIGH.

# --- Ring on the RATE / CPS page -------------------------------------------------
# Shows the dose rate on a logarithmic scale from RING_MIN_USV to RING_MAX_USV.
RING_MIN_USV = 0.01
RING_MAX_USV = 10.0

# --- Dose alarm (15-min window) -------------------------------------------------
# Triggers when the dose of the last DOSE_WINDOW_MIN minutes exceeds
# DOSE_LIMIT_USV: 2.5 µSv / 15 min -> 10 µSv/h after ~15 min, 100 µSv/h after ~1.5 min.
DOSE_ON = True
DOSE_WINDOW_MIN = 15
DOSE_LIMIT_USV = 2.5

# --- DOSE page ---------------------------------------------------------------------
# Outer ring: 15-min dose in % of DOSE_LIMIT_USV – green < RING_FAIR_PCT,
#   yellow < RING_WARN_PCT, orange < 100 %, red from 100 % (= DOSE alarm).
# Inner ring (blue): extra dose today above BACKGROUND_USV in % of
#   DAILY_BUDGET_USV (2.7 µSv/day ≈ 1 mSv/year) – information only.
RING_FAIR_PCT = 50
RING_WARN_PCT = 80
BACKGROUND_USV = 0.15
DAILY_BUDGET_USV = 2.7

# --- Sounds (stage 1: simple tones; sirens/LEDs/vibration follow in stage 2) ---------
ALARM_VOLUME_PCT = 100      # speaker volume for alarms (0..100)

ALARM1_ON = True            # HIGH
ALARM1_FREQ_HZ = 2000
ALARM1_BEEPS = 1
ALARM1_BEEP_MS = 100
ALARM1_PAUSE_MS = 100
ALARM1_INTERVAL_MS = 10000
ALARM1_MAX_REPEAT = 3       # 0 = unlimited

ALARM2_ON = True            # DANGER
ALARM2_FREQ_HZ = 3000
ALARM2_BEEPS = 3
ALARM2_BEEP_MS = 100
ALARM2_PAUSE_MS = 100
ALARM2_INTERVAL_MS = 2000
ALARM2_MAX_REPEAT = 3       # 0 = unlimited

ALARM3_ON = True            # DOSE – plays once per alarm event
ALARM3_FREQ_HZ = 2500
ALARM3_BEEPS = 2
ALARM3_BEEP_MS = 150
ALARM3_PAUSE_MS = 100

GEIGER_ON = True            # clicks once when the dose ring reaches RING_WARN_PCT
GEIGER_DURATION_MS = 5000
GEIGER_RATE_HZ = 12
GEIGER_CLICK_MS = 3
GEIGER_FREQ_HZ = 3000

# --- RadiaCode signal (the RadiaCode itself beeps / vibrates) ---------------------
# On HIGH / DANGER start the RadiaCode plays its short alarm (3 beeps + vibration).
# Only value 1 is ever sent; nothing is changed in the RadiaCode settings.
RC_SIGNAL_ON = True
RC_SIGNAL_HIGH_COUNT = 1
RC_SIGNAL_DANGER_COUNT = 2
RC_SIGNAL_GAP_MS = 5000

# --- Trend --------------------------------------------------------------------------
TREND_WINDOW_S = 10         # average of the last window vs. the window before
TREND_PCT = 0.10
TREND_MIN_USV = 0.02
TREND_MIN_CPS = 1.0

# --- CSV log ------------------------------------------------------------------------
# Time;uSv/h;CPS;Alarm;Dose15;Lat;Lon;Alt  (Lat/Lon/Alt stay empty until GPS, stage 4)
#   Alarm 0 none, 1 HIGH, 2 DANGER, 3 DOSE (state, DANGER > DOSE > HIGH)
# Semicolon + decimal comma -> opens directly in German Numbers/Excel.
LOG_ON = True
SD_FREQ = 4_000_000          # microSD bus clock (shared with the display)
LOG_SD_DIR = "/sd/RadZilla/logs"        # microSD (FAT32)
LOG_INT_DIR = "/flash/RadZilla/logs"    # fallback without SD card
LOG_INTERVAL_S = 3
LOG_FLUSH_S = 60            # buffered, written every 60 s
LOG_FILE_H = 24             # new file after this run time
LOG_MAX_AGE_H = 168         # 7 days – older files are deleted
LOG_MAX_FILES = 200
LOG_MAX_TOTAL_KB = 25600    # 25 MB on the SD card
LOG_MIN_FREE_KB = 1024
LOG_INT_MAX_TOTAL_KB = 1024 # smaller limits for the internal flash
LOG_INT_MIN_FREE_KB = 512
LOG_CHECK_S = 3600          # clean-up at start and then this often
