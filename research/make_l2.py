"""Build accented-English test sets from L2-ARCTIC's four native-Mandarin speakers (BWC, LXC, NCC, TXHC).

l2_zh_scripted - 30 read ARCTIC sentences per speaker
l2_zh_spont    - their spontaneous "suitcase story", split at pauses into 2-6 s utterances
L2-ARCTIC is CC BY-NC 4.0: used for evaluation only, never redistributed.
"""
import csv, pathlib, sys

import numpy as np
import soundfile as sf

SPEAKERS = ["BWC", "LXC", "NCC", "TXHC"]


def split_at_pauses(x: np.ndarray, sr: int, min_s=2.0, max_s=6.0, frame_ms=30, pause_ms=250):
    n = sr * frame_ms // 1000
    frames = x[: len(x) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)
    quiet = db < np.percentile(db, 90) - 30
    pause_frames = pause_ms // frame_ms
    chunks, start, run = [], 0, 0
    for i, q in enumerate(quiet):
        run = run + 1 if q else 0
        length = (i - start) * frame_ms / 1000
        if (run >= pause_frames and length >= min_s) or length >= max_s:
            chunks.append((start * n, i * n))
            start, run = i + 1, 0
    return [x[a:b] for a, b in chunks if (b - a) / sr >= min_s]


def main(raw: pathlib.Path, out: pathlib.Path):
    d = out / "l2_zh_scripted"; d.mkdir(parents=True, exist_ok=True)
    rows = []
    for spk in SPEAKERS:
        for wav in sorted((raw / spk / "wav").glob("*.wav"))[:30]:
            txt = (raw / spk / "transcript" / f"{wav.stem}.txt").read_text().strip()
            fn = f"{spk}_{wav.name}"
            audio, sr = sf.read(wav)
            sf.write(d / fn, audio, sr)
            rows.append({"file": fn, "text": txt})
    with open(d / "meta.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "text"]); w.writeheader(); w.writerows(rows)
    print("l2_zh_scripted", len(rows))

    d = out / "l2_zh_spont"; d.mkdir(parents=True, exist_ok=True)
    rows = []
    for spk in SPEAKERS:
        x, sr = sf.read(raw / "suitcase_corpus" / "wav" / f"{spk.lower()}.wav", dtype="float32")
        if x.ndim > 1:
            x = x.mean(axis=1)
        for i, chunk in enumerate(split_at_pauses(x, sr)):
            fn = f"{spk}_spont_{i:02d}.wav"
            sf.write(d / fn, chunk, sr)
            rows.append({"file": fn, "text": ""})
    with open(d / "meta.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "text"]); w.writeheader(); w.writerows(rows)
    print("l2_zh_spont", len(rows))


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
