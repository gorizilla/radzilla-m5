# Setup (stage 1)

RadZilla M5 runs on the UIFlow 2 firmware of the M5Stack Core2. In stage 1
it is started by hand from Thonny – nothing is changed on the device
(boot.py, main.py and the boot option stay as they are).

## 1. Requirements (once)

1. Core2 with **UIFlow 2.5.3** firmware.
2. **aioble** (Bluetooth library) – in the Thonny shell:
   ```python
   import mip
   mip.install("aioble", target="/flash/libs")
   ```
   (needs a WiFi connection of the Core2, e.g. via the UIFlow menu)
3. Optional: microSD card formatted as **FAT32 (MS-DOS FAT, MBR)** – exFAT
   is not supported.

## 2. Upload

1. In Thonny: *View → Files*. Upper half = computer, lower half = Core2.
2. The lower half shows the Core2. Thonny often shows the content of
   `/flash` directly, without the folder name (you see `boot.py`, `main.py`,
   `libs`) – that is the right place.
3. On the computer open the project folder `device/`, right-click the
   folder **`radzilla`** → *Upload to /flash*.
4. On a later update upload the folder again (overwrite).

## 3. Start

1. Close the RadiaCode phone app (only one Bluetooth connection at a time).
2. Open `device/rz_start.py` in Thonny, press **Stop**, then **F5**.
3. Stop with the **Stop** button – the log buffer is saved.

## Controls

| Action | Function |
|---|---|
| double tap on the display | next page |
| swipe left / right | next / previous page |
| button A / C | previous / next page |
| button B | DOSE page |
| hold button B (2 s) | Bluetooth to the RadiaCode off / on – while off: no readings, no alarms, no log; always on after a restart |

## Log files

`/sd/RadZilla/logs/rc_YYYY-MM-DD_HHMM.csv`, without SD card
`/flash/RadZilla/logs/`. Semicolon + decimal comma – opens directly in
German Numbers / Excel:

```
Time;uSv/h;CPS;Alarm;Dose15;Lat;Lon;Alt
2026-10-17 14:01:03;0,12;5,41;0;0,03;;;
```

Alarm: 0 none, 1 HIGH, 2 DANGER, 3 DOSE. Lat/Lon/Alt stay empty until GPS
is supported. Files older than 7 days are deleted automatically.

All settings: `device/radzilla/config.py`.
