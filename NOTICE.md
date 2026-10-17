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

## License (to be finalised)

Planned: **CC BY-NC-SA 4.0** with commercial licences only by the author on
request; presenting RadZilla in videos and articles is not considered
commercial use. See [LICENSE.md](LICENSE.md).
