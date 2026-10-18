# rz_test2.py – follow-up hardware test for RadZilla on M5Stack Core2 (UIFlow 2)
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# NOT part of RadZilla: run it by hand in Thonny (F5). Nothing is changed
# permanently; the motion sensor settings are restored at the end.
#
#   1 LEDs        LED 0..9 one by one, green, 30 %, 1 s each (driven directly
#                 with machine.bitstream – UIFlow 2 has no neopixel module)
#                 -> note where each number sits
#   2 Motion A    5 s via UIFlow (Imu.getAccel): how many DIFFERENT values?
#   3 Motion B    5 s direct MPU6886 read: ±8 g, 1 kHz, minimal filter
#                 -> tap the case twice when the display says TAP NOW
# Follow the instructions on the display. Copy the summary at the end.
import math
import time
import M5
from M5 import Lcd
import machine

LED_PIN = 25
LED_COUNT = 10
LED_LEVEL = 0.30
LED_STEP_MS = 1000
IMU_SECONDS = 5
SPIKE_G = 1.5

MPU_ADDR = 0x68
REG_SMPLRT_DIV, REG_CONFIG, REG_ACCEL_CONFIG, REG_ACCEL_CONFIG2 = 0x19, 0x1A, 0x1C, 0x1D
REG_ACCEL_XOUT_H, REG_WHO_AM_I = 0x3B, 0x75

results = []


def screen(title, *lines, color=0xFFFFFF, big=None):
    try:
        Lcd.fillScreen(0x000000)
        Lcd.setTextColor(0xFFC800, 0x000000)
        Lcd.setTextSize(2)
        Lcd.drawString(title, 10, 10)
        Lcd.setTextColor(color, 0x000000)
        y = 50
        for ln in lines:
            Lcd.drawString(str(ln), 10, y)
            y += 24
        if big is not None:
            Lcd.setTextSize(6)
            Lcd.drawString(str(big), 130, 120)
            Lcd.setTextSize(2)
    except Exception as e:
        print("display:", repr(e))


def say(*lines):
    for ln in lines:
        print(">>", ln)


def report(name, ok, detail=""):
    line = "%s %-9s %s" % ("OK  " if ok else "FAIL", name, detail)
    print(line)
    results.append(line)


def countdown(title, text):
    for n in (3, 2, 1):
        screen(title, text, "starting in ...", big=n)
        time.sleep_ms(1000)


# ---------- 1 LEDs --------------------------------------------------------------------
def leds_write(pin, colors):
    buf = bytearray()
    for r, g, b in colors:
        buf += bytes((g, r, b))              # SK6812 expects GRB order
    machine.bitstream(pin, 0, (400, 850, 800, 450), buf)


def test_leds():
    say("LED TEST: watch the two LED bars on the sides.",
        "Each number lights up for 1 s - note where it sits",
        "(e.g. 0 = left top ... 4 = left bottom, 5 = right bottom ...).")
    countdown("1 LEDs", "watch the side LEDs")
    try:
        pin = machine.Pin(LED_PIN, machine.Pin.OUT)
        g = int(255 * LED_LEVEL)
        for i in range(LED_COUNT):
            leds_write(pin, [(0, g, 0) if k == i else (0, 0, 0) for k in range(LED_COUNT)])
            screen("1 LEDs", "which LED is lit?", "note its position", big=i)
            print("   LED %d is on" % i)
            time.sleep_ms(LED_STEP_MS)
        leds_write(pin, [(0, 0, 0)] * LED_COUNT)
        report("leds", True, "note position of LED 0..9")
    except Exception as e:
        report("leds", False, repr(e))


