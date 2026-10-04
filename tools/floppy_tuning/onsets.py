import numpy as np, wave, sys
from scipy.signal import butter, sosfilt
def load(fn):
    w = wave.open(fn); sr = w.getframerate()
    return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2).mean(1)/32768, sr
for fn in sys.argv[1:]:
    x, sr = load(fn)
    hp = sosfilt(butter(4, 1000, "highpass", fs=sr, output="sos"), x)
    hop = int(.001*sr)
    env = np.sqrt(np.convolve(hp**2, np.ones(hop)/hop, mode="same"))[::hop]
    db = 20*np.log10(env+1e-9); floor = np.percentile(db, 30)
    on = []
    for i in range(3, len(db)):
        if db[i] > floor + 10 and db[i] - db[i-3:i].min() > 8 and (not on or i - on[-1] > 2):
            on.append(i)
    t = np.array(on)*.001; ioi = np.diff(t)*1000
    hist, e = np.histogram(ioi, bins=[0,3,4,5,6,8,10,12,15,20,30,50,100,200,500,5000])
    print(f"{fn}: {len(on)} onsets in {len(x)/sr:.0f}s ({len(on)/(len(x)/sr):.0f}/s); IOI p10/25/50/75/90 ms:",
          np.round(np.percentile(ioi,[10,25,50,75,90]),1))
    print("   IOI hist:", {f"{e[i]:.0f}-{e[i+1]:.0f}": int(h) for i, h in enumerate(hist) if h})
    tr, cur = [], [t[0]]
    for a, b in zip(t[:-1], t[1:]):
        if b-a > .1: tr.append(cur); cur = [b]
        else: cur.append(b)
    tr.append(cur); L = [len(c) for c in tr]
    print(f"   runs (split at >100 ms gaps): {len(tr)}; onsets/run p25/50/75/max {np.percentile(L,[25,50,75,100])}")
    # within dense runs: period by autocorrelation of the HP envelope over the busiest 1 s
    best = max(range(0, len(env)-1000, 250), key=lambda i: (db[i:i+1000] > floor+10).sum())
    seg = env[best:best+1000] - env[best:best+1000].mean(); ac = np.correlate(seg, seg, "full")[999:]; ac /= ac[0]
    lag = np.argmax(ac[2:60]) + 2
    print(f"   busiest second at {best/1000:.1f}s: HP-envelope period {lag} ms (ac {ac[lag]:.2f})")
