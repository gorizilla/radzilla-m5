# Changelog

## v2.0.0 – 2026-10-18

First release of **RadZilla M5** for the M5Stack Core2 (UIFlow 2.5.3),
successor of RadZilla v1.x for the Waveshare ESP32-S3-LCD-1.69
([gorizilla/radzilla](https://github.com/gorizilla/radzilla)). Complete
rewrite; the alarm, dose, trend and RadiaCode logic was taken over from
RadZilla v1.4.1.

**Display and controls**
- Pages RATE, CPS, DOSE and SET; retro 5x7 dot-matrix font and 7-segment
  digits with ghost segments; drawn directly, only changed parts are redrawn.
- Values with 3 significant digits (mSv/h from 1000 µSv/h, kCPS from
  10 000 CPS); trend arrow behind the value (grey / orange / green).
- Logarithmic ring 0.01–10 µSv/h; colour of symbol, ring and value by alarm
  state.
- Status bar: clock, RadiaCode connection (symbol grey / yellow) and battery,
  Core2 battery with charge indicator.
- Double tap / swipe, buttons A / B / C; hold B 2 s = Bluetooth to the
  RadiaCode off / on.
- Radiation symbol held 2 s: CPS page = RadiaCode ticker on / off (only
  bit 1 of SOUND_CTRL 0x0520 is changed, verified by reading back), RATE
  page = restart the current RadiaCode spectrum ("SP RESET OK").
- Auto-dim after 90 s (brightness 130 / 30).

**Alarms and effects**
- HIGH 0.20 µSv/h, DANGER 10 µSv/h, DOSE 2.5 µSv in 15 min, Geiger
  pre-warning at 80 %; based only on the energy-compensated dose rate;
  no acknowledgement.
- Synced sound, LEDs and vibration with priorities
  DANGER > DOSE > HIGH > Geiger > heartbeat; alarms always first, LED runs
  are never lost when the program is busy.
- LED heartbeat every 20 s (10 s during an alarm) in the colour of the dose
  rate (green → yellow-green → yellow → orange → red).
- Optional short alarm signal on the RadiaCode itself (PLAY_SIGNAL 1 only).

**Log, WiFi, time, power**
- CSV log `Time;uSv/h;CPS;Alarm;Dose15` on the microSD card (fallback
  internal flash), fixed 5 s grid + a line at every alarm start / end,
  7 days / 25 MB; LOG button on the SET page; empty RadiaCode records are
  ignored.
- SET page: up to 5 WiFi networks (on-screen keyboard or phone setup page),
  time sync with the PTB atomic clock after the start, every 24 h and on
  request; German local time with automatic summer time.
- microSD on the shared SPI bus of the display (slot 2, 4 MHz).
- Splash with jingle, LED animation and vibration; autostart with
  `main.py` (hold A to skip).
- Battery level from voltage and current; automatic switch-off below 5 %;
  CPU at 160 MHz and lighter polling to save power.

**Tools**
- Hardware tests (display, SD card, sound, battery, Bluetooth), a read-only
  dump of the RadiaCode sound / light / alarm registers, sound generators.

The development builds 2.0.0-dev1 … dev19 are in the git history.

## Earlier versions

RadZilla v1.x for the Waveshare ESP32-S3-LCD-1.69:
[gorizilla/radzilla](https://github.com/gorizilla/radzilla).
