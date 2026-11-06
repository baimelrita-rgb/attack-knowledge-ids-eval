"""OpTC host-hour features from the hourly Zeek conn logs on Google Drive, streamed hour by hour.

Same feature code as development (features.day_features, features_p3.extra_day). Each hourly file is
processed once its hour is complete; novelty/rarity state is frozen at the start of each UTC day and updated
at its end, as in development (history = earlier days). Flows logged more than one hour after they started
are counted and dropped.

Labels (evaluation only): label = 1 for flows between an internal host and a documented attacker IP
(red-team report: 132.197.158.98, 202.6.172.98, 53.192.68.50).

Usage: python optc_features.py OUT_PREFIX DAY [DAY ...]
"""
import gzip
import io
import json
import pickle
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from features import day_features  # noqa: E402
from features_p3 import EXTRA, extra_day  # noqa: E402
from drive_list import ls  # noqa: E402

BRO_ROOT = "1T1kXs0G9cTxi7p2Jqi60ApWNOfvVqFkp"
INTERNAL = tuple(f"142.20.{i}." for i in range(56, 64))
C2 = {"132.197.158.98", "202.6.172.98", "53.192.68.50"}
COLS = [0, 2, 4, 5, 9, 10, 11]
NAMES = ["ts", "src", "dst", "dst_port", "orig_bytes", "resp_bytes", "conn_state"]


class DeferredSet(set):
    """Membership = state at the start of the day; updates are applied by commit() at the end of the day."""
    def __init__(self, *args):
        super().__init__(*args)
        self.pending = []

    def update(self, *its):
        for it in its:
            self.pending.extend(it)

    def commit(self):
        super().update(self.pending)
        self.pending = []


class DeferredPop(dict):
    def __init__(self):
        super().__init__()
        self.pending = {}

    def setdefault(self, k, default=None):
        return self.pending.setdefault(k, set())

    def commit(self):
        for k, v in self.pending.items():
            dict.setdefault(self, k, set()).update(v)
        self.pending = {}


def download(fid, tries=6, quota_waits=48):
    """Retry on network errors and on non-gzip answers (Drive sometimes returns an HTML page).
    On Drive's per-file 'Quota exceeded' page, wait 30 min and retry (up to quota_waits times)."""
    i = waits = 0
    while True:
        raw = b""
        try:
            url = f"https://drive.usercontent.google.com/download?id={fid}&export=download&confirm=t"
            raw = urllib.request.urlopen(url, timeout=600).read()
            if raw[:2] == b"\x1f\x8b":
                return raw
        except Exception:
            if i == tries - 1:
                raise
        if b"Quota exceeded" in raw[:4000]:
            waits += 1
            if waits > quota_waits:
                raise RuntimeError(f"Drive quota still exceeded for {fid}")
            print(json.dumps({"quota_exceeded": fid, "wait_number": waits, "utc": time.strftime("%H:%M:%S", time.gmtime())}), flush=True)
            time.sleep(1800)
            continue
        i += 1
        if i >= tries:
            raise RuntimeError(f"no gzip content for {fid} after {tries} attempts")
        time.sleep(min(2 ** (i + 1), 120))


def parse(raw):
    d = pd.read_csv(io.BytesIO(gzip.decompress(raw)), sep="\t", comment="#", header=None, usecols=COLS,
                    names=None, dtype=str, keep_default_na=False, on_bad_lines="skip")
    d.columns = NAMES
    num = lambda s: pd.to_numeric(s.replace({"-": "0", "": "0"}), errors="coerce").fillna(0.0)  # noqa: E731
    src_int, dst_int = d["src"].str.startswith(INTERNAL), d["dst"].str.startswith(INTERNAL)
    lab = (src_int & d["dst"].isin(C2)) | (dst_int & d["src"].isin(C2))
    return pd.DataFrame({
        "ts": pd.to_numeric(d["ts"], errors="coerce"), "src": d["src"], "dst": d["dst"], "dst_port": d["dst_port"],
        "bytes_out": num(d["orig_bytes"]), "bytes_in": num(d["resp_bytes"]),
        "failed": d["conn_state"].isin(["S0", "REJ"]), "label": lab.astype(int),
        "technique": np.where(lab, "C2", ""), "tactic": np.where(lab, "C2", "")}).dropna(subset=["ts"])


