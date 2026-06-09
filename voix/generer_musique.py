"""
Génère une musique ambient tech professionnelle pour Amah Agent.
Style : ambient électronique, chaleureux, doré — 100% libre de droits.
"""
import numpy as np
import wave, struct, os

SR     = 44100
DIR    = r"C:\Users\Smarte technologui\Desktop\Projets\amah-agent\voix"
OUTPUT = os.path.join(DIR, "musique_amah.wav")
DURATION = 210  # 3 min 30


def note_freq(note, octave=4):
    """Fréquence d'une note musicale."""
    notes = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,
             'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
    n = notes[note] + (octave - 4) * 12
    return 440.0 * (2 ** (n / 12))


def sine(freq, dur, amp=0.5, phase=0):
    t = np.linspace(0, dur, int(SR * dur), endpoint=False)
    return amp * np.sin(2 * np.pi * freq * t + phase)


def adsr(signal, a=0.1, d=0.1, s=0.7, r=0.3, sr=SR):
    """Enveloppe ADSR."""
    n   = len(signal)
    env = np.ones(n)
    na  = int(a * sr); nd = int(d * sr)
    nr  = int(r * sr); ns = n - na - nd - nr
    if ns < 0: ns = 0; nr = max(0, n - na - nd)
    env[:na]           = np.linspace(0, 1, na)
    env[na:na+nd]      = np.linspace(1, s, nd)
    env[na+nd:na+nd+ns]= s
    env[na+nd+ns:]     = np.linspace(s, 0, nr) if nr > 0 else np.array([])
    return signal * env[:n]


def pad_chord(freqs, dur, amp=0.15):
    """Accord pad doux (plusieurs harmoniques)."""
    result = np.zeros(int(SR * dur))
    for f in freqs:
        s = sine(f, dur, amp/len(freqs))
        s+= sine(f*2, dur, amp/len(freqs)*0.4)
        s+= sine(f*3, dur, amp/len(freqs)*0.2)
        result += adsr(s, a=0.8, d=0.3, s=0.7, r=1.5)
    return result


def bass_note(freq, dur, amp=0.20):
    """Basse avec harmoniques douces."""
    s = sine(freq, dur, amp)
    s+= sine(freq*2, dur, amp*0.3)
    s+= sine(freq*3, dur, amp*0.1)
    return adsr(s, a=0.05, d=0.2, s=0.6, r=0.4)


def shimmer(freq, dur, amp=0.06):
    """Brillance haute (shimmer)."""
    t = np.linspace(0, dur, int(SR*dur), endpoint=False)
    vibrato = 1 + 0.003 * np.sin(2*np.pi*5*t)
    s = amp * np.sin(2*np.pi*freq*vibrato*t)
    return adsr(s, a=1.2, d=0.5, s=0.5, r=2.0)


def soft_kick(dur_total, bpm=85, amp=0.12):
    """Kick doux et subtil."""
    beat     = SR * 60 / bpm
    track    = np.zeros(int(SR * dur_total))
    kick_dur = 0.18
    for beat_n in range(int(dur_total * bpm / 60)):
        start = int(beat_n * beat)
        if start + int(SR*kick_dur) > len(track):
            break
        t   = np.linspace(0, kick_dur, int(SR*kick_dur), endpoint=False)
        env = np.exp(-t * 30)
        freq= 80 * np.exp(-t * 40)
        k   = amp * env * np.sin(2*np.pi*freq*t)
        track[start:start+len(k)] += k
    return track


def hihat(dur_total, bpm=85, amp=0.04):
    """Hi-hat doux."""
    beat  = SR * 60 / bpm
    track = np.zeros(int(SR * dur_total))
    hat_d = 0.05
    for beat_n in range(int(dur_total * bpm / 60 * 2)):
        start = int(beat_n * beat / 2 + beat / 2)
        if start + int(SR*hat_d) > len(track): break
        noise = amp * np.random.randn(int(SR*hat_d))
        env   = np.exp(-np.linspace(0, 50, int(SR*hat_d)))
        track[start:start+len(noise)] += noise * env
    return track


