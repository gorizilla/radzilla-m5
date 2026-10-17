# rz_ble_test.py – Bluetooth connection test RadiaCode <-> M5Stack Core2 (UIFlow 2)
#
# RadZilla – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
# NOT part of RadZilla: run it by hand in Thonny (F5). Changes nothing on the
# device. Requires aioble in /flash/libs (mip.install("aioble", target="/flash/libs")).
#
# Finds the RadiaCode, connects, reads values every second for 30 s and shows
# dose rate, count rate, RadiaCode battery, serial number and firmware on the
# display and in the shell. Disconnect the RadiaCode phone app first.
#
# The protocol part below is the unchanged RadZilla radiacode.py (after the
# Python library cdump/radiacode, MIT – thanks to its authors).

# ======================= protocol (from RadZilla radiacode.py) =======================
import asyncio
import struct
import time

import aioble
import bluetooth

UUID_WRITE = bluetooth.UUID("e63215e6-7003-49d8-96b0-b024798fb901")
UUID_NOTIFY = bluetooth.UUID("e63215e7-7003-49d8-96b0-b024798fb901")

CMD_SET_EXCHANGE = 0x0007
CMD_GET_VERSION = 0x000A
CMD_WR_VIRT_SFR = 0x0825
CMD_RD_VIRT_STRING = 0x0826
VS_DATA_BUF = 0x0100
VS_SERIAL_NUMBER = 0x0008
VSFR_DEVICE_TIME = 0x0504
VSFR_PLAY_SIGNAL = 0x05E1  # write only; tested on RC-102 firmware, see below

CHUNK = 18                 # write chunk size (as in the Python library)

# Record sizes in the data buffer: (eid, gid) -> bytes after the 7-byte header
_REC_SIZE = {
    (0, 0): 15, (0, 1): 8, (0, 2): 16, (0, 3): 14, (0, 4): 16,
    (0, 5): 16, (0, 6): 6, (0, 7): 4, (0, 8): 6, (0, 9): 6,
}
# Records with a variable number of samples: (eid, gid) -> bytes per sample
_REC_SAMPLES = {(1, 1): 8, (1, 2): 16, (1, 3): 14}


async def find(name="", prefix="RadiaCode", scan_ms=5000):
    """Scan for the device. Returns (device, name) or (None, None)."""
    async with aioble.scan(scan_ms, interval_us=30000, window_us=30000,
                           active=True) as scanner:
        async for result in scanner:
            n = result.name()
            if not n:
                continue
            if (name and n == name) or (not name and n.startswith(prefix)):
                return result.device, n
    return None, None