def main(prefix, *days):
    import os
    index = os.environ.get("OPTC_INDEX")  # CSV day,file,hour,file_id of copies (index_copies.py); else the original folders
    if index:
        idx = pd.read_csv(index).drop_duplicates(["day", "hour"])
        day_files = {d: sorted(zip(g["file"], g["file_id"])) for d, g in idx.groupby("day")}
    else:
        day_ids = {name: fid for _, name, fid in ls(BRO_ROOT)}
        day_files = None
    seen_ext, seen_admin = DeferredSet(), DeferredSet()
    state = {"pop": DeferredPop(), "events": {}}
    parts, eparts, log = [], [], []
    buf = pd.DataFrame()
    done_hour = -1
    done_days = []
    ck = Path(prefix + "_checkpoint.pkl")
    if ck.exists():  # resume after the last completed day
        with open(ck, "rb") as fh:
            seen_ext, seen_admin, state, parts, eparts, log, buf, done_hour, done_days = pickle.load(fh)
        print("resumed after", done_days[-1], flush=True)

    def process(flows, day):
        nonlocal done_hour
        if not len(flows):
            return
        f = day_features(flows, INTERNAL, INTERNAL, seen_ext, seen_admin)
        x, e = extra_day(flows, INTERNAL, INTERNAL, state)
        f = f.merge(x, on=["host", "hour"], how="outer")
        f["day"], e["day"] = day, day
        parts.append(f)
        eparts.append(e)

    for day in days:
        if day in done_days:
            continue
        if day_files is not None:
            if day not in day_files:
                raise RuntimeError(f"day {day} missing from the index")
            files = day_files[day]
        else:
            files = sorted((n, fid) for _, n, fid in ls(day_ids[day]) if n.startswith("conn."))
        for name, fid in files:
            h_file = int(name.split(".")[1][:2])
            flows = parse(download(fid))
            hour_of = (flows["ts"] // 3600).astype("int64")
            day0 = int(pd.Timestamp(day).timestamp() // 3600)
            cur = day0 + h_file
            buf = pd.concat([buf, flows], ignore_index=True)
            bh = (buf["ts"] // 3600).astype("int64")
            late = bh <= done_hour
            ready = (bh < cur) & ~late
            log.append({"day": day, "file": name, "flows": len(flows), "dropped_late": int(late.sum()),
                        "processed": int(ready.sum()), "attack_flows": int(flows["label"].sum())})
            for h in sorted(bh[ready].unique()):
                process(buf[bh == h], day if h >= day0 else pd.Timestamp(h * 3600, unit="s").strftime("%Y-%m-%d"))
                done_hour = h
            buf = buf[~late & ~ready]
            print(json.dumps(log[-1]), flush=True)
        # end of day: process the remaining hours of this day, then commit the day's history
        bh = (buf["ts"] // 3600).astype("int64")
        day_end = int(pd.Timestamp(day).timestamp() // 3600) + 24
        for h in sorted(bh[(bh < day_end) & (bh > done_hour)].unique()):
            process(buf[bh == h], day)
            done_hour = h
        buf = buf[bh >= day_end]
        seen_ext.commit()
        seen_admin.commit()
        state["pop"].commit()
        done_days.append(day)
        with open(ck, "wb") as fh:
            pickle.dump((seen_ext, seen_admin, state, parts, eparts, log, buf, done_hour, done_days), fh)

    from features import finish
    res = finish(parts)
    res = res[res["host"].str.startswith(INTERNAL)]
    res[EXTRA] = res[EXTRA].fillna(0)
    res.to_parquet(prefix + "_host_hour.parquet", index=False)
    pd.concat(eparts, ignore_index=True).to_parquet(prefix + "_edges.parquet", index=False)
    pd.DataFrame(log).to_csv(prefix + "_ingest_log.csv", index=False)


if __name__ == "__main__":
    main(*sys.argv[1:])
