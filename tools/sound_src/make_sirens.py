import wave, struct, math
SR = 22050
def siren_curve(t, rise, hold, fall, lo, hi):
    if t < rise:
        p = t / rise; return lo + (hi - lo) * (1 - (1 - p) ** 2)        # slow start, speeding up
    if t < rise + hold:
        return hi
    p = min(1.0, max(0.0, (t - rise - hold) / fall)); return hi - (hi - lo) * p ** 0.7       # long fade down
def render(segments, total):
    out = [0.0] * int(SR * total)
    for t0, rise, hold, fall, lo, hi, vol in segments:
        p1 = p2 = 0.0
        dur = rise + hold + fall
        for n in range(int(t0 * SR), min(len(out), int((t0 + dur) * SR))):
            t = n / SR - t0
            f = siren_curve(t, rise, hold, fall, lo, hi)
            p1 += f / SR; p2 += f * 1.006 / SR                         # two slightly detuned rotors
            env = min(1, t / 0.15) * (1 if t < rise + hold else 1 - 0.8 * ((t - rise - hold) / fall))
            x = 0.5 * math.sin(2 * math.pi * p1) + 0.5 * math.sin(2 * math.pi * p2)
            x += 0.25 * math.sin(2 * math.pi * 2 * p1)                   # a bit of harmonic bite
            out[n] += vol * env * x
    return out
def save(name, out):
    w = wave.open(name, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, v)) * 30000)) for v in out)); w.close()
# DOSE: one long purge-like wail (~6 s)
save("siren_dose.wav", render([(0, 2.2, 1.4, 2.4, 180, 620, 0.55)], 6.3))
# DANGER: max 3 short wails, 1 s each, every 3 s
save("siren_danger.wav", render([(k * 1.8, 0.45, 0.25, 0.3, 260, 700, 0.6) for k in range(3)], 5.0))
print("ok")
