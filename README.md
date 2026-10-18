# RadZilla M5

**External display for RadiaCode radiation detectors on the M5Stack Core2** –
a MicroPython (UIFlow 2) program that connects to a RadiaCode 10x over
Bluetooth and shows dose rate, count rate, dose and alarms with sound, LEDs
and vibration, and writes a CSV log to the microSD card.

> ⚠️ **Experimental hobby project – not a safety device.**
> Readings and alarms may be delayed, wrong or missing. Provided without any
> warranty or liability – see [NOTICE.md](NOTICE.md).

<!-- Photos follow – see docs/images/README.md -->

**Version 2.0.0** · Copyright © 2026 Shimizilla · [CC BY-NC-SA 4.0](LICENSE.md)

## Features

- **Pages** RATE (µSv/h), CPS, DOSE and SET in a retro dot-matrix /
  7-segment design; values with 3 significant digits and a trend arrow.
- **Logarithmic ring** 0.01–10 µSv/h, colours by alarm state: green normal,
  yellow HIGH, red DANGER, grey no data.
- **Alarms** based on the energy-compensated dose rate of the RadiaCode:
  HIGH (0.20 µSv/h), DANGER (10 µSv/h) and DOSE (2.5 µSv in 15 min), with
  synced sirens, LED effects and vibration; optional short alarm signal on
  the RadiaCode itself. No acknowledgement needed.
- **DOSE page**: 15-min dose and extra dose today.
- **LED heartbeat** every 20 s (10 s during an alarm) in the colour of the
  dose rate.
- **Radiation symbol held 2 s**: CPS page switches the RadiaCode **ticker**
  on / off, RATE page restarts the RadiaCode **spectrum**.
- **CSV log** on the microSD card (fallback: internal flash), 5 s grid,
  7 days, opens directly in German Numbers / Excel.
- **SET page**: WiFi via on-screen keyboard or phone, time sync with the
  PTB atomic clock (German local time with summer time), log on / off.
- **Splash** with jingle, LED animation and vibration; **autostart**;
  auto-dim; automatic switch-off when the battery is empty.
- Controls: double tap / swipe, buttons A / B / C, hold B = Bluetooth
  off / on.

All settings are in [`device/radzilla/config.py`](device/radzilla/config.py).

## Hardware

- **M5Stack Core2** with **M5GO Bottom2** (LEDs) – tested: Core2 v1.0,
  firmware **UIFlow 2.5.3**
- **RadiaCode 10x** – tested: RadiaCode-102, firmware 4.14
- microSD card, FAT32 (optional, for the log)

## Why M5Stack instead of Waveshare?

RadZilla started on the **Waveshare ESP32-S3-LCD-1.69** (project
[gorizilla/radzilla](https://github.com/gorizilla/radzilla), stays at
v1.2). When the display of that board **cracked**, RadZilla moved to the
**M5Stack Core2**. The Core2 comes as a finished device in a robust case and
brings everything RadZilla needs on board: a larger touch display,
speaker, vibration motor, battery with charging and power management,
real-time clock and a microSD slot – plus the LED bars of the M5GO Bottom2.
That made the new features of version 2 possible (touch controls, sirens,
LED effects, log on SD card, battery switch-off). The code was rewritten
for this; it is modular so that other M5Stack devices (e.g. the StopWatch)
can follow.

## Quick start

1. Core2 with UIFlow 2.5.3; install `aioble` once (see setup).
2. Upload the folder `device/radzilla` to `/flash` with Thonny.
3. Close the RadiaCode app, start `device/rz_start.py` – or install
   `device/main.py` for autostart.

Full guide: **[docs/SETUP.md](docs/SETUP.md)**

## Project layout

```
device/                  files for the M5Stack
  main.py                autostart (hold A while switching on = skip)
  rz_start.py            start by hand from Thonny
  radzilla/
    config.py            all settings
    app.py               main program
    fx.py                sound / LED / vibration effects
    core/                RadiaCode protocol, alarms, dose, trend, log, WiFi, time (no hardware)
    devices/core2.py     everything Core2-specific
    ui/                  drawing, pages, splash, dialogs
    sounds/              WAV files (jingle, sirens)
tools/                   hardware tests, register dump, sound generators
docs/                    setup guide, images
```

## License

Copyright © 2026 Shimizilla.
[CC BY-NC-SA 4.0](LICENSE.md) – free for non-commercial use with credit and
share-alike; commercial use only with the author's permission; videos and
articles about RadZilla M5 are welcome. Contributions:
[CONTRIBUTING.md](CONTRIBUTING.md). Third-party notes and the RadiaCode
protocol credits (cdump/radiacode, MIT): [NOTICE.md](NOTICE.md).
