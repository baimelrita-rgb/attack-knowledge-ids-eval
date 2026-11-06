"""Download DEDALE files from Recherche Data Gouv, verify MD5 against file_list.csv, record SHA-256.

Usage: python download_dedale.py FILENAME [FILENAME ...]
Writes data to dep/data_raw/dedale/ and appends to dep/data_raw/dedale/MANIFEST.json.
"""
import csv
import datetime as dt
import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / "data_raw" / "dedale"
API = "https://entrepot.recherche.data.gouv.fr/api/access/datafile/{}"


def load_list():
    with open(HERE / "file_list.csv", newline="") as f:
        return {r["filename"]: r for r in csv.DictReader(f)}


def hashes(path):
    md5, sha = hashlib.md5(), hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            md5.update(chunk)
            sha.update(chunk)
    return md5.hexdigest(), sha.hexdigest()


def main(names):
    files = load_list()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for name in names:
        row = files[name]
        dest = OUT / name
        expected = row["md5_or_checksum"].split(":", 1)[1]
        if not (dest.exists() and dest.stat().st_size == int(row["bytes"])):
            tmp = dest.with_suffix(dest.suffix + ".part")
            with urllib.request.urlopen(API.format(row["file_id"]), timeout=600) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            tmp.rename(dest)
        md5, sha = hashes(dest)
        ok = md5 == expected
        manifest[name] = {"file_id": row["file_id"], "bytes": dest.stat().st_size, "md5": md5,
                          "md5_expected": expected, "md5_ok": ok, "sha256": sha,
                          "downloaded_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        print(name, "MD5 OK" if ok else "MD5 MISMATCH", sha, flush=True)
        if not ok:
            sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
