# rz_wav_test.py – sound / LED / vibration test for RadZilla M5 on M5Stack Core2
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# NOT part of RadZilla: run it by hand in Thonny (F5). Changes nothing.
# Needs the WAV files in /flash/radzilla/sounds/ (upload the radzilla folder).
#
#   1 Jingle 60 %      clicks -> all LEDs flash green + 20 ms vibration
#   2 DOSE siren 100 % LEDs pulse red with the pitch, 300 ms vibration at start + end
#   3 DANGER siren     3 bursts: red run centre -> ends + 400 ms vibration each
# Run 1 showed: playWavFile() blocks for the whole sound. This version loads the
# file into RAM and uses Speaker.playWav(), which should play in the background.
# Copy the summary at the end and tell me what you saw / heard / felt.
import time
import machine
import M5
from M5 import Lcd, Speaker, Power

SOUNDS = "/flash/radzilla/sounds/"
LED_PIN, LED_N, LED_LEVEL = 25, 10, 0.30
RUN = ((2, 7), (1, 3, 6, 8), (0, 4, 5, 9))        # centre -> ends, per side
RUN_STEP_MS = 80

JINGLE_MS = 4000
JINGLE_CLICKS = (1200, 1425, 1593, 1702, 1742, 2005, 2279, 2399, 2516, 2561,
                 2639, 2786, 3061, 3105, 3149)
DOSE_MS, DOSE_RISE, DOSE_HOLD, DOSE_FALL = 6300, 2200, 1400, 2400
DANGER_MS, DANGER_BURSTS = 5000, (0, 1800, 3600)

results = []
pin = machine.Pin(LED_PIN, machine.Pin.OUT)


def note(ok, name, detail=""):
    line = "%s %-8s %s" % ("OK  " if ok else "FAIL", name, detail)
    print(line)
    results.append(line)


def leds(cols):
    buf = bytearray()
    for r, g, b in cols:
        buf += bytes((int(g * LED_LEVEL), int(r * LED_LEVEL), int(b * LED_LEVEL)))
    machine.bitstream(pin, 0, (400, 850, 800, 450), buf)


def leds_all(col):
    leds([col] * LED_N)


def leds_off():
    leds_all((0, 0, 0))


def screen(title, line=""):
    Lcd.fillScreen(0x000000)
    Lcd.setTextColor(0xFFC800, 0x000000)
    Lcd.setTextSize(2)
    Lcd.drawString(title, 10, 90)
    Lcd.setTextColor(0xFFFFFF, 0x000000)
    Lcd.drawString(line, 10, 125)
    Lcd.setTextSize(1)


_buf = [None]          # keep the WAV data alive while it plays


def play(name, vol_pct):
    """Load a WAV file into RAM and start it with Speaker.playWav(), which
    plays in the background (playWavFile() streams and blocks the program).
    Returns (start ticks, ms the call blocked)."""
    with open(SOUNDS + name, "rb") as f:
        _buf[0] = f.read()
    Speaker.setVolume(int(255 * vol_pct / 100))
    t0 = time.ticks_ms()
    Speaker.playWav(_buf[0])
    return t0, time.ticks_diff(time.ticks_ms(), t0)


def wait_end(t0, dur_ms, step):
    """Run step(elapsed_ms) until the sound is over; returns isPlaying info."""
    playing_seen = False
    while True:
        el = time.ticks_diff(time.ticks_ms(), t0)
        try:
            if Speaker.isPlaying():
                playing_seen = True
        except Exception:
            pass
        if el > dur_ms + 300:
            break
        step(el)
        time.sleep_ms(5)
    leds_off()
    Power.setVibration(0)
    return playing_seen


# ---------- 1 jingle --------------------------------------------------------------------
def test_jingle():
    screen("1 Jingle 60 %", "LEDs green + vibration")
    state = {"i": 0, "off_at": None}

    def step(el):
        i = state["i"]
        if i < len(JINGLE_CLICKS) and el >= JINGLE_CLICKS[i]:
            state["i"] = i + 1
            leds_all((0, 255, 0))
            Power.setVibration(200)
            state["off_at"] = el + 30
        if state["off_at"] is not None and el >= state["off_at"]:
            state["off_at"] = None
            leds_off()
            Power.setVibration(0)

    t0, blocked = play("jingle.wav", 60)
    seen = wait_end(t0, JINGLE_MS, step)
    note(True, "jingle", "playWav blocked %d ms, isPlaying seen: %s, clicks %d"
         % (blocked, seen, state["i"]))


# ---------- 2 DOSE siren -------------------------------------------------------------------
def test_dose():
    screen("2 DOSE siren 100 %", "LEDs pulse red")
    vib = {"end_on": False}

    def step(el):
        if el < DOSE_RISE:
            p = el / DOSE_RISE
        elif el < DOSE_RISE + DOSE_HOLD:
            p = 1.0
        else:
            p = max(0.0, 1 - (el - DOSE_RISE - DOSE_HOLD) / DOSE_FALL)
        leds_all((int(30 + 225 * p), 0, 0))
        Power.setVibration(200 if el < 300 or DOSE_MS - 300 <= el < DOSE_MS else 0)

    t0, blocked = play("siren_dose.wav", 100)
    seen = wait_end(t0, DOSE_MS, step)
    note(True, "dose", "playWav blocked %d ms, isPlaying seen: %s" % (blocked, seen))


# ---------- 3 DANGER siren ---------------------------------------------------------------------
def test_danger():
    screen("3 DANGER siren 100 %", "red run + vibration")

    def step(el):
        on = None
        vib = False
        for b in DANGER_BURSTS:
            d = el - b
            if 0 <= d < 1000:
                vib = d < 400
                k = d // RUN_STEP_MS
                if k < len(RUN):
                    on = set()
                    for j in range(k + 1):
                        on.update(RUN[j])
                elif d < 600:
                    on = set(range(LED_N))
                else:
                    on = set()
        leds([(255, 0, 0) if on and i in on else (0, 0, 0) for i in range(LED_N)])
        Power.setVibration(200 if vib else 0)

    t0, blocked = play("siren_danger.wav", 100)
    seen = wait_end(t0, DANGER_MS, step)
    note(True, "danger", "playWav blocked %d ms, isPlaying seen: %s" % (blocked, seen))


def main():
    M5.begin()
    Lcd.setTextSize(1)
    try:
        Speaker.begin()
    except Exception:
        pass
    for fn in (test_jingle, test_dose, test_danger):
        try:
            fn()
        except Exception as e:
            note(False, fn.__name__, repr(e))
            leds_off()
            Power.setVibration(0)
        time.sleep_ms(800)
    screen("Done", "see Thonny shell")
    print("\n===== RZ WAV TEST SUMMARY =====")
    for ln in results:
        print(ln)
    print("===============================")


main()
