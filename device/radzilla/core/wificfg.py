# wificfg.py – stored WiFi networks (max. WIFI_MAX), never in git.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
#   /flash/radzilla/wifi.json   [{"ssid": "...", "pw": "..."}, ...]
#
# On the first start (no wifi.json yet) the network saved by UIFlow
# (NVS "uiflow", keys ssid0 / pswd0) is taken over once.
import json

PATH = "/flash/radzilla/wifi.json"


def load():
    """List of (ssid, password)."""
    try:
        with open(PATH) as f:
            return [(n["ssid"], n.get("pw", "")) for n in json.load(f)]
    except OSError:
        nets = _from_uiflow()
        if nets:
            save(nets)
        return nets
    except (ValueError, KeyError, TypeError) as e:
        print("wifi.json damaged:", repr(e))
        return []


def save(nets):
    try:
        with open(PATH, "w") as f:
            json.dump([{"ssid": s, "pw": p} for s, p in nets], f)
    except OSError as e:
        print("wifi.json:", repr(e))


def add(nets, ssid, pw, max_n):
    """Add or update a network (newest first); the oldest drops out."""
    nets = [(s, p) for s, p in nets if s != ssid]
    nets.insert(0, (ssid, pw))
    nets = nets[:max_n]
    save(nets)
    return nets


def remove(nets, ssid):
    nets = [(s, p) for s, p in nets if s != ssid]
    save(nets)
    return nets


def _from_uiflow():
    """Network saved in the UIFlow settings (UIFlow's NVS has get_str)."""
    try:
        import esp32
        nvs = esp32.NVS("uiflow")
        ssid = nvs.get_str("ssid0")
        pw = nvs.get_str("pswd0")
    except Exception as e:
        print("wifi: no UIFlow network (%r)" % e)
        return []
    if ssid:
        print("wifi: taken over from UIFlow:", ssid)
        return [(ssid, pw or "")]
    return []
