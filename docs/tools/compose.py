"""Crop and label in-game screenshots (1600x900, GUI scale 3) into the README images.

  compose.py <screenshots dir> <docs/img dir>
"""
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc"
BG = (22, 27, 34)
FG = (230, 237, 243)
MUTED = (145, 152, 161)
LOOM = (537, 201, 1065, 456)  # loom slots, pattern list and preview; inventory cropped off


def label_strip(panels, labels, scale=1.0, gap=16, pad=16, font_size=22):
    font = ImageFont.truetype(FONT, font_size)
    panels = [p.resize((round(p.width * scale), round(p.height * scale)), Image.NEAREST) for p in panels]
    w = sum(p.width for p in panels) + gap * (len(panels) - 1) + pad * 2
    h = max(p.height for p in panels) + pad * 2 + font_size + 18
    out = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(out)
    x = pad
    for p, text in zip(panels, labels):
        out.paste(p, (x, pad))
        tw = d.textlength(text, font=font)
        d.text((x + (p.width - tw) / 2, pad + p.height + 10), text, font=font, fill=FG)
        x += p.width + gap
    return out


def main(shots: pathlib.Path, out: pathlib.Path):
    out.mkdir(parents=True, exist_ok=True)
    open_ = lambda n: Image.open(shots / f"{n}.png").convert("RGB")

    open_("hero").crop((0, 0, 1600, 820)).resize((1280, 656), Image.LANCZOS).save(out / "hero.png", optimize=True)

    steps = [open_(f"loom_step{i}").crop(LOOM) for i in (1, 2, 3)]
    label_strip(steps, ["① yellow dye → Chief Dexter Canton", "② red dye → Chief Indented",
                        "③ red dye → Bordure = 中国"], scale=0.75, font_size=19).save(out / "crafting-loom.png", optimize=True)

    anvil = open_("anvil2").crop((537, 201, 1185, 470))
    tooltip = open_("inv_tooltip").crop((535, 590, 1075, 775))
    label_strip([anvil, tooltip], ["…or rename any banner in an anvil", "the finished flag's patterns"],
                scale=0.8, font_size=19).save(out / "crafting-anvil.png", optimize=True)

    deaths = [open_(n).crop((330, 160, 1270, 600)) for n in ("death_zh", "death_rock")]
    label_strip(deaths, ["China flag + English", "a cobblestone named “Rock” + big words"],
                scale=0.62, font_size=19).save(out / "deaths.png", optimize=True)

    for f in sorted(out.glob("*.png")):
        print(f.name, Image.open(f).size, f.stat().st_size // 1024, "KiB")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
