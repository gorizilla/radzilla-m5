# logger.py – CSV log of the readings on the microSD card (fallback: flash).
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
#   /sd/RadZilla/logs/rc_2026-10-17_1401.csv
#     Time;uSv/h;CPS;Alarm;Dose15;Lat;Lon;Alt
#     2026-10-17 14:01:03;0,12;8,53;0;0,03;;;
#
#   Alarm  0 none, 1 HIGH, 2 DANGER, 3 DOSE (state, DANGER > DOSE > HIGH)
#   Dose15 dose in µSv within the dose window
#   Lat/Lon/Alt GPS position (empty until the GPS unit is supported)
#
# * new file per start and after LOG_FILE_H hours of run time
# * buffered in RAM, written every LOG_FLUSH_S seconds
# * clean-up: files whose last entry is older than LOG_MAX_AGE_H are deleted,
#   then the oldest until count / total size / free space fit; the current
#   file is never deleted. If the limits cannot be met, logging stops ("FULL").
import os
import time

HEADER = "Time;uSv/h;CPS;Alarm;Dose15;Lat;Lon;Alt\n"


def days_from_civil(y, m, d):
    """Days since 1970-01-01 (proleptic Gregorian calendar)."""
    y -= m <= 2
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    return era * 146097 + doe - 719468


def _secs(t):
    return days_from_civil(t[0], t[1], t[2]) * 86400 + t[3] * 3600 + t[4] * 60 + t[5]


def _parse_ts(s):
    try:
        return (int(s[0:4]), int(s[5:7]), int(s[8:10]),
                int(s[11:13]), int(s[14:16]), int(s[17:19]))
    except (ValueError, IndexError):
        return None


def _parse_name(name):
    try:
        return (int(name[3:7]), int(name[8:10]), int(name[11:13]),
                int(name[14:16]), int(name[16:18]), 0)
    except (ValueError, IndexError):
        return None


def _num(v):
    return ("%.2f" % v).replace(".", ",")


def _opt(v, fmt):
    return "" if v is None else (fmt % v).replace(".", ",")


def _makedirs(path):
    cur = ""
    for part in path.strip("/").split("/"):
        cur += "/" + part
        try:
            os.stat(cur)
        except OSError:
            os.mkdir(cur)


class Logger:
    def __init__(self, cfg, use_sd):
        c = self.c = cfg
        self.on_sd = use_sd
        self.dir = c.LOG_SD_DIR if use_sd else c.LOG_INT_DIR
        self.max_kb = c.LOG_MAX_TOTAL_KB if use_sd else c.LOG_INT_MAX_TOTAL_KB
        self.min_free = c.LOG_MIN_FREE_KB if use_sd else c.LOG_INT_MIN_FREE_KB
        self.path = None
        self.start_s = None
        self.buf = []
        self.last_flush = time.ticks_ms()
        self.last_check = None
        self.full = False
        self.error = None

    def status(self, time_valid):
        """Short text for the footer: (text, ok)."""
        if not self.c.LOG_ON:
            return "LOG OFF", True
        if self.full:
            return "LOG FULL", False
        if self.error:
            return "LOG ERR", False
        if not time_valid:
            return "NO TIME", False
        return ("LOG SD" if self.on_sd else "LOG INT"), True

    # ---------- file system ----------
    def _files(self):
        try:
            names = [n for n in os.listdir(self.dir)
                     if n.startswith("rc_") and n.endswith(".csv")]
        except OSError:
            return []
        names.sort()
        return [self.dir + "/" + n for n in names]

    @staticmethod
    def _size(path):
        try:
            return os.stat(path)[6]
        except OSError:
            return 0

    def _free_kb(self):
        s = os.statvfs(self.dir)
        return s[0] * s[3] // 1024

    def _last_entry_s(self, path):
        try:
            size = self._size(path)
            with open(path, "rb") as f:
                if size > 120:
                    f.seek(size - 120)
                tail = f.read().decode()
            for line in reversed(tail.split("\n")):
                t = _parse_ts(line)
                if t:
                    return _secs(t)
        except (OSError, UnicodeError):
            pass
        t = _parse_name(path.rsplit("/", 1)[-1])
        return _secs(t) if t else None

    def _delete(self, path):
        try:
            os.remove(path)
            print("Log deleted:", path)
        except OSError:
            pass

    def cleanup(self, now_s):
        c = self.c
        files = [p for p in self._files() if p != self.path]
        keep = []
        for p in files:                              # 1. too old
            last = self._last_entry_s(p)
            if last is not None and now_s - last > c.LOG_MAX_AGE_H * 3600:
                self._delete(p)
            else:
                keep.append(p)
        files = keep
        cur_kb = self._size(self.path) if self.path else 0
        cur = 1 if self.path else 0
        while files:                                 # 2. count / size / free space
            total_kb = (sum(self._size(p) for p in files) + cur_kb) // 1024
            if (len(files) + cur <= c.LOG_MAX_FILES and total_kb <= self.max_kb
                    and self._free_kb() >= self.min_free):
                break
            self._delete(files.pop(0))
        total_kb = (sum(self._size(p) for p in files) + cur_kb) // 1024
        self.full = self._free_kb() < self.min_free or total_kb > self.max_kb

    def _new_file(self, t):
        _makedirs(self.dir)
        base = "%s/rc_%04d-%02d-%02d_%02d%02d" % (self.dir, t[0], t[1], t[2], t[3], t[4])
        path = base + ".csv"
        n = 2
        while True:
            try:
                os.stat(path)
                path = "%s_%d.csv" % (base, n)
                n += 1
            except OSError:
                break
        with open(path, "w") as f:
            f.write(HEADER)
        self.path = path
        self.start_s = _secs(t)
        print("Log created:", path)

    # ---------- writing ----------
    def add(self, t, usv, cps, alarm, dose, lat=None, lon=None, alt=None):
        if not self.c.LOG_ON or self.full or self.error:
            return
        now_s = _secs(t)
        try:
            if self.path is None:
                _makedirs(self.dir)
                self.cleanup(now_s)
                self.last_check = time.ticks_ms()
                if self.full:
                    return
                self._new_file(t)
            elif now_s - self.start_s >= self.c.LOG_FILE_H * 3600:
                self.flush()
                self._new_file(t)
            self.buf.append("%04d-%02d-%02d %02d:%02d:%02d;%s;%s;%d;%s;%s;%s;%s\n" % (
                t[0], t[1], t[2], t[3], t[4], t[5], _num(usv), _num(cps), alarm,
                _num(dose), _opt(lat, "%.6f"), _opt(lon, "%.6f"), _opt(alt, "%.1f")))
            now = time.ticks_ms()
            if time.ticks_diff(now, self.last_flush) >= self.c.LOG_FLUSH_S * 1000:
                self.flush()
            if time.ticks_diff(now, self.last_check) >= self.c.LOG_CHECK_S * 1000:
                self.last_check = now
                self.cleanup(now_s)
        except OSError as e:
            self.error = e
            print("Log error:", repr(e))

    def flush(self):
        self.last_flush = time.ticks_ms()
        if not self.buf or not self.path:
            return
        try:
            if self._free_kb() < self.min_free:
                self.full = True
                self.buf = []
                print("Log full")
                return
            with open(self.path, "a") as f:
                for line in self.buf:
                    f.write(line)
            self.buf = []
        except OSError as e:
            self.error = e
            print("Log error:", repr(e))
