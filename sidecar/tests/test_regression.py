"""End-to-end check against the research test sets (Opus round-tripped clips, see research/prep.py).

Slow and needs the data, so it only runs when LE_REGRESSION_DATA points at research's prepped dir:
  LE_REGRESSION_DATA=/path/to/prepped uv run pytest tests/test_regression.py -s
"""
import csv
import os
import pathlib

import numpy as np
import pytest

from langenforcer_sidecar.engine import Engine
from langenforcer_sidecar.rules import Rules, judge

DATA = os.environ.get("LE_REGRESSION_DATA")
pytestmark = pytest.mark.skipif(not DATA, reason="set LE_REGRESSION_DATA to research's prepped dir")

# set -> (expected flag rate %, tolerance) from research/report (Whisper small, two-stage, whole utterances)
EXPECT = {
    "cmn_hans_cn": (0.0, 3), "fleurs_zh_flat": (0.0, 3), "phr_zh_native": (0.0, 3),
    "phr_zh_learner": (5.0, 6), "phr_zh_pinyin": (5.8, 6),
    "en_us": (99.3, 4), "phr_en": (95.8, 5), "ja_jp": (100.0, 4),
}


@pytest.fixture(scope="module")
def engine():
    return Engine(os.environ.get("LE_MODEL", "small"))


@pytest.mark.parametrize("name", list(EXPECT))
def test_flag_rate_matches_research(engine, name):
    root = pathlib.Path(DATA)
    audio = np.load(root / f"{name}.npz")
    rows = list(csv.DictReader(open(root / f"{name}.csv")))[:60]
    flagged = 0
    for r in rows:
        a = engine.analyze(audio[r["file"]].astype(np.float32))
        flagged += judge(Rules(frozenset({"zh"})), a.seconds, a.probs, a.decode).violation
    rate = 100 * flagged / len(rows)
    want, tol = EXPECT[name]
    print(f"{name}: {rate:.1f}% flagged (research {want}%)")
    assert abs(rate - want) <= tol
