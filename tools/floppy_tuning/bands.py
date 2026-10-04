import numpy as np, wave, sys
from scipy.signal import butter, sosfilt
for fn in sys.argv[1:]:
    w = wave.open(fn); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, 2).mean(1)/32768
    hp = sosfilt(butter(4, 1000, "highpass", fs=sr, output="sos"), x); hop = int(.001*sr)
    env = np.sqrt(np.convolve(hp**2, np.ones(hop)/hop, mode="same"))[::hop]; db = 20*np.log10(env+1e-9)
    floor = np.percentile(db, 30)
    on = [i for i in range(3, len(db)) if db[i] > floor+10 and db[i]-db[i-3:i].min() > 8]
    on = [i for k, i in enumerate(on) if k == 0 or i - on[k-1] > 2]
    edges = [0,60,120,250,500,1000,2000,4000,8000,24000]
    def bandE(segs):
        n = len(segs[0]); f = np.fft.rfftfreq(n, 1/sr)
        m = np.mean([np.abs(np.fft.rfft(s*np.hanning(n)))**2 for s in segs], 0)
        e = [m[(f>=a)&(f<b)].sum() for a, b in zip(edges[:-1], edges[1:])]; tot = sum(e)
        return " ".join(f"{a}-{b}:{100*v/tot:.0f}%" for a, b, v in zip(edges[:-1], edges[1:], e)), (f*m).sum()/m.sum()
    clicks = [x[int(i*.001*sr):int(i*.001*sr)+1440] for i in on]; clicks = [c for c in clicks if len(c) == 1440]
    quiet_idx = [i for i in range(0, len(db)-200, 97) if db[i:i+180].max() < floor + 4][:60]
    quiet = [x[int(i*.001*sr):int(i*.001*sr)+8192] for i in quiet_idx]; quiet = [q for q in quiet if len(q) == 8192]
    cb, cc = bandE(clicks); print(f"{fn}: {len(on)/(len(x)/sr):.1f} clicks/s\n  CLICKS centroid {cc:.0f} Hz | {cb}")
    if quiet:
        qb, qc = bandE(quiet); print(f"  QUIET  centroid {qc:.0f} Hz | {qb}")
    print(f"  loudness: click-window rms / quiet rms = "
          f"{20*np.log10(np.sqrt(np.mean([np.mean(c**2) for c in clicks]))/np.sqrt(np.mean([np.mean(q**2) for q in quiet]))):.1f} dB" if quiet else "")
