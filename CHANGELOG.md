# Changelog

## v2.0.0-dev17 – 2026-10-18 (in development)

Based on dev14 (felt the best on the device); dev15 / dev16 are dropped:
no year dose ring, RadiaCode read every 1 s and clicks in 1 s chunks again
(0.5 s felt slower).
- Fix: empty RadiaCode records (rate and CPS exactly 0) are ignored
  (display, alarms, dose, log).
- Log: lines on a fixed 5 s grid of the clock; uSv/h and Dose15 with
  3 decimals.
- Alarms always first: LED runs (HIGH, heartbeat) are no longer lost when
  the program is held up (e.g. by a page redraw) – they continue where they
  stopped instead of skipping steps; sirens keep following their sound.
- The dose gap limit no longer depends on the poll interval.

## v2.0.0-dev16 – 2026-10-18 (in development)

- Fix: with dev15 no readings arrived although connected (the zero filter
  skipped every valid reading).

## v2.0.0-dev15 – 2026-10-18 (in development)

- **Year dose** on the DOSE page: every 20 s the symbol is replaced for 5 s
  by a thin violet ring + value (whole measured dose this calendar year,
  µSv / mSv, ring full at 1 mSv). Stored in `/flash/radzilla/yeardose.json`
  (every 10 min and when stopping / switching off), reset at the new year.
- Faster readings: RadiaCode read every 0.5 s (`RC_POLL_MS`, was 1 s) – the
  RadiaCode updates its values every 0.5 s.
- Counter clicks in 0.5 s chunks (`CLICK_CHUNK_MS`, adjustable).
- Fix: empty RadiaCode records (rate and CPS exactly 0) are ignored.
- Fix: the dose gap limit no longer depends on the poll interval.
- Log: lines on a fixed 5 s grid of the clock; uSv/h and Dose15 with
  3 decimals.

## v2.0.0-dev14 – 2026-10-18 (in development)

- Counter clicks louder (tested on the device): volume 50 -> 80 %,
  dimmed x 0.75 (38 -> 60 %).

## v2.0.0-dev13 – 2026-10-18 (in development)

- Counter clicks reworked for source finding (16 kHz):
  - up to 50 CPS 1:1 with the count rate, soft tick, pitch rises slightly
  - 50 -> 300 CPS (≈ DANGER for Cs-137) denser (up to 70/s) and harder
  - above, the clicks turn into a subtle monotone scream in the timbre of
    the DANGER siren, max. 100 clicks/s at 30 000 CPS (end of the RC-102 range)
  - volume 40 -> 70 % (dimmed half: 20 -> 35 %), logarithmic
- Splash LEDs smooth: own 25 ms task independent of drawing; three dim
  green dots circle with the electrons, every click flashes and fades out
  (green -> yellow -> orange -> red), red at the end with a soft fade-out.

## v2.0.0-dev12 – 2026-10-18 (in development)

- Fix: during a HIGH / DANGER / DOSE alarm the LEDs stayed dark after the
  alarm signals. Now the heartbeat run continues every 10 s
  (`HEARTBEAT_ALARM_S`) once the beeps / siren are over.
- Heartbeat colour follows the dose rate (logarithmic): green up to
  0.12 µSv/h, slightly yellow-green up to 0.18, towards yellow up to 0.20;
  HIGH yellow -> orange -> nearly red at 10 µSv/h; DANGER / DOSE red
  (`HB_*` in config.py). 40 %, also while dimmed.

## v2.0.0-dev11 – 2026-10-18 (in development)

- **Counter clicks** on the CPS page: quiet clicks with the count rate
  (randomly spaced, 1 s WAV built in RAM every second); 1:1 up to 5 CPS,
  above logarithmic up to 60 clicks/s (`CLICK_TABLE`). Volume 20 %, 13 %
  while dimmed; paused during alarm sounds. On / off: hold the large
  radiation symbol 2 s (one vibration), stored in
  `/flash/radzilla/settings.json` (not in git).
