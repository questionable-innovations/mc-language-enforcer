"""Verdict logic: does this utterance break the speaker's rules?

Pure functions over language probabilities and lazily-produced transcripts, so it is testable
without a model. The thresholds come from research/ (see research/report): language-ID alone
flags 72-78% of learner Mandarin as English, so English is only punished when the forced English
transcript is confident, real English.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable

import wordfreq

# Varieties Whisper splits that a learner's flag should treat as one language
FAMILIES = {"zh": {"zh", "yue"}, "yue": {"yue", "zh"}, "no": {"no", "nn"}, "nn": {"nn", "no"}}

# "Rock" mode: the N most common English words, plus what a caveman needs to say
CAVEMAN_WORDS = {
    "rock", "rocks", "fire", "eat", "food", "meat", "kill", "hit", "smash", "sleep", "dig", "cave", "hunt",
    "stone", "wood", "tree", "ugh", "ooga", "booga", "grunt", "me", "you", "big", "small", "good", "bad",
    "hmm", "grr", "huh", "argh", "oof", "ooh",
}

Decoder = Callable[[str], tuple[str, float]]  # language -> (transcript, average token log-prob)


@dataclass(frozen=True)
class Thresholds:
    tau: float = 0.1  # P(allowed languages) below this makes the utterance suspicious
    tau_other: float = 0.02  # a non-English language must be this clear-cut...
    min_top_other: float = 0.7  # ...and this confident to be punished
    min_lp: float = -0.4  # forced English transcript must be at least this confident
    lp_span: float = 0.35  # severity ramps from min_lp up to min_lp + lp_span
    min_words: float = 0.6  # share of the English transcript that must be real words
    vocab_min_lp: float = -0.6  # only police vocabulary on intelligible English


@dataclass(frozen=True)
class Rules:
    allowed: frozenset[str] = frozenset()  # Whisper language codes, e.g. {"zh"}
    rock: int = 0  # 0 = off, otherwise English vocabulary size
    mime: bool = False  # any speech at all is a violation
    gadsby: bool = False  # English words containing the letter "e" are violations

    @property
    def english_games(self) -> bool:
        return self.rock > 0 or self.gadsby

    @property
    def active(self) -> bool:
        return bool(self.allowed) or self.english_games or self.mime


@dataclass
class Verdict:
    violation: bool
    severity: float  # 0..1, how sure / how bad
    rule: str | None  # "language" | "rock" | "gadsby" | "mime"
    language: str | None  # the language heard
    p_allowed: float
    transcript: str | None = None
    offending: list[str] = field(default_factory=list)


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def expand(langs: frozenset[str]) -> set[str]:
    out: set[str] = set()
    for lang in langs:
        out |= FAMILIES.get(lang, {lang})
    return out


def english_words(text: str) -> list[str]:
    return [w for w in wordfreq.tokenize(text, "en") if any(c.isalpha() for c in w)]


def real_word_ratio(words: list[str]) -> float:
    if not words:
        return 0.0
    return sum(wordfreq.zipf_frequency(w, "en") >= 2.5 for w in words) / len(words)


@lru_cache(maxsize=8)
def vocabulary(n: int) -> frozenset[str]:
    return frozenset(wordfreq.top_n_list("en", n)) | CAVEMAN_WORDS


def judge(rules: Rules, seconds: float, probs: dict[str, float], decode: Decoder,
          th: Thresholds = Thresholds()) -> Verdict:
    top = max(probs, key=probs.get) if probs else None
    if rules.mime:
        return Verdict(True, clamp(seconds / 3.0), "mime", top, 0.0)
    ok = expand(rules.allowed) | ({"en"} if rules.english_games else set())
    if not ok:
        return Verdict(False, 0.0, None, top, 1.0)
    p_ok = sum(probs.get(lang, 0.0) for lang in ok)

    if p_ok < th.tau:
        others = {lang: p for lang, p in probs.items() if lang not in ok}
        heard = max(others, key=others.get)
        if heard == "en":
            text, lp = decode("en")
            if lp >= th.min_lp and real_word_ratio(english_words(text)) >= th.min_words:
                severity = clamp((lp - th.min_lp) / th.lp_span) * (1 - p_ok / th.tau)
                return Verdict(True, severity, "language", "en", p_ok, text)
            # mangled audio that isn't intelligible English: likely a learner trying, so let it pass
            return Verdict(False, 0.0, None, "en", p_ok, text)
        if p_ok < th.tau_other and others[heard] >= th.min_top_other:
            return Verdict(True, others[heard], "language", heard, p_ok)
        return Verdict(False, 0.0, None, heard, p_ok)

    if rules.english_games and top == "en":
        text, lp = decode("en")
        if lp < th.vocab_min_lp:
            return Verdict(False, 0.0, None, "en", p_ok, text)
        words = english_words(text)
        if rules.rock:
            vocab = vocabulary(rules.rock)
            # Whisper spells grunts unpredictably ("og", "uh", "hm"): two letters or fewer never count
            bad = [w for w in words if w not in vocab and not w.isdigit() and len(w) > 2]
            if bad:
                return Verdict(True, clamp(len(bad) / 4), "rock", "en", p_ok, text, bad)
        if rules.gadsby:
            bad = [w for w in words if "e" in w]
            if bad:
                return Verdict(True, clamp(len(bad) / 4), "gadsby", "en", p_ok, text, bad)
    return Verdict(False, 0.0, None, top, p_ok)
