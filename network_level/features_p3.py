"""P3 features: P2 features + rare-destination/beacon (C2), volume, and the hourly internal edge list
(any port) used by the GNN lateral-movement channel (gnn_edges.py).

Usage:
  python features_p3.py dedale ZIP OUT_PREFIX
  python features_p3.py unraveled FLOWS_DIR OUT_PREFIX [START_DAY]
Writes OUT_PREFIX_host_hour.parquet and OUT_PREFIX_edges.parquet.
"""
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

from features import UNRAVELED_SUBNETS, day_features, finish
from flows import dedale_days, unraveled_days

RARE_MAX_HOSTS = 2        # an external destination is rare if at most 2 internal hosts contacted it before
BEACON_WINDOW = 72 * 3600  # seconds of history used for regularity
BEACON_MIN_EVENTS = 4
EVENT_GAP = 60            # flows of the same pair less than 60 s apart form one event


def _events(ts):
    ts = np.sort(ts)
    keep = np.r_[True, np.diff(ts) >= EVENT_GAP]
    return ts[keep]


def _regularity(ev):
    """1 / (CV of inter-event intervals + 0.05); 0 if too few events."""
    if len(ev) < BEACON_MIN_EVENTS:
        return 0.0
    d = np.diff(ev)
    return float(1.0 / (d.std() / d.mean() + 0.05))


def extra_day(df, internal, local, state):
    df = df.copy()
    df["hour"] = (df["ts"] // 3600).astype("int64")
    src_loc = df["src"].str.startswith(local)
    src_int, dst_int = df["src"].str.startswith(internal), df["dst"].str.startswith(internal)
    pop = state["pop"]

    ext = df[src_loc & ~dst_int].copy()
    ext["pop"] = ext["dst"].map(lambda d: len(pop.get(d, ())))
    ext["rare"] = ext["pop"] <= RARE_MAX_HOSTS
    g = ext.groupby(["src", "hour"])
    f = pd.DataFrame({
        "c2_rare_flows": g["rare"].sum(),
        "c2_rare_dsts": g.apply(lambda x: x.loc[x["rare"], "dst"].nunique(), include_groups=False),
    }) if len(ext) else pd.DataFrame(columns=["c2_rare_flows", "c2_rare_dsts"])

    # beacon regularity for rare pairs active in the hour, using events of the last 72 h
    beacon = defaultdict(float)
    hist = state["events"]
    for (s, d), x in ext[ext["rare"]].groupby(["src", "dst"]):
        ev_today = _events(x["ts"].to_numpy())
        past = hist.get((s, d), np.empty(0))
        allev = np.r_[past, ev_today]
        for h in np.unique(x["hour"].to_numpy()):
            end = (h + 1) * 3600
            w = allev[(allev > end - BEACON_WINDOW) & (allev <= end)]
            beacon[(s, h)] = max(beacon[(s, h)], _regularity(w))
    if beacon:
        b = pd.Series(beacon, name="c2_beacon")
        b.index.names = ["src", "hour"]
        f = f.join(b, how="outer")

    out = df[src_loc]
    go = out.groupby(["src", "hour"])
    f = f.join(pd.DataFrame({"vol_bytes_out": go["bytes_out"].sum(), "vol_bytes_in": go["bytes_in"].sum()}), how="outer")
    fin = df[df["dst"].str.startswith(local)].groupby(["dst", "hour"]).size().rename("vol_flows_in")
    fin.index.names = ["src", "hour"]
    f = f.join(fin, how="outer")
    f.index.names = ["host", "hour"]

    edges = df[src_int & dst_int & (src_loc | df["dst"].str.startswith(local))].groupby(
        ["src", "dst", "dst_port", "hour"]).size().rename("n").reset_index()

    # state update (after the day: today's flows become history)
    for d, hosts in ext.groupby("dst")["src"].unique().items():
        pop.setdefault(d, set()).update(hosts)
    day_end = df["ts"].max()
    for (s, d), x in ext.groupby(["src", "dst"]):
        hist[(s, d)] = np.r_[hist.get((s, d), np.empty(0)), _events(x["ts"].to_numpy())]
    for k in list(hist):
        v = hist[k][hist[k] > day_end - BEACON_WINDOW]
        if len(v):
            hist[k] = v
        else:
            del hist[k]
    return f.reset_index(), edges


EXTRA = ["c2_rare_flows", "c2_rare_dsts", "c2_beacon", "vol_bytes_out", "vol_bytes_in", "vol_flows_in"]


def run(days_iter, internal, local, tag=None):
    seen_ext, seen_admin = set(), set()
    state = {"pop": {}, "events": {}}
    parts, eparts = [], []
    for day, df in days_iter:
        base = day_features(df, internal, local, seen_ext, seen_admin)
        extra, edges = extra_day(df, internal, local, state)
        f = base.merge(extra, on=["host", "hour"], how="outer")
        f["day"] = day
        edges["day"] = day
        if tag:
            f["capture"], edges["capture"] = tag, tag
        parts.append(f)
        eparts.append(edges)
        print(tag or "", day, len(df), len(f), len(edges), flush=True)
    return parts, eparts


def main(kind, src, prefix, start_day="0000-00-00"):
    parts, eparts = [], []
    if kind == "dedale":
        p, e = run(dedale_days(src), "172.16.", "172.16.")
        parts += p
        eparts += e
    else:
        for capture, subnet in UNRAVELED_SUBNETS.items():
            p, e = run(((d, x) for d, x in unraveled_days(src, capture, subnet) if d >= start_day), "10.1.", subnet, capture)
            parts += p
            eparts += e
    res = finish(parts)
    # rows created only by the extra features (host active only as destination, etc.)
    res = res[res["host"].str.startswith("172.16." if kind == "dedale" else "10.1.")]
    res[EXTRA] = res[EXTRA].fillna(0)
    res.to_parquet(prefix + "_host_hour.parquet", index=False)
    edges = pd.concat(eparts, ignore_index=True)
    # Unraveled: an edge between two subnets appears in both captures; keep one copy
    edges = edges.groupby(["src", "dst", "dst_port", "hour", "day"], as_index=False)["n"].max()
    edges.to_parquet(prefix + "_edges.parquet", index=False)


if __name__ == "__main__":
    main(*sys.argv[1:])
