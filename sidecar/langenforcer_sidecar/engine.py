"""faster-whisper wrapper: language probabilities plus lazy forced-language transcripts."""
from __future__ import annotations

import ctypes
import glob
import logging
import os
from dataclasses import dataclass

import numpy as np

log = logging.getLogger(__name__)
SAMPLE_RATE = 16000


def preload_cuda_libs() -> None:
    """Load pip-installed cuBLAS/cuDNN so CTranslate2 finds them without LD_LIBRARY_PATH."""
    try:
        import nvidia.cublas, nvidia.cudnn  # noqa: E401
    except ImportError:
        return
    for pkg in (nvidia.cublas, nvidia.cudnn):
        for lib in sorted(glob.glob(os.path.join(list(pkg.__path__)[0], "lib", "lib*.so.*"))):
            try:
                ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)
            except OSError as e:
                log.debug("could not preload %s: %s", lib, e)


def pick_device(device: str, compute_type: str) -> tuple[str, str]:
    import ctranslate2

    if device == "auto":
        device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    if compute_type == "auto":
        if device == "cpu":
            compute_type = "int8"
        else:
            # Pascal (GTX 10xx, sm_61) has no FP16 tensor cores; CTranslate2 only offers fp16 from Volta on
            compute_type = "float16" if "int8_float16" in ctranslate2.get_supported_compute_types("cuda") else "float32"
    return device, compute_type


@dataclass
class Analysis:
    probs: dict[str, float]
    seconds: float
    _engine: "Engine"
    _audio: np.ndarray
    _first: tuple[str, object] | None
    _cache: dict[str, tuple[str, float]]

    def decode(self, lang: str) -> tuple[str, float]:
        """Transcript forced to `lang`, with its token-weighted average log-probability."""
        if lang not in self._cache:
            if self._first and self._first[0] == lang:
                segments = self._first[1]
                self._first = None
            else:
                segments = self._engine.transcribe(self._audio, lang)[0]
            self._cache[lang] = _collect(segments)
        return self._cache[lang]


def _collect(segments) -> tuple[str, float]:
    segs = list(segments)
    ntok = sum(len(s.tokens) for s in segs)
    lp = sum(s.avg_logprob * len(s.tokens) for s in segs) / ntok if ntok else -10.0
    return " ".join(s.text.strip() for s in segs).strip(), lp


class Engine:
    def __init__(self, model: str, device: str = "auto", compute_type: str = "auto", cpu_threads: int = 4,
                 num_workers: int = 2, download_root: str | None = None):
        preload_cuda_libs()
        from faster_whisper import WhisperModel

        self.device, self.compute_type = pick_device(device, compute_type)
        if model == "auto":
            # small is the accuracy/latency sweet spot on a GTX 1080; on CPU only base keeps up in real time
            model = "small" if self.device == "cuda" else "base"
        self.model_name = model
        self.model = WhisperModel(model, device=self.device, compute_type=self.compute_type,
                                  cpu_threads=cpu_threads, num_workers=num_workers, download_root=download_root)
        log.info("loaded whisper %s on %s (%s)", model, self.device, self.compute_type)

    def transcribe(self, audio: np.ndarray, lang: str | None):
        return self.model.transcribe(audio, language=lang, beam_size=1, temperature=0.0, without_timestamps=True,
                                     condition_on_previous_text=False, vad_filter=False)

    def analyze(self, audio: np.ndarray) -> Analysis:
        audio = audio[: 30 * SAMPLE_RATE]
        # language=None runs language-ID; the returned generator decodes in the top language only if consumed
        segments, info = self.transcribe(audio, None)
        probs = dict(info.all_language_probs or [(info.language, info.language_probability)])
        return Analysis(probs, len(audio) / SAMPLE_RATE, self, audio, (info.language, segments), {})

    def warm_up(self) -> None:
        silence = np.zeros(SAMPLE_RATE, dtype=np.float32)
        self.analyze(silence).decode("en")