class RadiaCode:
    def __init__(self, connection, wr, nt):
        self.conn = connection
        self.wr = wr
        self.nt = nt
        self.seq = 0
        self.rx = bytearray()

        # aioble keeps only the latest notification per characteristic, which
        # loses packets of multi-packet responses. Append every packet to our
        # own buffer instead.
        def _on_data(queue, event, data):
            self.rx.extend(data)
        nt._on_notify_indicate = _on_data

    @classmethod
    async def connect(cls, device):
        conn = await device.connect(timeout_ms=10000)
        try:
            await conn.exchange_mtu(247)
        except Exception:
            pass
        services = []
        async for svc in conn.services():
            services.append(svc)
        wr = nt = None
        for svc in services:
            if wr is None:
                wr = await svc.characteristic(UUID_WRITE)
            if nt is None:
                nt = await svc.characteristic(UUID_NOTIFY)
        if wr is None or nt is None:
            await conn.disconnect()
            raise OSError("RadiaCode service not found")
        rc = cls(conn, wr, nt)
        await nt.subscribe(notify=True)
        await rc._init()
        return rc

    def is_connected(self):
        return self.conn.is_connected()

    async def disconnect(self):
        try:
            await self.conn.disconnect()
        except Exception:
            pass

    # ---------- protocol ----------
    async def _wait_rx(self, n, deadline):
        """Wait until at least n bytes have been received."""
        while len(self.rx) < n:
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                raise asyncio.TimeoutError()
            await asyncio.sleep_ms(5)

    async def execute(self, cmd, args=b"", timeout_ms=10000):
        """Send a command and return the response payload."""
        header = struct.pack("<HBB", cmd, 0, 0x80 + self.seq)
        self.seq = (self.seq + 1) % 32
        req = header + args
        full = struct.pack("<I", len(req)) + req

        self.rx = bytearray()               # drop leftovers
        for pos in range(0, len(full), CHUNK):
            await self.wr.write(full[pos:pos + CHUNK])

        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        size = None
        try:
            await self._wait_rx(4, deadline)
            size = struct.unpack("<i", self.rx[:4])[0]
            await self._wait_rx(4 + size, deadline)
        except asyncio.TimeoutError:
            print("RadiaCode: timeout on command 0x%04X, expected %s, got %d bytes"
                  % (cmd, "?" if size is None else 4 + size, len(self.rx)))
            raise
        buf = bytes(self.rx[4:4 + size])
        if buf[:4] != header:
            raise OSError("response does not match request")
        return buf[4:]

    async def _init(self):
        await self.execute(CMD_SET_EXCHANGE, b"\x01\xff\x12\xff")
        await self.execute(CMD_WR_VIRT_SFR,
                           struct.pack("<II", VSFR_DEVICE_TIME, 0))

    async def serial_number(self):
        """Device serial number as text, e.g. "RC-102-012345" (read only)."""
        r = await self.execute(CMD_RD_VIRT_STRING,
                               struct.pack("<I", VS_SERIAL_NUMBER))
        retcode, flen = struct.unpack("<II", r[:8])
        if retcode != 1:
            raise OSError("retcode %d" % retcode)
        return bytes(r[8:8 + flen]).decode().strip("\x00").strip()

    async def fw_version(self):
        """Firmware version of the device as text, e.g. "4.14" (read only)."""
        r = await self.execute(CMD_GET_VERSION)
        pos = 4 + 1 + r[4]                     # skip boot version and its date
        minor, major = struct.unpack_from("<HH", r, pos)
        return "%d.%d" % (major, minor)

    async def play_signal(self):
        """Let the RadiaCode play its short alarm: 3 short beeps, then
        vibration; it ends by itself. Nothing is changed in the device.

        Only value 1 is ever sent. Tested values of PLAY_SIGNAL (RC-102):
          1     short alarm (used here)
          2     loud permanent alarm that cannot be stopped by writing 0,
                only by switching the device off -> never send it
          3..8  rejected by the device
        """
        r = await self.execute(CMD_WR_VIRT_SFR,
                               struct.pack("<II", VSFR_PLAY_SIGNAL, 1))
        return struct.unpack("<I", r[:4])[0] == 1

    async def read_data(self):
        """Read the data buffer. Returns a dict with the latest values:
        cps, dose_raw, cps_err, dose_err (%), batt (%), temp (°C)."""
        r = await self.execute(CMD_RD_VIRT_STRING,
                               struct.pack("<I", VS_DATA_BUF))
        retcode, flen = struct.unpack("<II", r[:8])
        if retcode != 1:
            raise OSError("retcode %d" % retcode)
        return parse_databuf(r[8:8 + flen])


def parse_databuf(data):
    """Decode the records of the data buffer; keep the latest values."""
    out = {}
    pos = 0
    n = len(data)
    while n - pos >= 7:
        seq, eid, gid, ts = struct.unpack_from("<BBBi", data, pos)
        pos += 7
        key = (eid, gid)
        if key == (0, 0):                              # real-time values
            cps, dose, cps_e, dose_e, flags, rtf = \
                struct.unpack_from("<ffHHHB", data, pos)
            out["cps"] = cps
            out["dose_raw"] = dose
            out["cps_err"] = cps_e / 10
            out["dose_err"] = dose_e / 10
        elif key == (0, 3):                            # rare data
            dur, dose, temp, charge, flags = \
                struct.unpack_from("<IfHHH", data, pos)
            out["temp"] = (temp - 2000) / 100
            out["batt"] = charge / 100
        if key in _REC_SIZE:
            pos += _REC_SIZE[key]
        elif key in _REC_SAMPLES:
            samples, _ = struct.unpack_from("<HI", data, pos)
            pos += 6 + samples * _REC_SAMPLES[key]
        else:
            break                                      # unknown -> ignore rest
    return out


# ======================= test ==========================================================
import M5
from M5 import Lcd

