# Notice

## ⚠️ Experimental software – read before use

RadZilla M5 is an **experimental hobby project**. It is **not** a certified
radiation measuring or safety device and must **not** be relied upon for
radiation protection, safety decisions, medical purposes or any situation in
which a failure could cause harm.

- Readings, colours, trends and alarms shown by RadZilla M5 are derived from
  data received over Bluetooth and may be **delayed, wrong or missing**
  (e.g. connection loss, software errors, empty battery, wrong configuration).
- The dose-rate conversion factor and the alarm thresholds are user settings
  and have **not** been validated or calibrated.
- Always use the RadiaCode device itself and the manufacturer's official app
  as the authoritative source, and follow applicable radiation-protection
  rules.

**No warranty, no liability.** The software is provided "as is", without
warranty of any kind, express or implied. To the maximum extent permitted by
law, the author accepts no liability for any direct or indirect damage
arising from the use, misuse or inability to use this software or the
hardware it controls. Use at your own risk. Mandatory statutory liability
(e.g. for intent or gross negligence, where it cannot be excluded by law)
remains unaffected.

## What RadZilla M5 changes on the RadiaCode

RadZilla M5 reads the RadiaCode values over Bluetooth. It writes to the
RadiaCode **only** in these cases:

| Action | Trigger | Register / command |
|---|---|---|
| Short alarm signal of the RadiaCode (3 beeps + vibration) | HIGH / DANGER alarm starts (`RC_SIGNAL_ON`) | `PLAY_SIGNAL` 0x05E1, value **1** only |
| Ticker (clicks) on / off | radiation symbol held 2 s on the CPS page | `SOUND_CTRL` 0x0520, **only bit 1** (read – change – write – read back) |
| Restart the current spectrum | radiation symbol held 2 s on the RATE page | `WR_VIRT_STRING` 0x0827, `SPECTRUM` 0x0200 |
| Start of the data session (handshake, as in the library) | every connection | `DEVICE_TIME` 0x0504 = 0 |

The spectrum reset deletes the current spectrum in the RadiaCode – save
spectra you want to keep in the official app first. `PLAY_SIGNAL` value 2
is never sent (it starts a permanent alarm on the RC-102 that can only be
stopped by switching the device off). Register meanings were checked on a
RadiaCode-102 with firmware 4.14; other models or firmware versions may
behave differently.

## No affiliation, trademarks

RadZilla M5 is an independent project. It is **not affiliated with, endorsed
by or supported by** the manufacturer of RadiaCode devices, by M5Stack, by
Espressif or by the MicroPython project.

"RadiaCode", "M5Stack", "Core2", "UIFlow", "ESP32" and other product names
are trademarks of their respective owners and are used here only to describe
compatibility.

## Acknowledgements

| Project | Used for | License |
|---|---|---|
| [cdump/radiacode](https://github.com/cdump/radiacode) | The RadiaCode Bluetooth protocol implemented in `device/radzilla/core/radiacode.py` follows this Python library (command IDs, framing, data-buffer record layout). No code was copied; the protocol was re-implemented for MicroPython. | MIT |
| [MicroPython](https://micropython.org) / [UIFlow 2](https://uiflow2.m5stack.com) | Firmware running on the device | MIT / M5Stack |
| [aioble](https://github.com/micropython/micropython-lib/tree/master/micropython/bluetooth/aioble) (micropython-lib) | Bluetooth Low Energy library, installed separately on the device via `mip` | MIT |

Third-party software is not included in this repository and is not covered by
RadZilla's license. Each component keeps its own license.

## License

RadZilla M5: **CC BY-NC-SA 4.0**, commercial licenses only by the author;
showing RadZilla M5 in videos and articles is allowed. See
[LICENSE.md](LICENSE.md).
