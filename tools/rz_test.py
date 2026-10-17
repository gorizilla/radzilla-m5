# rz_test.py – hardware test for RadZilla on M5Stack Core2 (UIFlow 2 firmware)
#
# RadZilla – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – licensed under CC BY-NC 4.0 (see LICENSE.md)
#
# NOT part of RadZilla: run it by hand in Thonny (F5). It changes nothing on
# the device (boot.py, main.py and the boot option stay as they are); the SD
# test file is deleted again.
#
# Tests, one after the other (results on the display and in the shell):
#   1 Info          firmware, free memory, battery, RTC time
#   2 microSD       mount, create /sd/RadZilla/, write/read/delete a test file
#   3 Speaker       60 % volume: 2000 Hz 200 ms, 3000 Hz 200 ms, 1 s siren
#   4 Vibration     2 x 300 ms
#   5 LEDs          LED 0..9 one by one, green, 30 %, 1 s each – note where
#                   each number sits (left/right side, top/bottom)
#   6 Motion sensor 5 s: measure, tap the case twice meanwhile
#   7 Touch buttons 10 s: touch A, B and C
#   8 Bluetooth     10 s scan, is a "RadiaCode..." found?
#                   (disconnect the RadiaCode phone app first)
# A failing test is marked FAIL with its reason; the others still run.
# Copy the summary at the end and send it back.
import time
import M5
from M5 import Lcd

VOLUME_PCT = 60
VIBRATION_MS = 300
LED_PIN = 25
LED_COUNT = 10
LED_LEVEL = 0.30
LED_STEP_MS = 1000
IMU_SECONDS = 5
TOUCH_SECONDS = 10
BLE_SECONDS = 10

results = []


# ---------- display helpers ------------------------------------------------------
def screen(title, *lines, color=0xFFFFFF):
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
    except Exception as e:
        print("display:", repr(e))


def report(name, ok, detail=""):
    tag = "OK  " if ok else "FAIL"
    line = "%s %-10s %s" % (tag, name, detail)
    print(line)
    results.append(line)


# ---------- 1 info ----------------------------------------------------------------
def test_info():
    import sys
    import gc
    gc.collect()
    detail = "MP %s, free %d KB" % (".".join(str(v) for v in sys.implementation.version[:3]),
                                   gc.mem_free() // 1024)
    try:
        from M5 import Power
        detail += ", batt %s %%" % Power.getBatteryLevel()
    except Exception as e:
        detail += ", batt ? (%r)" % e
    t = None
    for get in (lambda: M5.Rtc.getDateTime(),
                lambda: __import__("machine").RTC().datetime()):
        try:
            t = get()
            break
        except Exception:
            pass
    detail += ", rtc %s" % (t,)
    screen("1 Info", detail[:26], detail[26:52], detail[52:78])
    report("info", True, detail)


# ---------- 2 microSD -------------------------------------------------------------------
def test_sd():
    import os
    screen("2 microSD", "mounting ...")
    mounted = "sd" in os.listdir("/")
    err = ""
    if not mounted:
        try:                                     # UIFlow 2 driver (shares SPI with LCD)
            from hardware import sdcard
            sdcard.SDCard(slot=3, width=1, sck=18, miso=38, mosi=23, cs=4, freq=1000000)
            mounted = "sd" in os.listdir("/")
        except Exception as e:
            err = "hardware.sdcard: %r" % e
    if not mounted:
        try:                                     # plain MicroPython fallback
            import machine
            sd = machine.SDCard(slot=2, sck=18, miso=38, mosi=23, cs=4)
            os.mount(sd, "/sd")
            mounted = True
        except Exception as e:
            err += " machine.SDCard: %r" % e
    if not mounted:
        screen("2 microSD", "FAIL", err[:26], err[26:52])
        report("sd", False, err)
        return
    try:
        try:
            os.mkdir("/sd/RadZilla")
        except OSError:
            pass                                 # already there
        path = "/sd/RadZilla/rz_test.txt"
        with open(path, "w") as f:
            f.write("RadZilla SD test\n")
        with open(path) as f:
            ok = f.read() == "RadZilla SD test\n"
        os.remove(path)
        st = os.statvfs("/sd")
        free_mb = st[0] * st[3] // (1024 * 1024)
        screen("2 microSD", "OK" if ok else "read mismatch", "free %d MB" % free_mb)
        report("sd", ok, "free %d MB" % free_mb)
    except Exception as e:
        screen("2 microSD", "FAIL", repr(e)[:26])
        report("sd", False, repr(e))


# ---------- 3 speaker ---------------------------------------------------------------------
def test_speaker():
    screen("3 Speaker", "2000 Hz, 3000 Hz,", "then siren")
    try:
        from M5 import Speaker
        try:
            Speaker.begin()
        except Exception:
            pass
        Speaker.setVolume(int(255 * VOLUME_PCT / 100))
        Speaker.tone(2000, 200)
        time.sleep_ms(400)
        Speaker.tone(3000, 200)
        time.sleep_ms(400)
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < 1000:      # rising siren
            p = time.ticks_diff(time.ticks_ms(), t0) / 1000
            Speaker.tone(int(1500 + 2000 * p), 25)
            time.sleep_ms(20)
        time.sleep_ms(100)
        report("speaker", True, "played - did you hear 2 tones + siren?")
    except Exception as e:
        report("speaker", False, repr(e))


# ---------- 4 vibration -------------------------------------------------------------------
def test_vibration():
    screen("4 Vibration", "2 x %d ms" % VIBRATION_MS)
    try:
        from M5 import Power
        for _ in range(2):
            Power.setVibration(200)
            time.sleep_ms(VIBRATION_MS)
            Power.setVibration(0)
            time.sleep_ms(400)
        report("vibration", True, "done - did you feel it twice?")
    except Exception as e:
        report("vibration", False, repr(e))


# ---------- 5 LEDs --------------------------------------------------------------------------
def test_leds():
    try:
        import machine
        import neopixel
        np = neopixel.NeoPixel(machine.Pin(LED_PIN), LED_COUNT)
        g = int(255 * LED_LEVEL)
        for i in range(LED_COUNT):
            for k in range(LED_COUNT):
                np[k] = (0, 0, 0)
            np[i] = (0, g, 0)
            np.write()
            screen("5 LEDs", "LED number:", "", "      %d" % i, "", "where is it?")
            time.sleep_ms(LED_STEP_MS)
        for k in range(LED_COUNT):
            np[k] = (0, 0, 0)
        np.write()
        report("leds", True, "note the position of LED 0..9")
    except Exception as e:
        report("leds", False, repr(e))


# ---------- 6 motion sensor ------------------------------------------------------------------
def test_imu():
    screen("6 Motion sensor", "tap the case", "twice now ...")
    try:
        from M5 import Imu
        import math
        n = 0
        spikes = 0
        in_spike = False
        peak = 0.0
        g = None
        t0 = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), t0) < IMU_SECONDS * 1000:
            ax, ay, az = Imu.getAccel()
            n += 1
            if g is None:
                g = [ax, ay, az]
            dev = math.sqrt((ax - g[0]) ** 2 + (ay - g[1]) ** 2 + (az - g[2]) ** 2)
            peak = max(peak, dev)
            if dev > 1.5 and not in_spike:
                in_spike = True
                spikes += 1
            elif dev < 0.5:
                in_spike = False
                g[0] += 0.01 * (ax - g[0])
                g[1] += 0.01 * (ay - g[1])
                g[2] += 0.01 * (az - g[2])
        rate = n / IMU_SECONDS
        detail = "%d samples/s, %d spikes > 1.5 g, peak %.1f g" % (rate, spikes, peak)
        screen("6 Motion sensor", "%d samples/s" % rate, "%d spikes" % spikes,
               "peak %.1f g" % peak)
        report("imu", True, detail)
    except Exception as e:
        report("imu", False, repr(e))


