# radiacode.py – Bluetooth LE connection to RadiaCode 10x devices.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# Protocol re-implemented for MicroPython following the Python library
# cdump/radiacode (https://github.com/cdump/radiacode, MIT license).
# Thanks to its authors! No code was copied.
#
# Requires aioble on the board (install once: mip.install("aioble", target="/flash/libs")).
#
# Request frame:  <u32 length> <u16 command> <u8 0> <u8 0x80+seq> <args>
# Response frame: <u32 length> <same 4-byte header> <payload>
# Requests are written in chunks of 18 bytes, responses arrive as several
# notifications and are reassembled using the length prefix.
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
CMD_WR_VIRT_STRING = 0x0827
CMD_RD_VIRT_SFR_BATCH = 0x082A
VS_DATA_BUF = 0x0100
VS_SERIAL_NUMBER = 0x0008
VSFR_DEVICE_TIME = 0x0504
VSFR_PLAY_SIGNAL = 0x05E1  # write only; tested on RC-102 firmware, see below
VSFR_SOUND_CTRL = 0x0520   # bit 1 = ticker (clicks), tested RC-102 FW 4.14: 0x0303 on / 0x0301 off
VS_SPECTRUM = 0x0200       # current spectrum (reset = write with length 0)
TICKER_BIT = 0x02

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

    # ---- the only settings RadZilla changes (on request of the user) ----
    async def read_vsfr(self, reg):
        """Raw 32-bit value of one register, or None."""
        r = await self.execute(CMD_RD_VIRT_SFR_BATCH, struct.pack("<II", 1, reg))
        if len(r) < 8:
            return None
        flags, value = struct.unpack("<II", r[:8])
        return value if flags & 1 else None

    async def toggle_ticker(self):
        """Switch only the ticker (clicks) of the RadiaCode on / off: read
        SOUND_CTRL, flip bit 1, write, read back. All other bits (alarm
        sounds, buttons) stay exactly as read. Nothing is written if the
        read fails. Returns True when the new value was verified."""
        v = await self.read_vsfr(VSFR_SOUND_CTRL)
        if v is None:
            return False
        new = v ^ TICKER_BIT
        r = await self.execute(CMD_WR_VIRT_SFR, struct.pack("<II", VSFR_SOUND_CTRL, new))
        if len(r) < 4 or struct.unpack("<I", r[:4])[0] != 1:
            return False
        return await self.read_vsfr(VSFR_SOUND_CTRL) == new

    async def spectrum_reset(self):
        """Restart the current spectrum of the RadiaCode (the accumulated
        spectrum is not touched). Returns True if the device confirms."""
        r = await self.execute(CMD_WR_VIRT_STRING, struct.pack("<II", VS_SPECTRUM, 0))
        return len(r) >= 4 and struct.unpack("<I", r[:4])[0] == 1

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