# ---------- 2 motion via UIFlow ------------------------------------------------------------
def test_imu_uiflow():
    say("MOTION A: just leave the device lying still.")
    screen("2 Motion A (UIFlow)", "leave it lying still", "measuring 5 s ...")
    try:
        from M5 import Imu
        n = 0
        seen = set()
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < IMU_SECONDS * 1000:
            seen.add(tuple(Imu.getAccel()))
            n += 1
        detail = "%d reads/s, %d different values" % (n // IMU_SECONDS, len(seen))
        screen("2 Motion A (UIFlow)", detail[:26], detail[26:])
        report("imu-uiflow", True, detail)
    except Exception as e:
        report("imu-uiflow", False, repr(e))


# ---------- 3 motion direct ------------------------------------------------------------------
def test_imu_direct():
    say("MOTION B: when the display shows TAP NOW,",
        "tap the case TWICE (like a double tap), then leave it still.")
    try:
        i2c = machine.I2C(0, scl=machine.Pin(22), sda=machine.Pin(21), freq=400000)
        who = i2c.readfrom_mem(MPU_ADDR, REG_WHO_AM_I, 1)[0]
        saved = {r: i2c.readfrom_mem(MPU_ADDR, r, 1)[0]
                 for r in (REG_SMPLRT_DIV, REG_CONFIG, REG_ACCEL_CONFIG, REG_ACCEL_CONFIG2)}
    except Exception as e:
        report("imu-direct", False, "I2C: %r" % e)
        return
    try:
        i2c.writeto_mem(MPU_ADDR, REG_SMPLRT_DIV, b"\x00")     # 1 kHz
        i2c.writeto_mem(MPU_ADDR, REG_ACCEL_CONFIG, b"\x10")   # ±8 g
        i2c.writeto_mem(MPU_ADDR, REG_ACCEL_CONFIG2, b"\x00")  # widest accel filter at 1 kHz
        countdown("3 Motion B (direct)", "get ready to tap twice")
        screen("3 Motion B (direct)", "", "  TAP TWICE NOW!", color=0xFF4040)
        n = 0
        last = None
        changes = 0
        spikes = []
        in_spike = False
        peak = 0.0
        g = None
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < IMU_SECONDS * 1000:
            raw = i2c.readfrom_mem(MPU_ADDR, REG_ACCEL_XOUT_H, 6)
            if raw != last:
                changes += 1
                last = raw
            n += 1
            ax, ay, az = [((raw[k] << 8 | raw[k + 1]) - (65536 if raw[k] & 0x80 else 0)) / 4096
                          for k in (0, 2, 4)]
            if g is None:
                g = [ax, ay, az]
            dev = math.sqrt((ax - g[0]) ** 2 + (ay - g[1]) ** 2 + (az - g[2]) ** 2)
            peak = max(peak, dev)
            if dev > SPIKE_G and not in_spike:
                in_spike = True
                spikes.append((time.ticks_diff(time.ticks_ms(), t0), dev))
            elif dev < 0.5:
                in_spike = False
                g[0] += 0.01 * (ax - g[0])
                g[1] += 0.01 * (ay - g[1])
                g[2] += 0.01 * (az - g[2])
        detail = "who 0x%02X, %d reads/s, %d new values/s, %d spikes, peak %.1f g" % (
            who, n // IMU_SECONDS, changes // IMU_SECONDS, len(spikes), peak)
        for t, d in spikes:
            print("   spike at %4d ms: %.1f g" % (t, d))
        screen("3 Motion B (direct)", "%d new values/s" % (changes // IMU_SECONDS),
               "%d spikes" % len(spikes), "peak %.1f g" % peak)
        report("imu-direct", True, detail)
    except Exception as e:
        report("imu-direct", False, repr(e))
    finally:
        for r, v in saved.items():                             # restore UIFlow settings
            try:
                i2c.writeto_mem(MPU_ADDR, r, bytes((v,)))
            except Exception:
                pass


def main():
    M5.begin()
    for test in (test_leds, test_imu_uiflow, test_imu_direct):
        try:
            test()
        except Exception as e:
            report(test.__name__, False, "crash: %r" % e)
        time.sleep_ms(500)
    print("\n===== RZ TEST 2 SUMMARY =====")
    for ln in results:
        print(ln)
    print("=============================")
    screen("Done", "see Thonny shell", "for the summary")


main()