# ---------- 7 touch buttons --------------------------------------------------------------------
def test_touch():
    from M5 import BtnA, BtnB, BtnC
    seen = set()
    t0 = time.ticks_ms()
    try:
        while time.ticks_diff(time.ticks_ms(), t0) < TOUCH_SECONDS * 1000 and len(seen) < 3:
            M5.update()
            for name, b in (("A", BtnA), ("B", BtnB), ("C", BtnC)):
                if b.wasPressed():
                    seen.add(name)
            left = TOUCH_SECONDS - time.ticks_diff(time.ticks_ms(), t0) // 1000
            screen("7 Touch buttons", "touch A, B and C", "seen: " + " ".join(sorted(seen)),
                   "%d s left" % left)
            time.sleep_ms(50)
        report("touch", len(seen) == 3, "seen: " + (" ".join(sorted(seen)) or "none"))
    except Exception as e:
        report("touch", False, repr(e))


# ---------- 8 bluetooth --------------------------------------------------------------------------
def test_ble():
    screen("8 Bluetooth", "scanning %d s ..." % BLE_SECONDS)
    try:
        import bluetooth
        found = {}
        done = [False]

        def name_of(adv):
            i = 0
            while i + 1 < len(adv):
                ln = adv[i]
                if ln == 0:
                    break
                if adv[i + 1] in (0x08, 0x09):
                    return bytes(adv[i + 2:i + 1 + ln]).decode("utf-8", "ignore")
                i += 1 + ln
            return None

        def irq(event, data):
            if event == 5:                       # scan result
                _, addr, _, rssi, adv = data
                n = name_of(bytes(adv))
                if n:
                    found[n] = rssi
            elif event == 6:                     # scan done
                done[0] = True

        ble = bluetooth.BLE()
        ble.active(True)
        ble.irq(irq)
        ble.gap_scan(BLE_SECONDS * 1000, 30000, 30000, True)
        t0 = time.ticks_ms()
        while not done[0] and time.ticks_diff(time.ticks_ms(), t0) < (BLE_SECONDS + 3) * 1000:
            time.sleep_ms(100)
        ble.active(False)
        rc = [n for n in found if n.startswith("RadiaCode")]
        screen("8 Bluetooth", "%d devices" % len(found),
               ("found: " + rc[0])[:26] if rc else "no RadiaCode")
        report("ble", bool(rc), ("RadiaCode: %s" % rc[0]) if rc else
               "no RadiaCode (%d other devices)" % len(found))
    except Exception as e:
        report("ble", False, repr(e))


# ---------- run -----------------------------------------------------------------------------------
def main():
    M5.begin()
    for test in (test_info, test_sd, test_speaker, test_vibration, test_leds,
                 test_imu, test_touch, test_ble):
        try:
            test()
        except Exception as e:
            report(test.__name__, False, "crash: %r" % e)
        time.sleep_ms(500)
    print("\n===== RZ TEST SUMMARY =====")
    for ln in results:
        print(ln)
    print("===========================")
    screen("Done", "see Thonny shell", "for the summary")


main()
