"""Score every prepped clip with each language-ID model at several utterance lengths.

Output: results/<model>.csv with per-clip language probabilities.
Usage: eval_lid.py <prepped_dir> <results_dir> <model> [<model> ...]
"""
import csv, os, pathlib, sys, time

import numpy as np

DURS = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, None]  # None = whole utterance
KEEP = ["zh", "en", "yue", "ja", "ko", "es", "vi", "de"]
WHISPER = {
    "whisper-tiny": "tiny", "whisper-base": "base", "whisper-small": "small",
    "whisper-medium": "medium", "whisper-turbo": "large-v3-turbo", "whisper-large-v3": "large-v3",
}
SR = 16000


def load_sets(prepped: pathlib.Path):
    for meta_path in sorted(prepped.glob("*.csv")):
        audio = np.load(prepped / f"{meta_path.stem}.npz")
        for row in csv.DictReader(open(meta_path)):
            yield row, audio[row["file"]]


def jobs(prepped: pathlib.Path):
    for row, x in load_sets(prepped):
        for d in DURS:
            if d is None:
                yield row, "full", x[: 30 * SR]
            elif len(x) >= d * SR:
                yield row, str(d), x[: int(d * SR)]


class WhisperLID:
    def __init__(self, size: str):
        from faster_whisper import WhisperModel
        self.m = WhisperModel(size, device="cuda", compute_type="float16")

    def probs(self, batch: list[np.ndarray]) -> list[dict[str, float]]:
        from faster_whisper.audio import pad_or_trim
        fe = self.m.feature_extractor
        feats = np.stack([pad_or_trim(fe(x)[..., : fe.nb_max_frames]) for x in batch])
        out = self.m.model.detect_language(self.m.encode(feats))
        return [{tok[2:-2]: p for tok, p in res} for res in out]


class EcapaLID:
    def __init__(self, savedir: pathlib.Path):
        import torch
        from speechbrain.inference.classifiers import EncoderClassifier
        self.torch = torch
        self.m = EncoderClassifier.from_hparams(
            source="speechbrain/lang-id-voxlingua107-ecapa", savedir=str(savedir), run_opts={"device": "cuda"})
        labels = self.m.hparams.label_encoder
        self.codes = [labels.ind2lab[i].split(":")[0] for i in range(len(labels.ind2lab))]

    def probs(self, batch: list[np.ndarray]) -> list[dict[str, float]]:
        torch = self.torch
        n = max(len(x) for x in batch)
        wavs = torch.zeros(len(batch), n)
        for i, x in enumerate(batch):
            wavs[i, : len(x)] = torch.from_numpy(x)
        lens = torch.tensor([len(x) / n for x in batch])
        with torch.no_grad():
            logp = self.m.classify_batch(wavs, lens)[0]
        p = torch.softmax(logp, dim=-1).cpu().numpy()
        return [dict(zip(self.codes, row.tolist())) for row in p]


def main(prepped: pathlib.Path, out: pathlib.Path, models: list[str]):
    out.mkdir(parents=True, exist_ok=True)
    all_jobs = list(jobs(prepped))
    for name in models:
        model = EcapaLID(out.parent / "models" / "ecapa") if name == "ecapa" else WhisperLID(WHISPER[name])
        # Sort by length so ECAPA batches carry little padding; Whisper always pads to 30 s anyway.
        order = sorted(range(len(all_jobs)), key=lambda i: len(all_jobs[i][2]))
        rows, t0, bs = [None] * len(all_jobs), time.time(), int(os.environ.get("LID_BATCH", "32"))
        for s in range(0, len(order), bs):
            idx = order[s: s + bs]
            for i, pr in zip(idx, model.probs([all_jobs[i][2] for i in idx])):
                meta, dur, x = all_jobs[i]
                top = max(pr, key=pr.get)
                rows[i] = {"model": name, "set": meta["set"], "file": meta["file"], "label": meta["label"],
                           "dur": dur, "secs": round(len(x) / SR, 3), "top": top, "top_p": round(pr[top], 5),
                           **{f"p_{k}": round(pr.get(k, 0.0), 5) for k in KEEP}}
        with open(out / f"{name}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
        print(f"{name}: {len(rows)} scored in {time.time() - t0:.0f}s", flush=True)
        del model


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3:])
