"""Render vanilla banner designs from Minecraft's own textures, to pick a loom-craftable flag per language."""
import json, pathlib, sys

from PIL import Image

DYE = {  # DyeColor.getTextureDiffuseColors() in 1.20.1
    "white": 0xF9FFFE, "orange": 0xF9801D, "magenta": 0xC74EBD, "light_blue": 0x3AB3DA, "yellow": 0xFED83D,
    "lime": 0x80C71F, "pink": 0xF38BAA, "gray": 0x474F52, "light_gray": 0x9D9D97, "cyan": 0x169C9C,
    "purple": 0x8932B8, "blue": 0x3C44AA, "brown": 0x835432, "green": 0x5E7C16, "red": 0xB02E26, "black": 0x1D1D21,
}


def render(tex_dir: pathlib.Path, base: str, layers: list[tuple[str, str]], scale=8) -> Image.Image:
    out = Image.new("RGBA", (20, 40), (0, 0, 0, 0))
    for pattern, color in [("base", base)] + layers:
        mask = Image.open(tex_dir / f"{pattern}.png").convert("RGBA").crop((1, 1, 21, 41))
        rgb = DYE[color]
        tint = Image.new("RGBA", mask.size, ((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255, 255))
        # pattern textures are greyscale+alpha masks; multiply by the dye colour then alpha-blend
        px, tp = mask.load(), tint.load()
        for y in range(mask.height):
            for x in range(mask.width):
                g, _, _, a = px[x, y]
                r0, g0, b0, _ = tp[x, y]
                tp[x, y] = (r0 * g // 255, g0 * g // 255, b0 * g // 255, a)
        out = Image.alpha_composite(out, tint)
    return out.resize((20 * scale, 40 * scale), Image.NEAREST)


if __name__ == "__main__":
    tex, designs, out = pathlib.Path(sys.argv[1]), json.load(open(sys.argv[2])), pathlib.Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    for name, d in designs.items():
        render(tex, d["base"], [tuple(l) for l in d["layers"]]).save(out / f"{name}.png")
        print(name)
