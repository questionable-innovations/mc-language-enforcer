# Research: can a Minecraft server tell Mandarin from English?

This folder is the experiment behind the sidecar's design. It runs every test clip through Simple Voice
Chat's audio path (48 kHz Opus, VOIP mode, 20 ms frames, 24 kbps) and asks language-ID models what they hear.

## The problem: language ID alone punishes learners

There is no open corpus of English speakers learning Mandarin, so learner speech is approximated three ways:
English TTS voices reading pinyin respelled the way an anglophone says it, the same voices reading raw toneless
pinyin, and real native Mandarin (FLEURS) with its pitch flattened (no tones). With "punish if P(Mandarin) < 0.1":

| Model | Learner proxy wrongly flagged | Native Mandarin wrongly flagged (2 s clip) |
|---|---|---|
| ECAPA VoxLingua107 | 99% | 8% |
| Whisper tiny | 44% | 7% |
| Whisper base | 68% | 7% |
| Whisper small | 72% | 7% |
| Whisper medium | 83% | 7% |

A better model is *more* certain that a beginner sounds English. That's correct, and useless here.

## The fix: punish only intelligible English

Second stage: force Whisper to transcribe the utterance as English, and punish only if that transcript is
confident (average token log-prob ≥ −0.4) and made of real words. Learner Mandarin, however English it sounds,
doesn't transcribe into confident English ("Gun Wallet", "Shao Shinyo Kuli Pa").

Whisper small, whole utterances, % flagged:

| Set | n | Language ID only | Two-stage |
|---|---|---|---|
| Native Mandarin (FLEURS) | 150 | 0% | **0%** |
| Native Mandarin, game phrases (TTS) | 120 | 0% | **0%** |
| Mandarin, tones removed | 150 | 0% | **0%** |
| Learner proxy, respelled pinyin | 120 | 72% | **5%** |
| Learner proxy, raw pinyin | 120 | 78% | **6%** |
| English (FLEURS) | 150 | 100% | **99%** |
| English, game phrases (TTS) | 120 | 100% | **96%** |
| Chinese-accented English, read (L2-ARCTIC) | 120 | 89% | 79% |
| Chinese-accented English, spontaneous (L2-ARCTIC) | 44 | 96% | 75% |
| Japanese / Korean / Vietnamese / Spanish | 60 each | 100% | 100% |
| German | 60 | 100% | 98% |
| Cantonese | 60 | 0% | 0% (counts as Chinese) |

The leniency costs some accented English, which is acceptable for a server of English speakers learning Mandarin.
The cut-off was picked on this data (a round number, one knob: `LE_MIN_LP`).

## Speed

Median time to fully judge a 3 s utterance (language ID plus both forced decodes), in ms:

| Model | RTX 3090 float32 | GTX 1080 (estimated ×3.5) | CPU, 4 threads, int8 |
|---|---|---|---|
| tiny | 49 | ~170 | 612 |
| base | 85 | ~300 | 1025 |
| small | 219 | ~770 | 3366 |
| medium | 578 | ~2000 | — |
| large-v3-turbo | 700 | ~2450 | — |

Most Mandarin stops after language ID, about a quarter of the total. Hence the defaults: `small` on a GPU,
`base` on CPU. The GTX 1080 numbers are estimated, but its kernels are verified: CTranslate2 4.9.1, cuBLAS 12.9
and cuDNN 9.10.2.21 all ship `sm_61` code (checked with `cuobjdump`). Later cuDNN 9 releases drop it from
`libcudnn_cnn`, and current PyTorch wheels start at `sm_75`, so the sidecar pins cuDNN and avoids PyTorch.

## Reproducing

```bash
uv sync
python fetch_fleurs.py data/fleurs cmn_hans_cn:160 en_us:160 yue_hant_hk:60 ja_jp:60 ko_kr:60 es_419:60 vi_vn:60 de_de:60
python make_synthetic.py data/voices data/fleurs data/synth      # Piper voices in data/voices
python prep.py data/prepped data/fleurs data/synth               # SVC Opus round-trip
python eval_lid.py data/prepped data/results ecapa whisper-tiny whisper-base whisper-small whisper-medium
python eval_verdict.py data/prepped data/results whisper-small
python bench_latency.py data/prepped data/results/latency.csv
python analyze.py data/results report/report.json
```

L2-ARCTIC (CC BY-NC 4.0) must be requested from its authors; `make_l2.py` builds the accented-English sets from it.
Raw results from the run above are in `report/`.
