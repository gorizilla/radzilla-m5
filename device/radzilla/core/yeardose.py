# yeardose.py – total dose of the calendar year, kept across restarts.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
#   /flash/radzilla/yeardose.json   {"year": 2026, "usv": 441.2}
#
# Counts the whole measured dose (incl. background) while connected to the
# RadiaCode. Saved every YEAR_SAVE_S and when RadZilla stops / switches off;
# reset when the (valid) clock shows a new year. Not in git.
import json

PATH = "/flash/radzilla/yeardose.json"


def load():
    """(year or None, µSv)."""
    try:
        with open(PATH) as f:
            d = json.load(f)
        return d.get("year"), float(d.get("usv", 0.0))
    except OSError:
        return None, 0.0
    except (ValueError, TypeError) as e:
        print("yeardose.json damaged:", repr(e))
        return None, 0.0


def save(year, usv):
    try:
        with open(PATH, "w") as f:
            json.dump({"year": year, "usv": round(usv, 4)}, f)
    except OSError as e:
        print("yeardose.json:", repr(e))