RC_DOSE_FACTOR = 10000.0       # raw dose rate -> µSv/h
TEST_SECONDS = 30
POLL_MS = 1000

Y = 0xFFC800
WH = 0xFFFFFF
GR = 0x8C8C8C


def show(lines, title="BLE TEST", col=WH):
    try:
        Lcd.fillScreen(0x000000)
        Lcd.setTextSize(2)
        Lcd.setTextColor(Y, 0x000000)
        Lcd.drawString(title, 10, 10)
        Lcd.setTextColor(col, 0x000000)
        y = 50
        for ln in lines:
            Lcd.drawString(str(ln)[:26], 10, y)
            y += 26
    except Exception as e:
        print("display:", repr(e))


async def run():
    summary = []
    show(["searching RadiaCode ...", "(phone app disconnected?)"])
    print("Searching RadiaCode ...")
    dev, name = await find("", "RadiaCode", 8000)
    if dev is None:
        show(["no RadiaCode found"], col=0xFF4040)
        print("FAIL no RadiaCode found")
        return ["FAIL scan  no RadiaCode found"]
    print("Found:", name)
    show(["found:", name, "connecting ..."])
    t0 = time.ticks_ms()
    try:
        rc = await RadiaCode.connect(dev)
    except Exception as e:
        show(["connect failed", repr(e)], col=0xFF4040)
        return ["FAIL connect %r" % e]
    summary.append("OK   connect %s (%d ms)" % (name, time.ticks_diff(time.ticks_ms(), t0)))
    sn = fw = "?"
    try:
        r = await rc.execute(CMD_RD_VIRT_STRING, struct.pack("<I", 0x0008))
        _, flen = struct.unpack("<II", r[:8])
        sn = bytes(r[8:8 + flen]).decode().strip("\x00").strip()
    except Exception as e:
        sn = "error %r" % e
    try:
        r = await rc.execute(0x000A)
        pos = 4 + 1 + r[4]
        minor, major = struct.unpack_from("<HH", r, pos)
        fw = "%d.%d" % (major, minor)
    except Exception as e:
        fw = "error %r" % e
    summary.append("OK   info    SN %s, FW %s" % (sn, fw))
    print("SN", sn, "FW", fw)
    reads = errors = 0
    usv = cps = batt = None
    t_end = time.ticks_add(time.ticks_ms(), TEST_SECONDS * 1000)
    while time.ticks_diff(t_end, time.ticks_ms()) > 0 and rc.is_connected():
        try:
            d = await rc.read_data()
            reads += 1
            if "cps" in d:
                cps = d["cps"]
                usv = d["dose_raw"] * RC_DOSE_FACTOR
            if "batt" in d:
                batt = d["batt"]
            left = time.ticks_diff(t_end, time.ticks_ms()) // 1000
            line = "%s uSv/h  %s CPS  batt %s" % (
                "--" if usv is None else "%.2f" % usv,
                "--" if cps is None else "%.2f" % cps,
                "--" if batt is None else "%d%%" % batt)
            print(line)
            show(["uSv/h  " + ("--" if usv is None else "%.2f" % usv),
                  "CPS    " + ("--" if cps is None else "%.2f" % cps),
                  "RC bat " + ("--" if batt is None else "%d %%" % batt),
                  "SN " + sn, "FW " + fw, "%d s left" % left], title="RADIACODE LIVE")
        except Exception as e:
            errors += 1
            print("read error:", repr(e))
        await asyncio.sleep_ms(POLL_MS)
    connected = rc.is_connected()
    await rc.disconnect()
    summary.append("%s reads   %d ok, %d errors, still connected: %s" % (
        "OK  " if reads and not errors else "FAIL", reads, errors, connected))
    summary.append("     last    %s uSv/h, %s CPS, batt %s %%" % (
        "--" if usv is None else "%.2f" % usv, "--" if cps is None else "%.2f" % cps, batt))
    return summary


def main():
    M5.begin()
    try:
        summary = asyncio.run(run())
    except Exception as e:
        summary = ["FAIL crash %r" % e]
    finally:
        asyncio.new_event_loop()
    print("\n===== RZ BLE TEST SUMMARY =====")
    for ln in summary:
        print(ln)
    print("===============================")
    show(["see Thonny shell", "for the summary"], title="DONE")


main()
