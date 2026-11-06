"""Download Unraveled (DAPT2021) labelled network flows from the public S3 bucket.

Usage: python download_unraveled.py [PREFIX]   (default prefix: processed/network-flows/)
Writes to dep/data_raw/unraveled/<key> and dep/audit/unraveled/MANIFEST.json.
The S3 ETag equals the MD5 for single-part uploads (ETag without '-'); it is checked when that holds.
"""
import hashlib
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BUCKET = "https://dapt2021.s3.amazonaws.com/"
HERE = Path(__file__).resolve().parent
OUT = HERE.parent.parent / "data_raw" / "unraveled"


def list_keys(prefix):
    keys, token = [], None
    while True:
        q = {"list-type": "2", "prefix": prefix}
        if token:
            q["continuation-token"] = token
        xml = urllib.request.urlopen(BUCKET + "?" + urllib.parse.urlencode(q), timeout=60).read().decode()
        for block in re.findall(r"<Contents>(.*?)</Contents>", xml, re.S):
            key = re.search(r"<Key>(.*?)</Key>", block).group(1)
            size = int(re.search(r"<Size>(\d+)</Size>", block).group(1))
            etag = re.search(r"<ETag>(.*?)</ETag>", block).group(1).replace("&quot;", "").strip('"')
            if size:
                keys.append((key, size, etag))
        m = re.search(r"<NextContinuationToken>(.*?)</NextContinuationToken>", xml)
        if not m:
            return keys
        token = m.group(1)


def main(prefix="processed/network-flows/"):
    mpath = HERE / "MANIFEST.json"
    manifest = json.loads(mpath.read_text()) if mpath.exists() else {}
    for key, size, etag in list_keys(prefix):
        dest = OUT / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(4):
            if dest.exists() and dest.stat().st_size == size:
                break
            tmp = dest.with_suffix(dest.suffix + ".part")
            with urllib.request.urlopen(BUCKET + urllib.parse.quote(key), timeout=600) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            if tmp.stat().st_size == size:
                tmp.rename(dest)
        else:
            sys.exit(f"incomplete download after 4 attempts: {key}")
        md5, sha = hashlib.md5(), hashlib.sha256()
        with open(dest, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                md5.update(chunk)
                sha.update(chunk)
        single = "-" not in etag
        manifest[key] = {"bytes": size, "etag": etag, "md5": md5.hexdigest(), "sha256": sha.hexdigest(),
                         "md5_ok": (md5.hexdigest() == etag) if single else None}
        if single and md5.hexdigest() != etag:
            mpath.write_text(json.dumps(manifest, indent=1, sort_keys=True))
            sys.exit(f"MD5 mismatch: {key}")
    mpath.write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print(len(manifest), "files;", sum(1 for v in manifest.values() if v["md5_ok"]), "MD5 OK;",
          sum(1 for v in manifest.values() if v["md5_ok"] is None), "multipart (SHA-256 only)")


if __name__ == "__main__":
    main(*sys.argv[1:])
