# fx.py – sound, LED and vibration effects, played in sync.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# One effect at a time, higher priority wins:
#   DANGER (siren, 3 bursts) > DOSE (siren ~6 s) > HIGH (beep) > GEIGER > HEARTBEAT
# Each effect is a function of the elapsed time that returns the LED colours
# and the vibration level for that moment; fx_task() renders it every 20 ms.
#
# Sounds are WAV files in /flash/radzilla/sounds/. They are loaded into RAM
# and started with dev.play_wav(): playback runs in the background (the
# UIFlow playWavFile() would block the program for the whole sound).
#
# Needs from the device: leds(list of (r, g, b)), vibrate(level),
# play_wav(data, vol_pct), stop_sound(), set_volume(pct), tone(hz, ms).
import asyncio
import math
import random
import time

SOUND_DIR = "/flash/radzilla/sounds/"
RUN = ((2, 7), (1, 3, 6, 8), (0, 4, 5, 9))     # LED groups centre -> ends, per side
N_LED = 10
OFF = (0, 0, 0)

P_IDLE, P_HEART, P_GEIGER, P_HIGH, P_DOSE, P_DANGER = 0, 1, 2, 3, 4, 5


class FX:
    def __init__(self, dev, cfg):
        self.dev = dev
        self.c = cfg
        self.cur = None             # (prio, start ticks, frame function, length ms)
        self.wav = {}               # name -> bytes (kept while playing / preloaded)
        self.last_leds = None
        self.last_vib = None
        self.geiger_clicks = []
        if cfg.FX_PRELOAD:
            for n in ("siren_dose.wav", "siren_danger.wav"):
                self._load(n)

    # ---------- helpers ----------
    def _load(self, name):
        if name not in self.wav:
            try:
                with open(SOUND_DIR + name, "rb") as f:
                    self.wav[name] = f.read()
            except Exception as e:
                print("fx: cannot load %s: %r" % (name, e))
                return None
        return self.wav[name]

    def _play(self, name, vol):
        data = self._load(name)
        if data is not None:
            self.dev.play_wav(data, vol)

    def busy(self, prio=P_HEART):
        """True if an effect with at least this priority is running."""
        return self.cur is not None and self.cur[0] >= prio

    def _start(self, prio, frame, length_ms):
        if self.cur is not None and self.cur[0] > prio:
            return False
        if self.cur is not None and self.cur[0] >= P_HIGH:
            self.dev.stop_sound()               # a higher alarm replaces a sound
        self.cur = (prio, time.ticks_ms(), frame, length_ms)
        return True

    def _run_leds(self, el, col, step):
        """Lights moving from the centre to the ends of both bars (or blink)."""
        if self.c.LED_MODE == "blink":
            return [col] * N_LED if el < self.c.LED_BLINK_MS else None
        k = el // step
        if k >= len(RUN):
            return None
        return [col if i in RUN[k] else OFF for i in range(N_LED)]

    # ---------- effects ----------
    def heartbeat(self):
        c = self.c
        if not (c.LED_ON and c.HEARTBEAT_ON) or self.busy():
            return
        self._start(P_HEART, lambda el: (self._run_leds(el, c.LED_GREEN, c.LED_STEP_MS), 0),
                    len(RUN) * c.LED_STEP_MS + 40)

    def high(self):
        c = self.c
        if not self._start(P_HIGH, None, 0):
            return
        self.dev.set_volume(c.ALARM_VOLUME_PCT)
        for i in range(c.ALARM1_BEEPS):        # beeps are short tones (non-blocking)
            asyncio.create_task(self._tone_at(i * (c.ALARM1_BEEP_MS + c.ALARM1_PAUSE_MS),
                                              c.ALARM1_FREQ_HZ, c.ALARM1_BEEP_MS))

        def frame(el):
            return (self._run_leds(el, c.LED_YELLOW, c.LED_STEP_MS),
                    c.VIB_LEVEL if el < c.HIGH_VIB_MS else 0)
        self.cur = (P_HIGH, time.ticks_ms(), frame,
                    max(c.HIGH_VIB_MS, len(RUN) * c.LED_STEP_MS) + 40)

    async def _tone_at(self, delay, hz, ms):
        await asyncio.sleep_ms(delay)
        self.dev.tone(hz, ms)

    def danger(self):
        c = self.c
        if not self._start(P_DANGER, None, 0):
            return
        self._play("siren_danger.wav", c.ALARM_VOLUME_PCT)

        def frame(el):
            leds, vib = [OFF] * N_LED, 0
            for b in c.DANGER_BURSTS_MS:
                d = el - b
                if 0 <= d < c.DANGER_BURST_MS:
                    vib = c.VIB_LEVEL if d < c.DANGER_VIB_MS else 0
                    run = self._run_leds(d, c.LED_RED, c.LED_STEP_MS)
                    if run is not None:
                        leds = run
                    elif d < c.DANGER_BURST_MS * 0.6:
                        leds = [c.LED_RED] * N_LED
            return leds, vib
        self.cur = (P_DANGER, time.ticks_ms(), frame, c.DANGER_SIREN_MS)

    def dose(self):
        c = self.c
        if not self._start(P_DOSE, None, 0):
            return
        self._play("siren_dose.wav", c.ALARM_VOLUME_PCT)
        rise, hold, fall = c.DOSE_RISE_MS, c.DOSE_HOLD_MS, c.DOSE_FALL_MS
        total = rise + hold + fall

        def frame(el):
            if el < rise:
                p = el / rise
            elif el < rise + hold:
                p = 1.0
            else:
                p = max(0.0, 1 - (el - rise - hold) / fall)
            r = int(c.LED_RED[0] * (0.12 + 0.88 * p))
            vib = c.VIB_LEVEL if (el < c.DOSE_VIB_MS or total - c.DOSE_VIB_MS <= el < total) else 0
            return [(r, 0, 0)] * N_LED, vib
        self.cur = (P_DOSE, time.ticks_ms(), frame, total + 100)

    def geiger(self):
        """Dose pre-warning: random clicks, LEDs flicker orange with them."""
        c = self.c
        if not self._start(P_GEIGER, None, 0):
            return
        t, clicks = 0, []
        while t < c.GEIGER_DURATION_MS:
            clicks.append(t)
            t += max(c.GEIGER_CLICK_MS + 5, int(-math.log(1.0 - random.random()) / c.GEIGER_RATE_HZ * 1000))
        self.geiger_clicks = clicks
        self.dev.set_volume(c.ALARM_VOLUME_PCT)
        state = {"i": 0}

        def frame(el):
            on = False
            while state["i"] < len(clicks) and el >= clicks[state["i"]]:
                self.dev.tone(c.GEIGER_FREQ_HZ, c.GEIGER_CLICK_MS)
                state["i"] += 1
                on = True
            if not on and state["i"] and el - clicks[state["i"] - 1] < 30:
                on = True
            return ([c.LED_ORANGE] * N_LED if on else [OFF] * N_LED), 0
        self.cur = (P_GEIGER, time.ticks_ms(), frame, c.GEIGER_DURATION_MS + 50)

    def stop(self):
        self.cur = None
        self.dev.stop_sound()

    # ---------- renderer ----------
    def _output(self, leds, vib):
        if not self.c.LED_ON:
            leds = [OFF] * N_LED
        if not self.c.VIB_ON:
            vib = 0
        if leds != self.last_leds:
            self.last_leds = leds
            self.dev.leds(leds)
        if vib != self.last_vib:
            self.last_vib = vib
            self.dev.vibrate(vib)

    async def task(self):
        while True:
            await asyncio.sleep_ms(20)
            cur = self.cur
            if cur is None:
                self._output([OFF] * N_LED, 0)
                continue
            prio, t0, frame, length = cur
            el = time.ticks_diff(time.ticks_ms(), t0)
            if el >= length:
                self.cur = None
                self._output([OFF] * N_LED, 0)
                continue
            try:
                leds, vib = frame(el)
            except Exception as e:
                print("fx:", repr(e))
                self.cur = None
                continue
            self._output(leds if leds is not None else [OFF] * N_LED, vib)
