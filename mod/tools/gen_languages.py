"""Generate mod/common/src/main/resources/langenforcer/languages.json: every Whisper language and the names
an anvil-renamed banner can use to select it.

  uvx --with langcodes --with language_data --with faster-whisper==1.2.1 python mod/tools/gen_languages.py
"""
import json
import pathlib

import langcodes
from faster_whisper.tokenizer import _LANGUAGE_CODES

# Hand-picked extras: country names and the words learners actually type
ALIASES = {
    "zh": ["中文", "中国", "中國", "汉语", "漢語", "普通话", "普通話", "华语", "華語", "國語", "国语",
           "Chinese", "Mandarin", "China", "Zhongwen", "Putonghua", "Hanyu"],
    "yue": ["粵語", "粤语", "廣東話", "广东话", "Cantonese", "Hong Kong"],
    "ja": ["日本語", "日本", "にほんご", "Japanese", "Japan", "Nihongo"],
    "ko": ["한국어", "한국", "조선어", "Korean", "Korea", "Hangugeo"],
    "es": ["Español", "España", "Castellano", "Spanish", "Spain", "Mexico", "México"],
    "fr": ["Français", "France", "French"],
    "de": ["Deutsch", "Deutschland", "German", "Germany"],
    "it": ["Italiano", "Italia", "Italian", "Italy"],
    "pt": ["Português", "Portugal", "Brasil", "Brazil", "Portuguese"],
    "ru": ["Русский", "Россия", "Russian", "Russia"],
    "nl": ["Nederlands", "Nederland", "Dutch", "Netherlands", "Holland"],
    "pl": ["Polski", "Polska", "Polish", "Poland"],
    "uk": ["Українська", "Україна", "Ukrainian", "Ukraine"],
    "id": ["Bahasa Indonesia", "Indonesia", "Indonesian"],
    "vi": ["Tiếng Việt", "Việt Nam", "Vietnamese", "Vietnam"],
    "th": ["ภาษาไทย", "ไทย", "Thai", "Thailand"],
    "ar": ["العربية", "Arabic"],
    "hi": ["हिन्दी", "Hindi", "India"],
    "sv": ["Svenska", "Sverige", "Swedish", "Sweden"],
    "mi": ["Te Reo Māori", "Te Reo", "Māori", "Maori", "Aotearoa"],
    "en": ["English", "England"],
}


def main() -> None:
    out = []
    for code in _LANGUAGE_CODES:
        lang = langcodes.Language.get(code)
        english = lang.display_name("en")
        native = lang.autonym()
        names = [english, native] + ALIASES.get(code, [])
        seen, uniq = set(), []
        for n in names:
            if n and n.casefold() not in seen and not n.startswith("Unknown"):
                seen.add(n.casefold())
                uniq.append(n)
        out.append({"code": code, "name": english, "native": native, "names": uniq})
    path = pathlib.Path(__file__).resolve().parents[1] / "common/src/main/resources/langenforcer/languages.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(out)} languages -> {path}")


if __name__ == "__main__":
    main()
