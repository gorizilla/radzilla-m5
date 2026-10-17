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

## 3. Start by hand (Thonny)

1. Close the RadiaCode phone app (only one Bluetooth connection at a time).
2. Open `device/rz_start.py` in Thonny, press **Stop**, then **F5**.
3. Stop with the **Stop** button – the log buffer is saved.

## 4. Autostart after switching on

1. Boot option 0 (UIFlow then runs only `main.py`, no UIFlow menu) – in the
   Thonny shell:
   ```python
   import esp32; n=esp32.NVS("uiflow"); n.set_u8("boot_option",0); n.commit()
   ```
2. On the Core2 rename the old `main.py` to `main_uiflow.py` (backup).
3. Upload `device/main.py` to `/flash`.
4. Switch off and on: splash, then RadZilla.

- **Skip once:** hold button **A** while switching on – RadZilla does not
  start and Thonny can connect normally.
- **Back to UIFlow:** same command as in step 1 with `1` instead of `0`,
  and restore `main_uiflow.py` as `main.py`.

## Controls

| Action | Function |
|---|---|
| double tap on the display | next page |
| swipe right / left | next / previous page |
| button A / C | previous / next page |
| button B | DOSE page |
| hold button B (2 s) | Bluetooth to the RadiaCode off / on – while off: no readings, no alarms, no log; always on after a restart |

## SET page – WiFi and time

The WiFi is only used for the time sync (PTB atomic clock). After a sync the
clock keeps running on its battery, also without WiFi. Without a valid time
the clock shows `--:--` and nothing is logged.

| Button | Function |
|---|---|
| `+WIFI` | scan, tap a network, enter the password on the keyboard, `OK` |
| `PHONE` | connect the phone to the WiFi **RadZilla-Setup** with the password shown, open **http://192.168.4.1**, choose the network, enter the password, `SAVE` |
| `SYNC` | sync the time now |
| `LOG` | CSV log on (green) / off (grey), the footer shows `LOG SD` / `LOG OFF` – not stored, **on after every start** |

Up to 5 networks are stored in `/flash/radzilla/wifi.json` (newest first,
the strongest one in range is used). On the first start the network saved
in UIFlow is taken over. The time is synced after the start and every 24 h.

### WiFi from the Thonny shell (alternative)

Stop RadZilla first (hold **A** while switching on, or **Stop** in Thonny).
Replace the placeholders – never put real passwords into git or a chat.

Set the list (overwrites all stored networks):
```python
import json; open("/flash/radzilla/wifi.json","w").write(json.dumps([{"ssid":"MY_WIFI","pw":"MY_PASSWORD"}]))
```

Two networks:
```python
import json; open("/flash/radzilla/wifi.json","w").write(json.dumps([{"ssid":"WIFI_1","pw":"PASSWORD_1"},{"ssid":"WIFI_2","pw":"PASSWORD_2"}]))
```

Show the stored network names (without passwords):
```python
import json; print([n["ssid"] for n in json.load(open("/flash/radzilla/wifi.json"))])
```

## Log files

The log is on after every start; switch it off with `LOG` on the SET page.
A line every 5 s (`LOG_INTERVAL_S`) and immediately when an alarm starts or
ends; written to the card once per minute.

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
