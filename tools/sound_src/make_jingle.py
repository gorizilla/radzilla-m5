# make_jingle.py – generates jingle.wav (splash, 4 s, with Geiger clicks) for RadZilla M5.
#
# RadZilla M5 – external display for RadiaCode
# Copyright (c) 2026 Shimizilla – license: see LICENSE.md
#
# Run on a computer with Python 3: python3 make_jingle.py – writes the WAV file(s)
# into the current folder; copy them to device/radzilla/sounds/.
import wave, struct, math, random
SR = 22050; DUR = 4.0
random.seed(21)
def sq(ph, d): return 1.0 if ph % 1.0 < d else -1.0
out = [0.0] * int(SR * DUR)
def add(n, v):
    if 0 <= n < len(out): out[n] += v
# --- end-time melody (0 - 1.5 s): slow, low, phrygian: C4 - Db4 - G3 held, fading ---------
mel = [(0.00, 0.38, 262), (0.40, 0.38, 277), (0.80, 0.70, 196)]
ph = 0.0
for t0, ln, f in mel:
    for n in range(int(t0 * SR), int((t0 + ln) * SR)):
        tt = n / SR - t0
        vib = 1 + 0.015 * math.sin(2 * math.pi * 4.2 * tt) * min(1, tt / 0.15)
        ph += f * vib / SR
        d = 0.45 - 0.35 * tt / ln                  # slow pulse-width sweep
        env = min(1, tt / 0.02) * (1 - 0.85 * (tt / ln) ** 1.5 if f == 196 else 1 - 0.3 * tt / ln)
        out[n] += 0.40 * env * sq(ph, d)
# --- real Geiger clicks: sharp broadband pulse + short damped ring (like an old counter) ----
def click(t0, amp=1.0, crunch=0.0):
    """Clean digital click: 1.5 ms square burst at 3 kHz, sharp attack, no noise."""
    n0 = int(t0 * SR)
    for k in range(int(0.0015 * SR)):
        tt = k / SR
        x = sq(3000 * tt, 0.5) * (1 - tt / 0.0015) ** 0.5
        add(n0 + k, 0.5 * x)
# clicks start while the last note fades (1.2 s) and run cleanly until 3.7 s, irregular ~6/s
t = 1.20
while t < 3.85:
    click(t)
    t += random.expovariate(6)
y = 0; res = []
for x in out:
    y += 0.7 * (x - y); res.append(y)
w = wave.open("jingle.wav", "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 32767)) for v in res)); w.close(); print("ok")
