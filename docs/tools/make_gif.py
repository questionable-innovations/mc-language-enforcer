"""Turn a raw game recording into a captioned README GIF.

  make_gif.py <in.mp4> <out.gif> <captions.json>
captions.json: [[start_s, end_s, "text", "ok"|"bad"|null], ...]
Frames where the window grab came back partly black are replaced by the previous good frame.
"""
import json
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc"
SRC_W, SRC_H, FPS = 1600, 900, 12
CROP = (200, 150, 1400, 900)  # keeps the village and makes the HUD hearts readable
OUT_W = 840


def frames(path):
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={FPS}", "-f", "rawvideo",
                             "-pix_fmt", "rgb24", "pipe:1"], stdout=subprocess.PIPE)
    size = SRC_W * SRC_H * 3
    while chunk := proc.stdout.read(size):
        if len(chunk) == size:
            yield np.frombuffer(chunk, np.uint8).reshape(SRC_H, SRC_W, 3)


def broken(f):
    # a grab glitch blanks whole rows; the sky is never pure black
    return (f[: SRC_H // 2].max(axis=(1, 2)) < 8).mean() > 0.2


def main(src, dst, captions_path):
    captions = json.load(open(captions_path))
    font = ImageFont.truetype(FONT, 26)
    out, last = [], None
    for i, f in enumerate(frames(src)):
        if broken(f) and last is not None:
            f = last
        last = f
        t = i / FPS
        im = Image.fromarray(f).crop(CROP)
        im = im.resize((OUT_W, round(OUT_W * im.height / im.width / 2) * 2), Image.LANCZOS)
        cap = next((c for c in captions if c[0] <= t < c[1]), None)
        if cap:
            d = ImageDraw.Draw(im, "RGBA")
            colour = {"ok": (120, 220, 120), "bad": (255, 110, 100)}.get(cap[3], (255, 255, 255))
            w = d.textlength(cap[2], font=font)
            x = (im.width - w) / 2
            d.rounded_rectangle((x - 16, 14, x + w + 16, 58), radius=10, fill=(0, 0, 0, 170))
            d.text((x, 18), cap[2], font=font, fill=colour)
        out.append(im)
    tmp = dst + ".frames.mp4"
    writer = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                               f"{out[0].width}x{out[0].height}", "-r", str(FPS), "-i", "pipe:0", "-c:v", "libx264",
                               "-crf", "12", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for im in out:
        writer.stdin.write(im.tobytes())
    writer.stdin.close()
    writer.wait()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-vf",
                    "split[a][b];[a]palettegen=max_colors=192:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4",
                    "-loop", "0", dst], check=True)
    subprocess.run(["rm", "-f", tmp])
    print(dst, len(out), "frames")


if __name__ == "__main__":
    main(*sys.argv[1:4])
