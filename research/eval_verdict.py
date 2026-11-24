"""Stage 2: decode each utterance twice (forced English, forced Mandarin) and record transcript confidence.

The hypothesis: language-ID alone flags heavily accented learner Mandarin as English, but such audio is not
*intelligible* English, so Whisper's English transcript is low-confidence. The likelihood ratio
  llr = avg_logprob(zh decode) - avg_logprob(en decode)
should separate "speaking English" from "speaking bad Mandarin".

Usage: eval_verdict.py <prepped_dir> <results_dir> <model> [<model> ...]
"""
import csv, pathlib, re, sys, time

import numpy as np
from faster_whisper import WhisperModel
from wordfreq import zipf_frequency

from eval_lid import SR, WHISPER, load_sets

LONG_DURS = ["2.0", "3.0", "full"]  # streaming checkpoints for long read speech


def decode(m: WhisperModel, x: np.ndarray, lang: str) -> tuple[str, float, int]:
    segs, _ = m.transcribe(x, language=lang, beam_size=1, temperature=0.0, without_timestamps=True,
                           condition_on_previous_text=False, vad_filter=False)
    segs = list(segs)
    ntok = sum(len(s.tokens) for s in segs)
    lp = sum(s.avg_logprob * len(s.tokens) for s in segs) / ntok if ntok else -10.0
    return " ".join(s.text.strip() for s in segs), lp, ntok


def english_word_ratio(text: str) -> float:
    words = re.findall(r"[A-Za-z']+", text)
    if not words:
        return 0.0
    return sum(zipf_frequency(w.lower(), "en") >= 2.5 for w in words) / len(words)


def main(prepped: pathlib.Path, out: pathlib.Path, models: list[str]):
    items = []
    for row, x in load_sets(prepped):
        if row["set"].startswith("phr_"):
            items.append((row, "full", x))
        else:
            for d in LONG_DURS:
                items.append((row, d, x[: 30 * SR] if d == "full" else x[: int(float(d) * SR)]))
    for name in models:
        m = WhisperModel(WHISPER[name], device="cuda", compute_type="float16")
        t0, rows = time.time(), []
        for row, dur, x in items:
            en_text, en_lp, en_n = decode(m, x, "en")
            zh_text, zh_lp, zh_n = decode(m, x, "zh")
            rows.append({"model": name, "set": row["set"], "file": row["file"], "label": row["label"], "dur": dur,
                         "secs": round(len(x) / SR, 3), "en_lp": round(en_lp, 4), "zh_lp": round(zh_lp, 4),
                         "llr": round(zh_lp - en_lp, 4), "en_words": round(english_word_ratio(en_text), 3),
                         "en_tokens": en_n, "zh_tokens": zh_n, "en_text": en_text, "zh_text": zh_text})
        with open(out / f"verdict-{name}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        print(f"{name}: {len(rows)} verdicts in {time.time() - t0:.0f}s", flush=True)
        del m


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3:])
