import numpy as np, sys
RES = [(120,6,1.4),(200,4,.9),(395,5,.8),(595,6,1.0),(800,3,.1)]
from scipy.signal import lfilter
sr = 48000; rng = np.random.default_rng(1)
def bq(kind, f0, Q):   # RBJ cookbook, as Web Audio's BiquadFilterNode
    w = 2*np.pi*f0/sr; a = np.sin(w)/(2*Q); c = np.cos(w)
    if kind == "bandpass": b = [a, 0, -a]
    elif kind == "lowpass": b = [(1-c)/2, 1-c, (1-c)/2]
    else: b = [(1+c)/2, -(1+c), (1+c)/2]
    A = [1+a, -2*c, 1-a]; return np.array(b)/A[0], np.array(A)/A[0]
def envelope(n_len, peak, att, dec):
    t = np.arange(n_len)/sr; e = np.where(t < att, peak*(t/att), peak*np.exp(-np.log(1e4)*(t-att)/dec)); return e
def impulse(peak, dur):
    n = int((dur+0.01)*sr); return rng.uniform(-1,1,n)*envelope(n, peak, 0.0003, dur)
T = 30.0; N = int(T*sr); body_in = np.zeros(N); direct = np.zeros(N)
def add(buf, t, sig): i = int(t*sr); j = min(N, i+len(sig)); buf[i:j] += sig[:j-i]
def filt(kind, f0, Q, sig): b, a = bq(kind, f0, Q); return lfilter(b, a, sig)
def step(t, vol=1): add(body_in, t, impulse(4.0*vol, 0.0015)); add(direct, t, filt("bandpass", 5000, 1, impulse(.05*vol, .0015)))
def seek(n, t):
    for _ in range(n): step(t, .75+.25*rng.random()); t += .005*(.95+.1*rng.random())
    return t
def clack(t, vol=1):
    add(direct, t, filt("bandpass", 560, 3, impulse(.9*vol, .014))); add(direct, t, filt("bandpass", 1100, 3, impulse(.5*vol, .012)))
    add(direct, t, filt("bandpass", 5000, 1, impulse(.35*vol, .004))); add(body_in, t, impulse(1.2*vol, .0015))
    if rng.random() < .35: thump(t, .9*vol)
def thump(t, vol=1): add(direct, t, filt("lowpass", 110, .8, impulse(1.6*vol, .036)))
# activity like chatter(): bursts with 60-105 ms gaps, odd pause/clack/thump
t = 0.3; clack(0.15, .8)
def gap_in_run():
    r = rng.random()
    return .005 if r < .35 else (.007 + .004*rng.random() if r < .6 else .012 + .038*rng.random())
while t < T - 0.3:
    r = rng.random()
    if r < .84:                                   # a short run of 1-4 steps
        for k in range(1 + int(rng.random()*rng.random()*5)):
            step(t, .7 + .3*rng.random()); t += gap_in_run()
    elif r < .92:                                 # a real seek: 8-22 steps, 5 ms apart
        t = seek(8 + int(15*rng.random()), t)
    elif r < .98: clack(t, .6 + .4*rng.random())
    else: thump(t, .8)
    t += .1 + (.15 + .75*rng.random()) * (1 if rng.random() < .7 else 2.5)   # pause between runs
body = sum(g*filt("bandpass", f, q, body_in) for f, q, g in RES)
tt = np.arange(N)/sr; mod = (1 + .2*np.sin(2*np.pi*5*tt))
motor = .02*mod*(sum(a*np.sin(2*np.pi*f*tt) for f, a in [(90,.15),(120,.2)]) + 4.2*filt("bandpass", 180, 1.0, rng.uniform(-1,1,N)) + 1.0*filt("bandpass", 380, 1.5, rng.uniform(-1,1,N)) + 0.6*filt("bandpass", 700, 1.2, rng.uniform(-1,1,N)))
y = 0.9*(body + direct + motor)
print("raw peak", float(np.abs(y).max()), "rms", float(np.sqrt(np.mean(y**2))))
import wave; w = wave.open("synth.wav","wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
s16 = (np.clip(y/np.abs(y).max()*0.7, -1, 1)*32767).astype(np.int16); w.writeframes(np.repeat(s16, 2).tobytes()); w.close()
print("wrote synth.wav", round(T,1), "s")