print("Composition de la musique ambient Amah Agent...")

# ── Accords Am – F – C – G (progression douce et professionnelle) ────────────
# Am: A3-C4-E4  | F: F3-A3-C4  | C: C3-E4-G4  | G: G3-B3-D4
PROGRESSIONS = [
    [note_freq('A',3), note_freq('C',4), note_freq('E',4)],  # Am
    [note_freq('F',3), note_freq('A',3), note_freq('C',4)],  # F
    [note_freq('C',3), note_freq('E',4), note_freq('G',4)],  # C
    [note_freq('G',3), note_freq('B',3), note_freq('D',4)],  # G
]
BASS_ROOTS = [
    note_freq('A',2), note_freq('F',2),
    note_freq('C',2), note_freq('G',2),
]

CHORD_DUR = 4.0  # durée de chaque accord (secondes)
total_samples = int(SR * DURATION)
track = np.zeros(total_samples)

# ── Rythme ───────────────────────────────────────────────────────────────────
print("  Percussions...")
track += soft_kick(DURATION, bpm=88, amp=0.10)
track += hihat(DURATION, bpm=88, amp=0.035)

# ── Basse ────────────────────────────────────────────────────────────────────
print("  Basse...")
t_pos = 0
while t_pos < DURATION:
    for i, (chord, bass) in enumerate(zip(PROGRESSIONS, BASS_ROOTS)):
        if t_pos >= DURATION: break
        dur  = min(CHORD_DUR * 2, DURATION - t_pos)
        seg  = bass_note(bass, dur, amp=0.18)
        seg2 = bass_note(bass * 2, dur, amp=0.08)
        start = int(t_pos * SR)
        end   = start + len(seg)
        if end > total_samples: end = total_samples; seg = seg[:end-start]; seg2 = seg2[:end-start]
        track[start:end] += seg + seg2
        t_pos += CHORD_DUR * 2

# ── Accords Pad ──────────────────────────────────────────────────────────────
print("  Pads harmoniques...")
t_pos = 0
while t_pos < DURATION:
    for chord in PROGRESSIONS:
        if t_pos >= DURATION: break
        dur  = min(CHORD_DUR * 4, DURATION - t_pos)
        seg  = pad_chord(chord, dur, amp=0.18)
        start = int(t_pos * SR)
        end   = start + len(seg)
        if end > total_samples: end = total_samples; seg = seg[:end-start]
        track[start:end] += seg
        t_pos += CHORD_DUR * 4

# ── Shimmer haute fréquence ──────────────────────────────────────────────────
print("  Shimmer...")
t_pos = 0
shimmer_notes = [note_freq('A',5), note_freq('E',5), note_freq('C',5), note_freq('B',5)]
while t_pos < DURATION:
    for i, sn in enumerate(shimmer_notes):
        if t_pos >= DURATION: break
        dur  = min(CHORD_DUR * 2, DURATION - t_pos)
        seg  = shimmer(sn, dur, amp=0.05)
        start = int(t_pos * SR)
        end   = start + len(seg)
        if end > total_samples: end = total_samples; seg = seg[:end-start]
        track[start:end] += seg
        t_pos += CHORD_DUR * 2

# ── Fade in / fade out ───────────────────────────────────────────────────────
fade_dur = int(SR * 4)
track[:fade_dur]  *= np.linspace(0, 1, fade_dur)
track[-fade_dur:] *= np.linspace(1, 0, fade_dur)

# ── Normalisation ─────────────────────────────────────────────────────────────
track = track / (np.max(np.abs(track)) + 1e-9) * 0.85
track = np.clip(track, -1.0, 1.0)

# ── Export WAV ───────────────────────────────────────────────────────────────
print(f"  Export WAV -> {OUTPUT}")
with wave.open(OUTPUT, 'w') as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    stereo = np.column_stack([track, track])
    packed = (stereo * 32767).astype(np.int16)
    wf.writeframes(packed.tobytes())

size = os.path.getsize(OUTPUT) / (1024*1024)
print(f"  Musique generee : {size:.1f} Mo")

# Prévisualiser
os.startfile(OUTPUT)