- Splash: the LED flashes go from green over yellow and orange to red.

## v2.0.0-dev10 – 2026-10-18 (in development)

Power saving without losing functions (readings still every second, drawn
at once):
- CPU clock 160 MHz instead of 240 MHz (`CPU_MHZ`).
- Touch / buttons read every 50 ms while the display is dimmed (20 ms
  otherwise); the effect control sleeps until an effect starts.
- Device battery read in one place every 2 s (`BAT_READ_S`) instead of on
  every redraw; clock checked once per second instead of every 100 ms.
- DIAG line also shows the CPU clock and the battery current (mA) to compare
  the power use.

## v2.0.0-dev9 – 2026-10-18 (in development)

- Automatic switch-off when the device battery stays below 5 % for 30 s
  (on battery only, also during an alarm): "AKKU LEER" with a 10 s
  countdown and vibration, log saved, then `Power.powerOff()`. Switch on
  again with the power button. Settings `BAT_OFF_*` in config.py.

## v2.0.0-dev8 – 2026-10-18 (in development)

- Heartbeat run (every 20 s) at 40 % LED brightness (`HEARTBEAT_LEVEL_PCT`);
  splash stays at 50 %, alarms at 80 %.
- Display brightness 130 (was 140).
- Log on by default again (line every 5 s); `LOG` on the SET page switches
  it off until the next start.

## v2.0.0-dev7 – 2026-10-17 (in development)

- **Log off by default**: fourth button `LOG` on the SET page, green = on,
  grey = off (footer `LOG SD` / `LOG OFF`); not stored, off after every
  start. The SET buttons are narrower: `+WIFI`, `PHONE`, `SYNC`, `LOG`.
- Log interval 5 s (was 3 s); an extra line immediately when an alarm starts
  or ends.
- Status bar: radiation symbol and "RC 100%" 16 px further left (touched the
  battery icon at 100 %), device battery icon 4 px further right.
- Radiation symbol in the status bar: grey without RadiaCode connection,
  yellow when connected.

## v2.0.0-dev6 – 2026-10-17 (in development)

- Fix: with dev5 the battery always showed the green bolt – the USB voltage
  reads ~5.1 V also without cable (internal 5 V boost). The cable is now
  detected by the charge flag and the battery current (+mA with cable,
  -mA on battery; tools/rz_batt_test.py).
- Battery level computed from the voltage corrected by current x internal
  resistance (`BAT_RINT_MOHM` 250), smoothed; UIFlow's level already shows
  100 % at 4.12 V. Measured: 4.122 V / -88 mA -> 94 %, charging
  4.196 V / +115 mA -> "~97%".

## v2.0.0-dev5 – 2026-10-17 (in development)

- Device battery with the cable: lightning bolt instead of the fill level –
  yellow + estimated level "~64%" while charging (voltage minus 150 mV,
  because the charger lifts the voltage), green + "100%" when full.
- Swipe direction reversed: swipe right = next page, swipe left = previous.
- Docs: set WiFi networks from the Thonny shell.

## v2.0.0-dev4 – 2026-10-17 (in development)

- Display brightness 140, dimmed 30 (after 90 s).
- Waking the display by picking it up is off (`WAKE_ON_PICKUP`); touch,
  buttons and alarms still wake it.
- LEDs: 50 % for the heartbeat run and the splash, 80 % for alarms
  (`LED_ALARM_LEVEL_PCT`); heartbeat every 20 s, run slower (110 ms per step).

## v2.0.0-dev3 – 2026-10-17 (in development, stage 3)

- **SET page**: stored WiFi networks (max. 5), time status, buttons
  `+ WIFI`, `PHONE`, `SYNC`.
- **+ WIFI**: scan, choose a network, password with the on-screen keyboard
  (dot-matrix style; a–z, A–Z, 0–9, symbols).
