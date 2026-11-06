"""Index a Drive folder of copied OpTC conn logs (copies lose their date folder): read the '#open' header line
from the first 64 KB of each conn copy and write day, file, file id.

Usage: python index_copies.py FOLDER_ID OUT_CSV
"""
import csv
import sys
import urllib.request
import zlib

from drive_list import ls


def opened(fid):
    req = urllib.request.Request(f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t",
                                 headers={"Range": "bytes=0-65535"})
    raw = urllib.request.urlopen(req, timeout=120).read()
    text = zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(raw).decode("utf-8", "replace")
    line = next(l for l in text.splitlines() if l.startswith("#open"))
    return line.split("\t")[1]  # e.g. 2019-09-25-10-00-00


def main(folder, out):
    rows = []
    for kind, name, fid in ls(folder):
        base = name.split()[-1]
        if not base.startswith("conn."):
            continue
        o = opened(fid)
        rows.append({"day": o[:10], "file": base, "hour": int(o[11:13]), "file_id": fid})
        print(rows[-1], flush=True)
    rows.sort(key=lambda r: (r["day"], r["hour"]))
    with open(out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["day", "file", "hour", "file_id"])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main(*sys.argv[1:])
