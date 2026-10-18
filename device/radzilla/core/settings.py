# settings.py – settings changed on the device that survive a restart.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
#   /flash/radzilla/settings.json   {"click": true}
#
# Not in git. Missing or damaged file -> defaults from config.py.
import json

PATH = "/flash/radzilla/settings.json"


def load(cfg):
    d = {"click": cfg.CLICK_ON}
    try:
        with open(PATH) as f:
            d.update(json.load(f))
    except OSError:
        pass
    except (ValueError, TypeError) as e:
        print("settings.json damaged:", repr(e))
    return d


def save(d):
    try:
        with open(PATH, "w") as f:
            json.dump(d, f)
    except OSError as e:
        print("settings.json:", repr(e))
