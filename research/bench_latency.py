"""Per-utterance latency for the work the sidecar does: language-ID, and the forced en+zh dual decode.

Only Pascal-compatible compute types are timed (GTX 1080 = sm_61: no FP16 tensor cores),
plus CPU int8 as the "no GPU at all" floor.
Usage: bench_latency.py <prepped_dir> <out_csv>
"""
import csv, pathlib, statistics, sys, time

import numpy as np
from faster_whisper import WhisperModel

from eval_lid import WHISPER

CONFIGS = [("cuda", "float32"), ("cuda", "int8"), ("cpu", "int8")]
MODELS = ["whisper-tiny", "whisper-base", "whisper-small", "whisper-medium", "whisper-turbo"]


def timed(fn, reps):
    fn(); fn()  # warm-up
    ts = []
    for _ in range(reps):
        t = time.perf_counter(); fn(); ts.append((time.perf_counter() - t) * 1000)
    return statistics.median(ts)


def main(prepped: pathlib.Path, out: pathlib.Path):
    clip = np.load(prepped / "phr_en.npz")
    # a ~3 s utterance: two short phrases back to back
    x = np.concatenate([clip["00_0.wav"], clip["05_0.wav"]])[: 3 * 16000].astype(np.float32)
    rows = []
    for name in MODELS:
        for device, ctype in CONFIGS:
            if device == "cpu" and name in ("whisper-medium", "whisper-turbo"):
                continue
            m = WhisperModel(WHISPER[name], device=device, compute_type=ctype, cpu_threads=4)
            reps = 5 if device == "cpu" else 15
            lid = timed(lambda: m.detect_language(x), reps)
            dec = lambda lang: list(m.transcribe(x, language=lang, beam_size=1, temperature=0.0,
                                                  without_timestamps=True, condition_on_previous_text=False)[0])
            dual = timed(lambda: (dec("en"), dec("zh")), reps)
            rows.append({"model": name, "device": device, "compute": ctype, "lid_ms": round(lid, 1),
                         "dual_decode_ms": round(dual, 1)})
            print(rows[-1], flush=True)
            del m
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