- **PHONE**: own WiFi "RadZilla-Setup" (WPA2, random 8-digit password on the
  display), page http://192.168.4.1 to choose a network and enter the
  password; closes after saving or 5 min.
- Networks in `/flash/radzilla/wifi.json` (never in git); the network saved
  in UIFlow is taken over on the first start.
- **Time sync** with the PTB atomic clock (NTP) after the splash, every 24 h
  and with `SYNC`; WiFi only on during the sync. The clock runs in UTC
  (system time + battery-backed BM8563), the display shows German local
  time with automatic summer time. Without a valid time: `--:--`, log off.
- Full 5x7 font (all printable ASCII characters).
- Single taps with position for buttons; double tap changes the page except
  on the SET page.

## v2.0.0-dev2 – 2026-10-17 (in development, stage 2)

- **Splash**: atom with the radiation symbol as core, three orbits and green
  electrons, "RadZilla", version, copyright; jingle (60 %) with LED flash and
  vibration on every Geiger click; a tap skips it. Bluetooth search starts
  meanwhile.
- **Effects** (`fx.py`): sound, LEDs and vibration in sync, one at a time by
  priority DANGER > DOSE > HIGH > Geiger > heartbeat.
  - DANGER: siren (3 bursts) once per alarm event, red run + vibration per burst
  - DOSE: siren (~6 s) once, LEDs pulse red with the pitch, vibration at start/end
  - HIGH: beep + yellow run + vibration (max. 3x, every 10 s)
  - Geiger pre-warning at 80 %: clicks with orange LED flicker
  - normal: green run every 30 s (also while dimmed)
  - LED_MODE "run" (centre -> ends) or "blink"; all times/levels in config.py
- Sounds as WAV files in `radzilla/sounds/`, played from RAM with
  `Speaker.playWav()` – `playWavFile()` blocks the program for the whole sound
  (tools/rz_wav_test.py). Generators in `tools/sound_src/`.
- HIGH threshold 0.20 µSv/h; alarms use only the dose rate (energy-corrected,
  independent of the model).
- **Autostart** with `device/main.py` (boot option 0); hold A while switching
  on to skip.

## v2.0.0-dev1 – 2026-10-17 (in development, stage 1)

First version of RadZilla M5 for the M5Stack Core2 (UIFlow 2.5.3).

- New modular structure: `core/` (no hardware), `devices/core2.py`
  (hardware layer, prepared for the StopWatch), `ui/` (drawing, layouts).
- Design A1: self-drawn 5x7 dot-matrix font and 7-segment digits with ghost
  segments. Drawn directly on the display, only changed parts are redrawn
  (a pushed canvas does not reliably reach the Core2 display, especially with
  the microSD card on the shared bus – tools/rz_sd_test*.py).
- microSD via UIFlow `hardware.sdcard` with slot 2 (SPI3, shared with the
  display), 4 MHz; slot 3 must not be used on the Core2.
- Pages RATE, CPS, DOSE, SET (placeholder); colour by alarm state
  (green / yellow / red / grey).
- Values with 3 significant digits (0.12 / 12.5 / 125); from 1000 µSv/h in
  mSv/h, from 10 000 CPS in kCPS. Trend as arrow behind the value
  (grey stable, orange rising, green falling).
- Alarm, dose, trend and RadiaCode logic taken over from RadZilla v1.4.1;
  alarms now need no acknowledgement (HIGH and DANGER beep max. 3 times).
- Touch controls (double tap, swipe), buttons A / B / C; holding B for 2 s
  switches Bluetooth to the RadiaCode off / on (confirmation text +
  vibration, always on after a restart).
- Brightness 150, auto-dim to 40 after 90 s, wake on touch / pick-up / alarm
  (changed in dev4).
- CSV log on microSD (`/sd/RadZilla/logs/`, fallback flash), new columns
  Lat;Lon;Alt for GPS, 7 days / 25 MB.
- Hardware and design test scripts in `tools/`.
