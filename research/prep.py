"""Run every clip through the Simple Voice Chat audio path and cache it as 16 kHz float32.

SVC (2.6.x) encodes 48 kHz mono in 20 ms frames with Opus in VOIP mode and no explicit bitrate
(libopus picks ~32-50 kbps). We use 24 kbps to be a little pessimistic.
Leading/trailing silence is trimmed, as SVC voice activation only transmits once you speak.
"""
import csv, pathlib, subprocess, sys

import numpy as np
import soundfile as sf

LABELS = {
    "cmn_hans_cn": "zh", "en_us": "en", "yue_hant_hk": "yue", "ja_jp": "ja", "ko_kr": "ko",
    "es_419": "es", "vi_vn": "vi", "de_de": "de",
    "phr_zh_native": "zh", "phr_zh_learner": "zh", "phr_zh_pinyin": "zh", "phr_en": "en",
    "fleurs_zh_flat": "zh", "l2_zh_scripted": "en", "l2_zh_spont": "en",
}


def svc_roundtrip(path: pathlib.Path) -> np.ndarray:
    enc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", "48000", "-c:a", "libopus",
         "-application", "voip", "-frame_duration", "20", "-b:a", "24k", "-f", "ogg", "pipe:1"],
        check=True, capture_output=True).stdout
    dec = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", "pipe:0", "-ac", "1", "-ar", "16000", "-f", "f32le", "pipe:1"],
        input=enc, check=True, capture_output=True).stdout
    return np.frombuffer(dec, dtype=np.float32).copy()


def trim(x: np.ndarray, sr=16000, frame_ms=30, rel_db=-35.0, pad_ms=100) -> np.ndarray:
    n = sr * frame_ms // 1000
    frames = x[: len(x) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)
    active = np.where(db > db.max() + rel_db)[0]
    if len(active) == 0:
        return x
    pad = pad_ms * sr // 1000
    return x[max(0, active[0] * n - pad): min(len(x), (active[-1] + 1) * n + pad)]


def main(out: pathlib.Path, *roots: pathlib.Path):
    out.mkdir(parents=True, exist_ok=True)
    for root in roots:
        for d in sorted(p for p in root.iterdir() if p.is_dir() and p.name in LABELS):
            rows = list(csv.DictReader(open(d / "meta.csv")))
            arrays, meta = {}, []
            for r in rows:
                x = trim(svc_roundtrip(d / r["file"]))
                arrays[r["file"]] = x
                meta.append({"set": d.name, "file": r["file"], "label": LABELS[d.name],
                             "dur": round(len(x) / 16000, 3), "text": r["text"], "voice": r.get("voice", "")})
            np.savez(out / f"{d.name}.npz", **arrays)
            with open(out / f"{d.name}.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(meta[0])); w.writeheader(); w.writerows(meta)
            durs = [m["dur"] for m in meta]
            print(f"{d.name:16s} n={len(meta):3d} median_dur={np.median(durs):.2f}s", flush=True)


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]), *map(pathlib.Path, sys.argv[2:]))
