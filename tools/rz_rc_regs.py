# rz_rc_regs.py – READ ONLY: shows the sound / light / alarm registers of the RadiaCode.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# NOT part of RadZilla. Writes NOTHING to the RadiaCode, only reads registers
# (command RD_VIRT_SFR_BATCH 0x082A, as in the Python library cdump/radiacode, MIT).
#
# Use:
#   1. Stop RadZilla in Thonny (Stop) and disconnect the RadiaCode app.
#   2. Run this file with F5 – it connects, prints all values and disconnects.
#   3. Change ONE setting in the RadiaCode app (e.g. ticker off), close the app
#      connection, run this file again and compare: the register that changed
#      belongs to that setting.
import asyncio
import struct

from radzilla.core import radiacode as rcm

CMD_RD_VIRT_SFR_BATCH = 0x082A

REGS = (
    (0x0503, "DEVICE_ON"),
    (0x0510, "DISP_CTRL"),
    (0x0511, "DISP_BRT"),
    (0x0513, "DISP_OFF_TIME"),
    (0x0514, "DISP_ON"),
    (0x0516, "DISP_BACKLT_ON"),
    (0x0520, "SOUND_CTRL"),
    (0x0521, "SOUND_VOL"),
    (0x0522, "SOUND_ON"),
    (0x0523, "SOUND_BUTTON"),
    (0x0530, "VIBRO_CTRL"),
    (0x0531, "VIBRO_ON"),
    (0x0540, "LEDS_CTRL"),
    (0x0545, "LEDS_ON"),
    (0x05E0, "ALARM_MODE"),
)

CTRL_BITS = ("BUTTONS", "CLICKS", "DR_ALARM1", "DR_ALARM2", "DR_OUT",
             "DS_ALARM1", "DS_ALARM2", "DS_OUT")


async def read_reg(rc, reg):
    """Raw 32-bit value of one register or None (read only)."""
    r = await rc.execute(CMD_RD_VIRT_SFR_BATCH, struct.pack("<II", 1, reg))
    if len(r) < 8:
        return None
    flags, value = struct.unpack("<II", r[:8])
    return value if flags & 1 else None


async def main():
    print("Searching RadiaCode ...")
    dev, name = await rcm.find()
    if dev is None:
        print("No RadiaCode found (app still connected?)")
        return
    rc = await rcm.RadiaCode.connect(dev)
    print("Connected:", name)
    try:
        for reg, label in REGS:
            try:
                v = await read_reg(rc, reg)
            except Exception as e:
                print("0x%04X %-15s error %r" % (reg, label, e))
                continue
            if v is None:
                print("0x%04X %-15s not readable" % (reg, label))
                continue
            line = "0x%04X %-15s 0x%08X  (%d)" % (reg, label, v, v)
            if label in ("SOUND_CTRL", "VIBRO_CTRL"):
                for shift in (0, 16):                # library reads the upper half for SOUND_CTRL
                    bits = (v >> shift) & 0xFF
                    on = [CTRL_BITS[i] for i in range(8) if bits & (1 << i)]
                    line += "\n        bits>>%d: %s" % (shift, " ".join(on) or "-")
            print(line)
    finally:
        await rc.disconnect()
        print("Disconnected - nothing was written.")


asyncio.run(main())
