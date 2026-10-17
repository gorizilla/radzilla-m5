# Changelog

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
- HIGH threshold 0.37 µSv/h (= 11 CPS on an RC-102); alarms use only the dose
  rate, independent of the model.
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
- Brightness 150, auto-dim to 40 after 90 s, wake on touch / pick-up / alarm.
- CSV log on microSD (`/sd/RadZilla/logs/`, fallback flash), new columns
  Lat;Lon;Alt for GPS, 7 days / 25 MB.
- Hardware and design test scripts in `tools/`.
