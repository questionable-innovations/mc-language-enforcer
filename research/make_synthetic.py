"""Build the learner-proxy test sets.

There is no open corpus of English speakers' learner Mandarin, so we approximate it:
  phr_zh_native   - native Mandarin TTS reading the phrases (control)
  phr_zh_learner  - English voices reading pinyin respelled the way an English speaker would say it
  phr_zh_pinyin   - English voices reading raw toneless pinyin (first-day beginner, worst case)
  phr_en          - English voices reading the English phrases (the thing we must catch)
  fleurs_zh_flat  - real native FLEURS Mandarin with pitch flattened to a monotone (no tones)
"""
import csv, pathlib, sys

import numpy as np
import parselmouth
import soundfile as sf
from parselmouth.praat import call
from piper import PiperVoice
from pypinyin import Style, pinyin

from phrases import PHRASES

EN_VOICES = ["en_US-lessac-medium", "en_US-ryan-medium", "en_GB-alan-medium", "en_US-amy-medium", "en_US-joe-medium"]
ZH_VOICES = ["zh_CN-huayan-medium", "zh_CN-chaowen-medium"]

INITIALS = {"q": "ch", "x": "sh", "zh": "j", "c": "ts", "z": "dz"}
FINALS = {
    "a": "ah", "o": "aw", "e": "uh", "i": "ee", "u": "oo", "v": "ew", "ai": "eye", "ei": "ay", "ao": "ow",
    "ou": "oh", "an": "ahn", "en": "un", "ang": "ahng", "eng": "ung", "ong": "oong", "er": "ar",
    "ia": "yah", "ie": "yeh", "iao": "yow", "iu": "yoh", "iou": "yoh", "ian": "yen", "in": "een",
    "iang": "yahng", "ing": "eeng", "iong": "yoong", "ua": "wah", "uo": "waw", "uai": "why",
    "ui": "way", "uei": "way", "uan": "wahn", "un": "wun", "uen": "wun", "uang": "wahng",
    "ue": "yweh", "ve": "yweh",
}
PALATAL = {"j", "q", "x", "y"}


def respell(syl_initial: str, syl_final: str) -> str:
    """Toneless pinyin syllable -> English-ish spelling, as a learner who knows the pinyin rules would say it."""
    ini = INITIALS.get(syl_initial, syl_initial)
    fin = syl_final
    if syl_initial in PALATAL and fin.startswith("u"):
        fin = {"u": "ew", "un": "ewn", "uan": "wen", "ue": "weh"}.get(fin, fin)
        return ini + fin
    if fin == "i" and syl_initial in {"zh", "ch", "sh", "r"}:
        return ini + "r"
    if fin == "i" and syl_initial in {"z", "c", "s"}:
        return ini + "uh"
    if syl_initial in {"y", "w"}:
        # y/w already carry the glide; drop the duplicated vowel glide from the final
        mapped = FINALS.get(fin, fin)
        if mapped.startswith(("y", "w")) and len(mapped) > 1:
            mapped = mapped[1:]
        return ini + mapped
    return ini + FINALS.get(fin, fin)


def to_learner(text: str) -> str:
    inis = pinyin(text, style=Style.INITIALS, strict=False)
    fins = pinyin(text, style=Style.FINALS, strict=False)
    out = []
    for i, f in zip(inis, fins):
        i, f = i[0], f[0]
        if not f or not f.isalpha():
            continue
        out.append(respell(i, f))
    return " ".join(out) + "."


def to_raw_pinyin(text: str) -> str:
    return " ".join(s[0] for s in pinyin(text, style=Style.NORMAL) if s[0].isalpha()) + "."


def synth(voice: PiperVoice, text: str) -> tuple[np.ndarray, int]:
    chunks = list(voice.synthesize(text))
    audio = np.concatenate([c.audio_float_array for c in chunks])
    return audio, chunks[0].sample_rate


def flatten_pitch(x: np.ndarray, sr: int) -> np.ndarray:
    snd = parselmouth.Sound(x.astype(np.float64), sr)
    manip = call(snd, "To Manipulation", 0.01, 75, 600)
    tier = call(manip, "Extract pitch tier")
    mean_f0 = call(tier, "Get mean (curve)", 0, 0)
    call(tier, "Formula", f"{mean_f0}")
    call([tier, manip], "Replace pitch tier")
    return call(manip, "Get resynthesis (overlap-add)").values[0].astype(np.float32)


def main(voices_dir: pathlib.Path, fleurs_dir: pathlib.Path, out: pathlib.Path):
    voices = {v: PiperVoice.load(str(voices_dir / f"{v}.onnx"), download_dir=voices_dir) for v in EN_VOICES + ZH_VOICES}
    sets = {
        "phr_zh_native": lambda zh, en, k: (ZH_VOICES[k % 2], zh),
        "phr_zh_learner": lambda zh, en, k: (EN_VOICES[k % 5], to_learner(zh)),
        "phr_zh_pinyin": lambda zh, en, k: (EN_VOICES[k % 5], to_raw_pinyin(zh)),
        "phr_en": lambda zh, en, k: (EN_VOICES[k % 5], en),
    }
    for name, pick in sets.items():
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        rows = []
        for idx, (zh, en) in enumerate(PHRASES):
            for rep in range(2):  # two different voices per phrase
                voice_name, text = pick(zh, en, idx * 2 + rep)
                audio, sr = synth(voices[voice_name], text)
                fn = f"{idx:02d}_{rep}.wav"
                sf.write(d / fn, audio, sr)
                rows.append({"file": fn, "text": text, "voice": voice_name})
        with open(d / "meta.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["file", "text", "voice"]); w.writeheader(); w.writerows(rows)
        print(name, len(rows), "e.g.", rows[2]["text"], flush=True)

    d = out / "fleurs_zh_flat"
    d.mkdir(parents=True, exist_ok=True)
    src = fleurs_dir / "cmn_hans_cn"
    rows = list(csv.DictReader(open(src / "meta.csv")))
    for r in rows:
        x, sr = sf.read(src / r["file"], dtype="float32")
        sf.write(d / r["file"], flatten_pitch(x, sr), sr)
    with open(d / "meta.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "text"]); w.writeheader(); w.writerows(rows)
    print("fleurs_zh_flat", len(rows), flush=True)


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]))
