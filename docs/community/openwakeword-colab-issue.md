<!--
Posted 2026-10-12 as https://github.com/alfiedennen/openwakeword-colab-2026/issues/9
(this file matches the posted text). Originally drafted for alfiedennen/openwakeword-colab-2026.
Title (paste into the issue's title box):

  Surviving Colab disconnects: fallback runtime, ESC-50 instead of FMA, aria2c for ACAV, Drive checkpoints

Body: everything below the line.
-->

---

Thanks for this notebook. We used it to train two custom wake words ("ahoy captain jack" and "goodnight jack") for a voice-controlled animatronic parrot, and it got us there. Along the way we kept losing runs to random **"hosted runtime disconnected"** errors partway through. These are the changes that finally got us two clean, validated models. They're posted as an issue, not a PR, because the pull requests here look unattended. Anyone else stuck can paste the cells in.

None of this overlaps with the Python 3.13 dependency fixes in #1/#3/#4/#5. Fix 1 below is an alternative to those.

Tested Oct 2026 on Colab Pay-As-You-Go with an L4 GPU. Both phrases trained successfully with these changes.

## 1. Skip the Python 3.13 dependency fight: use the fallback runtime

Before running anything: **Command Palette (`Ctrl+Shift+P`) → "Use fallback runtime version"**, then pick the oldest snapshot offered (for us, **2026.04 → Python 3.12**).

On the current default runtime (Python 3.13) we needed about 30 patch-and-restart cycles, and `piper-phonemize` still ended up with an ABI mismatch (`undefined symbol: espeak_TextToPhonemesWithTerminator`). On the 3.12 snapshot, the unmodified install cells ran through without a fatal error. Colab will eventually drop that snapshot, but while it's there this is the fastest fix.

## 2. Diagnosing the disconnects

The disconnects happened on free and Pay-As-You-Go, on GPU and CPU-only runtimes, with the tab focused and the mouse moving, with 59 GB of disk free and 98+ compute units left. Colab never gave a reason. They landed in different cells on different attempts (7, 8, 10, 11, 12), which looks like a **total session-duration cap**, not a bug in any one cell. That can't be fixed from inside the notebook, so the fixes below make the run shorter and make each expensive step's output survive a disconnect.

## 3. Section 7: download ACAV with `aria2c` and drop FMA

The 17 GB ACAV download over a single `requests` stream was slow enough that a disconnect usually hit it mid-download. `aria2c` with 16 connections is much faster and resumes with `-c`. FMA's 8 GB zip comes from a university server that was slow and unreliable for us, so we replaced it with ESC-50 (see section 4). Replace section 7's code cell with:

```python
import os, subprocess
os.chdir('/content')

# Install aria2 (fast parallel/multi-connection downloader) once.
subprocess.run(['apt-get', 'update', '-qq'], check=False)
subprocess.run(['apt-get', 'install', '-y', 'aria2'], check=False)

# ACAV features (17 GB) - the actual negative training corpus.
ACAV_FULL = '/content/openwakeword_features_ACAV100M_2000_hrs_16bit.npy'
ACAV_URL = 'https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/main/openwakeword_features_ACAV100M_2000_hrs_16bit.npy'
if os.path.exists(ACAV_FULL) and os.path.getsize(ACAV_FULL) > 16_000_000_000:
    print(f'  cached: ACAV {os.path.getsize(ACAV_FULL)/1e9:.1f} GB')
else:
    print('  ACAV: fetching with aria2 (16 parallel connections)...')
    result = subprocess.run([
        'aria2c', '-x16', '-s16', '-c',
        '--max-tries=5', '--retry-wait=5',
        '-d', '/content',
        '-o', 'openwakeword_features_ACAV100M_2000_hrs_16bit.npy',
        ACAV_URL
    ])
    if result.returncode != 0:
        raise RuntimeError(f'aria2c failed with exit code {result.returncode}')
    print(f'  done ACAV: {os.path.getsize(ACAV_FULL)/1e9:.1f} GB')

# FMA skipped - background-noise augmentation only, not the negative
# corpus itself. Keep the directory so later cells that just check it
# exists don't fail outright.
FMA_DIR = '/content/fma'
os.makedirs(FMA_DIR, exist_ok=True)
print('  FMA skipped (background-noise augmentation only)')
```

## 4. Section 8: use ESC-50 for background noise

[ESC-50](https://github.com/karoldvl/ESC-50) (2,000 five-second environmental-sound clips, a ~600 MB zip on GitHub) does the same job FMA did: background noise for augmentation. It's not the negative corpus, which is ACAV. The cell keeps the output directory name `/content/fma_wav` so nothing downstream has to change, and it skips files already converted when re-run. Replace section 8's code cell with:

```python
import os, glob, subprocess, zipfile, requests
from tqdm.auto import tqdm

out_dir = '/content/fma_wav'
os.makedirs(out_dir, exist_ok=True)
n_existing = len(os.listdir(out_dir))
if n_existing >= 1500:
    print(f'  cached: {n_existing} noise WAVs')
else:
    # FMA replaced with ESC-50 (environmental sounds): a single ~600MB
    # zip on GitHub, far smaller/more reliable than FMA's 8GB
    # university-hosted zip. Same role - background-noise augmentation,
    # not the negative training corpus itself.
    ESC50_ZIP = '/content/esc50.zip'
    ESC50_DIR = '/content/ESC-50-master'
    if not os.path.isdir(ESC50_DIR):
        if not os.path.exists(ESC50_ZIP):
            print('  fetching ESC-50 (~600 MB)...')
            with requests.get('https://github.com/karoldvl/ESC-50/archive/master.zip',
                               stream=True, timeout=120) as r:
                r.raise_for_status()
                total = int(r.headers.get('content-length', 0))
                with open(ESC50_ZIP, 'wb') as f, tqdm(total=total, unit='B',
                                                        unit_scale=True, unit_divisor=1024,
                                                        desc='ESC-50') as pbar:
                    for chunk in r.iter_content(chunk_size=4*1024*1024):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
        print('  extracting ESC-50...')
        with zipfile.ZipFile(ESC50_ZIP) as zf:
            zf.extractall('/content')
        os.remove(ESC50_ZIP)

    srcs = glob.glob(f'{ESC50_DIR}/audio/*.wav')
    if len(srcs) < 100:
        raise RuntimeError(f'ESC-50 extraction looks wrong - only {len(srcs)} WAVs found')
    existing = set(os.listdir(out_dir))
    n_target = min(1500, len(srcs))
    to_convert = [(i, srcs[i]) for i in range(n_target) if f'{i:05d}.wav' not in existing]
    print(f'  Converting {len(to_convert)} WAVs -> 16kHz mono (skipping {n_target - len(to_convert)} cached)')
    for i, src in tqdm(to_convert):
        out = f'{out_dir}/{i:05d}.wav'
        try:
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', src,
                            '-ac', '1', '-ar', '16000', out],
                           check=False, timeout=30, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            print(f'  skipped (ffmpeg timeout): {src}')
    print(f'  done: {len(os.listdir(out_dir))} noise WAVs ready')
```

Licensing: ESC-50 is CC BY-NC 3.0 (non-commercial). It's fine for hobby projects, but check whether that matters for yours.

## 5. Checkpoint expensive outputs to Google Drive

A disconnect wipes `/content`. These cells save each expensive step's output to Drive **as one zip file** and restore it at the start of a fresh session. The existing skip-if-cached logic in sections 8 and 11 then skips work that's already done. Writing thousands of small clip files straight to the Drive mount doesn't work well. A single zip written after the step finishes worked reliably.

Set `CKPT_DIR` to any Drive folder you like. A dedicated Google account just for this works fine.

**(a) New cell after section 7: mount Drive and restore the noise WAVs**

```python
import os, zipfile
from google.colab import drive
drive.mount('/content/drive')

CKPT_DIR = '/content/drive/MyDrive/oww_checkpoints'
os.makedirs(CKPT_DIR, exist_ok=True)

zip_path = f'{CKPT_DIR}/fma_wav.zip'
out_dir = '/content/fma_wav'
os.makedirs(out_dir, exist_ok=True)
if os.path.exists(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)
    print(f'Restored {len(os.listdir(out_dir))} fma_wav files from Drive')
else:
    print('No fma_wav checkpoint found - section 8 will convert from scratch')
```

**(b) New cell after section 8: checkpoint the noise WAVs**

```python
import os, zipfile

zip_path = f'{CKPT_DIR}/fma_wav.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zf:
    for fn in os.listdir('/content/fma_wav'):
        zf.write(f'/content/fma_wav/{fn}', fn)
print(f'Checkpointed fma_wav to {zip_path} ({os.path.getsize(zip_path)/1e6:.1f} MB)')
```

**(c) New cell after section 10: restore the TTS clips**

```python
import yaml, os, zipfile

with open('/content/my_model.yaml') as f:
    cfg = yaml.safe_load(f)

# generate_clips() writes to output_dir/model_name/<category> no matter
# what the *_clips_*_dir keys say, so pin those keys to the real location.
real_root = os.path.join(cfg['output_dir'], cfg['model_name'])
categories = ('positive_train', 'positive_test', 'negative_train', 'negative_test')
keys = ('positive_clips_train_dir', 'positive_clips_test_dir',
        'negative_clips_train_dir', 'negative_clips_test_dir')
for key, name in zip(keys, categories):
    cfg[key] = os.path.join(real_root, name)
with open('/content/my_model.yaml', 'w') as f:
    yaml.safe_dump(cfg, f)

zip_path = f'{CKPT_DIR}/{cfg["model_name"]}_clips.zip'
if os.path.exists(zip_path):
    os.makedirs(real_root, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(real_root)
    print(f'Restored clips to {real_root}')
else:
    print('No clips checkpoint found - section 11 will generate from scratch')
```

**(d) New cell after section 11, and the same cell again after section 12: checkpoint the TTS clips**

Running it again after section 12 saves the 16 kHz resampled versions, so the resample step doesn't have to be redone either.

```python
import yaml, os, zipfile

with open('/content/my_model.yaml') as f:
    cfg = yaml.safe_load(f)

real_root = os.path.join(cfg['output_dir'], cfg['model_name'])
categories = ('positive_train', 'positive_test', 'negative_train', 'negative_test')

zip_path = f'{CKPT_DIR}/{cfg["model_name"]}_clips.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zf:
    for name in categories:
        d = os.path.join(real_root, name)
        for fn in os.listdir(d):
            zf.write(os.path.join(d, fn), os.path.join(name, fn))
print(f'Checkpointed clips to {zip_path} ({os.path.getsize(zip_path)/1e6:.1f} MB)')
```

On a fresh session after a disconnect, run every cell top to bottom again. The restore cells and the existing cache checks make the steps that already finished take seconds.

## 6. Two smaller notes

- **Clip directory pitfall.** openWakeWord's `train.py` `generate_clips` always writes to `output_dir/model_name/<category>` and ignores the `positive_clips_train_dir`-style keys in `my_model.yaml`. The notebook's defaults happen to match, so nothing breaks out of the box. But if you edit those keys, for example to point them at Drive, the section 11 cache check looks in one place while the clips are written somewhere else, and it looks like nothing was generated. Cell (c) above keeps the two in sync.
- **The last FP/hour line in section 15 is misleading.** `ACAV val FP/hour at 0.5: {history["val_fp_per_hour"][-1]}` prints the *last training step's* value, not the exported checkpoint's. We saw it print 0.50 and 0.70 when the selected checkpoints were actually 0.05 and 0.10. The exported model's real numbers are the ones printed in the checkpoint-selection lines just above it. Also, "no checkpoint qualified — fell back to single best" came up on both of our runs. With only about 25 checkpoints the three-way percentile filter is strict, and the fallback still gave good models, so it isn't a cause for alarm.

Training on L4 (section 14) took about 2.5 minutes, not 30–40. The per-checkpoint metrics showed real convergence, so it wasn't skipping anything; the model is just small.

---

*These fixes and this write-up were worked out by Claude (Anthropic's AI assistant, via Claude Code) during a debugging session. A human ran the notebook and reported back what happened. The code is what actually trained the two models; the only changes for posting are generic Drive paths and a few small cells merged together.*
