"""Aggregate LID + verdict results into report.json for the concept report."""
import csv, json, pathlib, sys
from collections import defaultdict

SETS = {
    "cmn_hans_cn": "Native Mandarin (FLEURS)",
    "phr_zh_native": "Native Mandarin, game phrases (TTS)",
    "fleurs_zh_flat": "Mandarin, tones removed",
    "phr_zh_learner": "Learner Mandarin, anglophone accent",
    "phr_zh_pinyin": "Raw pinyin read by English voices",
    "en_us": "English (FLEURS)",
    "phr_en": "English, game phrases (TTS)",
    "l2_zh_scripted": "Chinese-accented English, read",
    "l2_zh_spont": "Chinese-accented English, chat",
    "yue_hant_hk": "Cantonese", "ja_jp": "Japanese", "ko_kr": "Korean",
    "vi_vn": "Vietnamese", "es_419": "Spanish", "de_de": "German",
}
TARGET_OK = {"cmn_hans_cn", "phr_zh_native", "fleurs_zh_flat", "phr_zh_learner", "phr_zh_pinyin"}
DURS = ["0.5", "1.0", "1.5", "2.0", "3.0", "5.0", "full"]


def load(path):
    return list(csv.DictReader(open(path))) if path.exists() else []


def lid_flag(r, tau):
    return float(r["p_zh"]) < tau


def verdict_flag(lid_row, v, rule):
    """Two-stage rule: LID suspects non-Mandarin AND the English decode is intelligible English."""
    if not lid_flag(lid_row, rule["tau"]):
        return False
    if v is None:
        return True
    if lid_row["top"] != "en":
        # non-English foreign language: no English-intelligibility test applies, trust LID
        return float(lid_row["p_zh"]) < rule["tau_other"] and float(lid_row["top_p"]) >= rule["min_top_other"]
    return float(v["en_words"]) >= rule["min_words"] and float(v["en_lp"]) >= rule["min_lp"]


def main(results: pathlib.Path, out: pathlib.Path):
    report = {"sets": SETS, "target_ok": sorted(TARGET_OK), "durs": DURS, "lid": {}, "verdict": {}, "examples": []}
    models = [p.stem for p in sorted(results.glob("*.csv")) if not p.stem.startswith("verdict-") and p.stem != "latency"]
    for m in models:
        rows = load(results / f"{m}.csv")
        by = defaultdict(list)
        for r in rows:
            by[(r["set"], r["dur"])].append(r)
        report["lid"][m] = {
            s: {d: (round(100 * sum(lid_flag(r, 0.1) for r in by[(s, d)]) / len(by[(s, d)]), 1), len(by[(s, d)]))
                for d in DURS if by[(s, d)]}
            for s in SETS
        }
    rule = json.loads(pathlib.Path(__file__).with_name("rule.json").read_text())
    report["rule"] = rule
    for vpath in sorted(results.glob("verdict-*.csv")):
        m = vpath.stem.removeprefix("verdict-")
        lid_rows = {(r["set"], r["file"], r["dur"]): r for r in load(results / f"{m}.csv")}
        # A window longer than the clip is the whole clip, which LID scored as "full"
        lid = lambda k: lid_rows.get(k) or lid_rows[(k[0], k[1], "full")]
        vrows = load(vpath)
        out_m = defaultdict(dict)
        for s in SETS:
            for d in DURS:
                sub = [v for v in vrows if v["set"] == s and v["dur"] == d]
                if not sub:
                    continue
                lid_only = sum(lid_flag(lid((s, v["file"], d)), 0.1) for v in sub)
                two = sum(verdict_flag(lid((s, v["file"], d)), v, rule) for v in sub)
                out_m[s][d] = {"n": len(sub), "lid_only": round(100 * lid_only / len(sub), 1),
                               "two_stage": round(100 * two / len(sub), 1)}
        report["verdict"][m] = out_m
        # streaming: English catch time & cumulative Mandarin false-cut over 2s/3s/full checkpoints
        stream = {}
        for s in ("cmn_hans_cn", "fleurs_zh_flat", "en_us"):
            files = sorted({v["file"] for v in vrows if v["set"] == s})
            first_cut = []
            for f in files:
                t = None
                for d in ("2.0", "3.0", "full"):
                    v = next((v for v in vrows if v["set"] == s and v["file"] == f and v["dur"] == d), None)
                    if v and verdict_flag(lid((s, f, d)), v, rule):
                        t = float(v["secs"]); break
                first_cut.append(t)
            stream[s] = {"n": len(files), "cut_pct": round(100 * sum(t is not None for t in first_cut) / len(files), 1),
                         "cut_by_2s": round(100 * sum(t is not None and t <= 2.0 for t in first_cut) / len(files), 1),
                         "cut_by_3s": round(100 * sum(t is not None and t <= 3.0 for t in first_cut) / len(files), 1)}
        report.setdefault("stream", {})[m] = stream
        if m == "whisper-small" or not report["examples"]:
            ex = []
            for s in ("phr_en", "phr_zh_learner", "phr_zh_native", "phr_zh_pinyin"):
                for v in [v for v in vrows if v["set"] == s][:6:2]:
                    l = lid((s, v["file"], v["dur"]))
                    ex.append({"set": s, "p_zh": float(l["p_zh"]), "top": l["top"], "en_text": v["en_text"],
                               "zh_text": v["zh_text"], "en_words": float(v["en_words"]), "en_lp": float(v["en_lp"]),
                               "flag": verdict_flag(l, v, rule)})
            report["examples"] = ex
    bench = results / "latency.csv"
    report["latency"] = load(bench)
    json.dump(report, open(out, "w"), ensure_ascii=False, indent=1)
    print(json.dumps({m: {s: report["verdict"][m][s].get("full") for s in ("cmn_hans_cn", "phr_zh_learner", "phr_zh_pinyin", "phr_en", "en_us")} for m in report["verdict"]}, indent=1))
    print(json.dumps(report.get("stream", {}), indent=1))


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
