from langenforcer_sidecar.rules import Rules, judge, vocabulary

ZH = Rules(frozenset({"zh"}))


def decoder(text: str, lp: float):
    calls = []

    def decode(lang):
        calls.append(lang)
        return text, lp

    decode.calls = calls
    return decode


def test_mandarin_passes_without_decoding():
    d = decoder("", 0.0)
    v = judge(ZH, 2.0, {"zh": 0.9, "en": 0.05}, d)
    assert not v.violation
    assert d.calls == []  # language-ID alone settles it: no transcript cost


def test_confident_english_is_a_violation_scaled_by_confidence():
    strong = judge(ZH, 2.0, {"en": 0.99, "zh": 0.0}, decoder("I need more iron", -0.05))
    weak = judge(ZH, 2.0, {"en": 0.95, "zh": 0.04}, decoder("I need more iron", -0.3))
    assert strong.violation and weak.violation
    assert strong.rule == "language" and strong.language == "en"
    assert strong.severity > weak.severity > 0


def test_mangled_learner_mandarin_gets_benefit_of_doubt():
    # language-ID says English, but the English transcript is low-confidence nonsense
    v = judge(ZH, 2.0, {"en": 0.9, "zh": 0.05}, decoder("Gun wallet", -0.83))
    assert not v.violation


def test_english_needs_real_words():
    v = judge(ZH, 2.0, {"en": 0.95, "zh": 0.0}, decoder("Shaoxingyoukuli Pa", -0.2))
    assert not v.violation


def test_cantonese_counts_as_chinese():
    v = judge(ZH, 2.0, {"yue": 0.6, "zh": 0.05, "en": 0.3}, decoder("", 0.0))
    assert not v.violation


def test_clear_other_language_is_a_violation():
    v = judge(ZH, 3.0, {"ja": 0.97, "zh": 0.01}, decoder("", 0.0))
    assert v.violation and v.language == "ja"


def test_rock_allows_simple_english_and_punishes_big_words():
    rock = Rules(rock=500)
    caveman = judge(rock, 2.0, {"en": 0.98}, decoder("Me want food, rock good, og.", -0.2))
    fancy = judge(rock, 2.0, {"en": 0.98}, decoder("I need diamonds for my enchantment table", -0.2))
    assert not caveman.violation
    assert fancy.violation and fancy.rule == "rock"
    assert "diamonds" in fancy.offending and "enchantment" in fancy.offending


def test_rock_plus_flag_allows_mandarin_and_basic_english():
    both = Rules(frozenset({"zh"}), rock=500)
    assert not judge(both, 2.0, {"zh": 0.95, "en": 0.03}, decoder("", 0.0)).violation
    assert not judge(both, 2.0, {"en": 0.97, "zh": 0.01}, decoder("You go there", -0.1)).violation
    assert judge(both, 2.0, {"en": 0.97, "zh": 0.01}, decoder("Fortunately the villagers restocked", -0.1)).violation


def test_gadsby_punishes_the_letter_e():
    g = Rules(gadsby=True)
    assert not judge(g, 2.0, {"en": 0.98}, decoder("Hold that block, it is ours", -0.1)).violation
    v = judge(g, 2.0, {"en": 0.98}, decoder("Get the sword", -0.1))
    assert v.violation and v.rule == "gadsby" and v.offending == ["get", "the"]


def test_mime_punishes_any_speech():
    v = judge(Rules(mime=True), 1.5, {"en": 0.98}, decoder("", 0.0))
    assert v.violation and v.rule == "mime" and 0 < v.severity <= 1


def test_no_rules_no_verdict():
    assert not judge(Rules(), 2.0, {"en": 1.0}, decoder("anything", 0.0)).violation


def test_vocabulary_has_caveman_words():
    vocab = vocabulary(500)
    assert {"the", "want", "rock", "ooga", "booga"} <= vocab
    assert "diamond" not in vocab
