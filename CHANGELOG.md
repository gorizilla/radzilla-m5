# Changelog

## v2.0.0-dev1 – 2026-10-17 (in development, stage 1)

First version of RadZilla M5 for the M5Stack Core2 (UIFlow 2.5.3).

- New modular structure: `core/` (no hardware), `devices/core2.py`
  (hardware layer, prepared for the StopWatch), `ui/` (drawing, layouts).
- Design A1: self-drawn 5x7 dot-matrix font and 7-segment digits with ghost
  segments, drawn off-screen on a canvas (~25 frames/s measured).
- Pages RATE, CPS, DOSE, SET (placeholder); colour by alarm state
  (green / yellow / red / grey).
- Alarm, dose, trend and RadiaCode logic taken over from RadZilla v1.4.1;
  alarms now need no acknowledgement (HIGH and DANGER beep max. 3 times).
- Touch controls (double tap, swipe), buttons A / B / C.
- Brightness 150, auto-dim to 80 after 60 s, wake on touch / pick-up / alarm.
- CSV log on microSD (`/sd/RadZilla/logs/`, fallback flash), new columns
  Lat;Lon;Alt for GPS, 7 days / 25 MB.
- Hardware and design test scripts in `tools/`.
