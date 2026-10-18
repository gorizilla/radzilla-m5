# RadZilla M5

**External display for RadiaCode radiation detectors on M5Stack hardware** –
a MicroPython (UIFlow 2) program that connects to a RadiaCode 10x via
Bluetooth and shows dose rate, count rate, dose and alarms on the M5Stack
Core2, with a CSV log on the microSD card.

> ⚠️ **Experimental hobby project – not a safety device.**
> Readings and alarms may be delayed, wrong or missing. Provided without any
> warranty or liability – see [NOTICE.md](NOTICE.md).

RadZilla M5 is the successor of RadZilla for the Waveshare ESP32-S3-LCD-1.69
and an independent project, not affiliated with the manufacturer of
RadiaCode devices or with M5Stack.

**Status: v2.0.0 in development (stage 3 done).**

## Features (stage 1)

- **Pages** RATE (µSv/h), CPS, DOSE and SET (placeholder) in a retro
  dot-matrix / 7-segment design.
- **Colour by alarm state** – radiation symbol, ring and value:
  green normal, yellow HIGH, red DANGER, grey no data.
- **Alarms** HIGH, DANGER and DOSE (2.5 µSv in 15 min), no acknowledgement
  needed; the RadiaCode itself can beep on HIGH / DANGER.
- **DOSE page**: 15-min dose (green → yellow → orange → red) and extra dose
  today (blue).
- **Controls**: double tap or swipe on the display, buttons A / C = page,
  B = DOSE page, hold B = Bluetooth off / on.
- **Auto-dim** after 90 s, wakes on touch, buttons or an alarm.
- **Counter clicks** on the CPS page (hold the radiation symbol 2 s), 1:1 up to 50 CPS for source finding, louder and harder above, a subtle scream above DANGER.
- **CSV log** on the microSD card (fallback: internal flash), 7 days; on / off with `LOG` on the SET page.
- **Splash**, synced **sirens / LEDs / vibration**, **autostart**.
- **SET page**: WiFi via on-screen keyboard or phone, time sync with the
  PTB atomic clock.

Planned: GPS (stage 4), documentation and license (stage 5), M5Stack
StopWatch support.

## Hardware

- M5Stack Core2 (tested: v1.0 with M5GO Bottom2) with UIFlow 2.5.3
- RadiaCode 10x (tested: RC-102, firmware 4.14)
- microSD card, FAT32 (optional)

## Project layout

```
device/                files for the M5Stack
  rz_start.py          start file (later main.py)
  radzilla/
    config.py          all settings
    app.py             main program
    core/              RadiaCode protocol, alarms, dose, trend, log (no hardware)
    devices/core2.py   everything Core2-specific
    ui/                drawing helpers and page layouts
tools/                 hardware and design tests
docs/                  documentation
```

Setup: [docs/SETUP.md](docs/SETUP.md)

## License

Copyright © 2026 Shimizilla. License to be finalised – see
[LICENSE.md](LICENSE.md).
