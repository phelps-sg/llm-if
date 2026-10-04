# Floppy-drive sound tuning

The web terminal's disk sound (`Floppy` in `web/static/index.html`) is synthesised
with Web Audio and was tuned against a recording of a real 5.25" drive. The
recording isn't included (it isn't ours to redistribute); fetch one into this
directory as `floppy.wav`, e.g.

    uvx yt-dlp --js-runtimes node -x --audio-format wav -o "floppy.%(ext)s" <url>

- `simulate.py` — a Python model of the exact Web Audio graph (RBJ biquads, as
  `BiquadFilterNode`), writing `synth.wav`. Keep its numbers in step with the page.
- `bands.py floppy.wav synth.wav` — click rate, click/quiet band energies, levels.
- `onsets.py floppy.wav synth.wav` — rhythm: click rate, inter-onset intervals and
  runs, detected on the high-passed signal (a plain RMS envelope rides the
  90-120 Hz hum and reports bogus 4-5 ms "steps").

    uv run --with numpy --with scipy python simulate.py
    uv run --with numpy --with scipy python bands.py floppy.wav synth.wav

What the recording showed: sparse activity (~4 steps/s in runs of 1-4, long
pauses); seeks at 5 ms/step whose energy is a mid-range growl (500-1000 Hz,
peaks 120/395/595 Hz) ~13 dB over the motor; a motor that is a low hum and noise
band (90/120 Hz, mostly 120-250 Hz); broad clacks, some with a 50-110 Hz thump.
