"""Unified flow tables for the pilots: one row per flow with the columns
ts, day, src, dst, dst_port, bytes_out, bytes_in, failed, label (0/1), technique, tactic.
Labels are carried for evaluation only.
"""
import csv
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

DEDALE_DAY = re.compile(r"D\d+_(\d{4}-\d{2}-\d{2})_output_.+_Zeek/conn_labeled\.csv$")


def _num(s):
    return pd.to_numeric(s.replace({"-": "0", "": "0"}), errors="coerce").fillna(0.0)


def dedale_days(zpath):
    """Yield (day, flows) for DEDALE zeek_<zone>.zip, day by day."""
    cols = ["ts", "ip_src", "ip_dst", "port_dst", "conn_state", "orig_bytes", "resp_bytes", "label", "tactic", "technique"]
    with zipfile.ZipFile(zpath) as z:
        names = sorted((DEDALE_DAY.search(n).group(1), n) for n in z.namelist() if n.endswith("conn_labeled.csv"))
        for day, name in names:
            with z.open(name) as fh:
                d = pd.read_csv(fh, sep=";", usecols=cols, dtype=str, keep_default_na=False)
            yield day, pd.DataFrame({
                "ts": pd.to_numeric(d["ts"]), "src": d["ip_src"], "dst": d["ip_dst"], "dst_port": d["port_dst"],
                "bytes_out": _num(d["orig_bytes"]), "bytes_in": _num(d["resp_bytes"]),
                "failed": d["conn_state"].isin(["S0", "REJ"]), "label": (d["label"] == "1").astype(int),
                "technique": d["technique"], "tactic": d["tactic"]})


# Unraveled NFStream CSV: leading fields by position, labels = last 4 fields (some rows have unquoted commas).
U_LEAD = {"src_ip": 2, "dst_ip": 6, "dst_port": 9, "bidirectional_first_seen_ms": 14,
          "src2dst_bytes": 23, "dst2src_packets": 27, "dst2src_bytes": 28}


def _read_unraveled(path):
    rows = []
    with open(path, newline="") as fh:
        r = csv.reader(fh)
        header = next(r)
        assert [header[i] for i in U_LEAD.values()] == list(U_LEAD), path
        for row in r:
            rows.append([row[i] for i in U_LEAD.values()] + row[-4:])
    return pd.DataFrame(rows, columns=list(U_LEAD) + ["Activity", "Stage", "DefenderResponse", "Signature"])


def unraveled_days(root, capture, subnet):
    """Yield (day, flows) for one Unraveled subnet capture (e.g. 'net1013x', '10.1.3.'), keeping flows with an
    endpoint in that subnet. Day = UTC day of the flow's first packet."""
    parts = [_read_unraveled(f) for f in sorted(Path(root).rglob(f"{capture}_Flow_labeled.csv"))]
    d = pd.concat(parts, ignore_index=True)
    d = d[d["src_ip"].str.startswith(subnet) | d["dst_ip"].str.startswith(subnet)]
    ts = pd.to_numeric(d["bidirectional_first_seen_ms"]) / 1000.0
    f = pd.DataFrame({
        "ts": ts, "src": d["src_ip"], "dst": d["dst_ip"], "dst_port": d["dst_port"],
        "bytes_out": pd.to_numeric(d["src2dst_bytes"]), "bytes_in": pd.to_numeric(d["dst2src_bytes"]),
        "failed": pd.to_numeric(d["dst2src_packets"]) == 0, "label": (d["Stage"] != "Benign").astype(int),
        "technique": d["Activity"].where(d["Stage"] != "Benign", ""), "tactic": d["Stage"].where(d["Stage"] != "Benign", "")})
    f["day"] = pd.to_datetime(f["ts"], unit="s").dt.strftime("%Y-%m-%d")
    for day, g in f.groupby("day", sort=True):
        yield day, g.drop(columns="day").reset_index(drop=True)
