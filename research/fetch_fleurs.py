"""Stream the first N clips of a FLEURS split without downloading the whole tarball."""
import csv, io, sys, tarfile, urllib.request, pathlib

BASE = "https://huggingface.co/datasets/google/fleurs/resolve/main/data"

def fetch(lang: str, split: str, n: int, out: pathlib.Path):
    dest = out / lang
    dest.mkdir(parents=True, exist_ok=True)
    tsv = urllib.request.urlopen(f"{BASE}/{lang}/{split}.tsv").read().decode()
    meta = {row[1]: row for row in csv.reader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE)}
    seen, rows = set(), []
    with urllib.request.urlopen(f"{BASE}/{lang}/audio/{split}.tar.gz") as resp:
        with tarfile.open(fileobj=resp, mode="r|gz") as tar:
            for m in tar:
                if not m.isfile() or not m.name.endswith(".wav"):
                    continue
                name = pathlib.Path(m.name).name
                row = meta.get(name)
                # FLEURS repeats each sentence with several speakers; keep one per sentence id
                if row is None or row[0] in seen:
                    continue
                seen.add(row[0])
                (dest / name).write_bytes(tar.extractfile(m).read())
                rows.append({"file": name, "text": row[2]})
                if len(rows) >= n:
                    break
    with open(dest / "meta.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "text"]); w.writeheader(); w.writerows(rows)
    print(lang, len(rows), flush=True)

if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1])
    for spec in sys.argv[2:]:
        lang, n = spec.split(":")
        fetch(lang, "dev", int(n), out)
