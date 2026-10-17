# Changelog

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
- Alarm, dose, trend and RadiaCode logic taken over from RadZilla v1.4.1;
  alarms now need no acknowledgement (HIGH and DANGER beep max. 3 times).
- Touch controls (double tap, swipe), buttons A / B / C.
- Brightness 150, auto-dim to 80 after 60 s, wake on touch / pick-up / alarm.
- CSV log on microSD (`/sd/RadZilla/logs/`, fallback flash), new columns
  Lat;Lon;Alt for GPS, 7 days / 25 MB.
- Hardware and design test scripts in `tools/`.
