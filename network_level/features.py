"""Per (host, hour) features for the pilots (P1, P2). See PILOT.md / PILOT_P2.md.

Usage:
  python features.py dedale ZIP OUT_PARQUET
  python features.py unraveled FLOWS_DIR OUT_PARQUET [START_DAY]
Days before START_DAY are skipped entirely (not even used as novelty history).
Labels are carried through only as evaluation columns (n_attack_flows, techniques, tactics); they are never features.
"""
import sys

import numpy as np
import pandas as pd

from flows import dedale_days, unraveled_days

ADMIN = {"22", "135", "139", "445", "3389", "5985", "5986"}
UNRAVELED_SUBNETS = {"net1011x": "10.1.1.", "net1012x": "10.1.2.", "net1013x": "10.1.3.",
                     "net1014x": "10.1.4.", "net1015x": "10.1.5."}


def _new_unique(x, flag, key):
    return x.loc[x[flag], key].nunique()


def day_features(df, internal, local, seen_ext, seen_admin):
    """internal: prefix of the whole internal network; local: prefix of the hosts described by this capture."""
    df = df.copy()
    df["hour"] = (df["ts"] // 3600).astype("int64")
    src_int, dst_int = df["src"].str.startswith(internal), df["dst"].str.startswith(internal)
    src_loc, dst_loc = df["src"].str.startswith(local), df["dst"].str.startswith(local)
    ext = df[src_loc & ~dst_int].copy()
    ext["new_ext"] = ~(ext["src"] + "|" + ext["dst"]).isin(seen_ext)
    adm = df[src_int & dst_int & df["dst_port"].isin(ADMIN)].copy()
    adm["edge"] = adm["src"] + "|" + adm["dst"] + "|" + adm["dst_port"]
    adm["new_edge"] = ~adm["edge"].isin(seen_admin)

    out = df[src_loc]
    g = out.groupby(["src", "hour"])
    f = pd.DataFrame({
        "flows_out": g.size(),
        "recon_dst_ips": g["dst"].nunique(),
        "recon_dst_ports": g["dst_port"].nunique(),
        "recon_failed_share": g["failed"].mean(),
    })
    if len(ext):
        e = ext.assign(ne_ob=ext["bytes_out"] * ext["new_ext"]).groupby(["src", "hour"])
        f = f.join(pd.DataFrame({
            "c2_new_ext_dsts": e.apply(_new_unique, "new_ext", "dst", include_groups=False),
            "c2_flows_new_ext": e["new_ext"].sum(),
            "c2_bytes_new_ext": e["ne_ob"].sum(),
            "exf_bytes_out_ext": e["bytes_out"].sum(),
            "exf_ratio_ext": np.log1p(e["bytes_out"].sum()) - np.log1p(e["bytes_in"].sum()),
        }), how="outer")
    a_out = adm[adm["src"].str.startswith(local)]
    if len(a_out):
        a = a_out.groupby(["src", "hour"])
        f = f.join(pd.DataFrame({
            "lm_new_edges_out": a.apply(_new_unique, "new_edge", "edge", include_groups=False),
            "lm_admin_flows": a.size(),
        }), how="outer")
    a_in = adm[adm["dst"].str.startswith(local)]
    if len(a_in):
        lm_in = a_in.groupby(["dst", "hour"]).apply(_new_unique, "new_edge", "edge", include_groups=False)
        lm_in = lm_in.rename("lm_new_edges_in")
        lm_in.index.names = ["src", "hour"]
        f = f.join(lm_in, how="outer")

    att = df[df["label"] == 1]
    ev = pd.concat([att.assign(host=att["src"]), att.assign(host=att["dst"])])
    ev = ev[ev["host"].str.startswith(local)]
    if len(ev):
        eg = ev.groupby(["host", "hour"])
        evf = pd.DataFrame({"n_attack_flows": eg.size(),
                            "techniques": eg["technique"].agg(lambda s: ",".join(sorted(set(s)))),
                            "tactics": eg["tactic"].agg(lambda s: ",".join(sorted(set(s))))})
        evf.index.names = ["src", "hour"]
        f = f.join(evf, how="outer")

    seen_ext.update(ext["src"] + "|" + ext["dst"])
    seen_admin.update(adm["edge"])
    f.index.names = ["host", "hour"]
    return f.reset_index()


FEATURES = ["flows_out", "recon_dst_ips", "recon_dst_ports", "recon_failed_share", "c2_new_ext_dsts",
            "c2_flows_new_ext", "c2_bytes_new_ext", "exf_bytes_out_ext", "exf_ratio_ext", "lm_new_edges_out",
            "lm_admin_flows", "lm_new_edges_in", "n_attack_flows"]


def finish(parts):
    res = pd.concat(parts, ignore_index=True)
    for c in FEATURES + ["techniques", "tactics"]:
        if c not in res:
            res[c] = np.nan
    res[FEATURES] = res[FEATURES].fillna(0)
    res["n_attack_flows"] = res["n_attack_flows"].astype(int)
    return res


def main(kind, src, out, start_day="0000-00-00"):
    parts = []
    if kind == "dedale":
        seen_ext, seen_admin = set(), set()
        for day, df in dedale_days(src):
            f = day_features(df, "172.16.", "172.16.", seen_ext, seen_admin)
            f["day"] = day
            parts.append(f)
            print(day, len(df), len(f), flush=True)
    elif kind == "unraveled":
        for capture, subnet in UNRAVELED_SUBNETS.items():
            seen_ext, seen_admin = set(), set()
            for day, df in unraveled_days(src, capture, subnet):
                if day < start_day:
                    continue
                f = day_features(df, "10.1.", subnet, seen_ext, seen_admin)
                f["day"], f["capture"] = day, capture
                parts.append(f)
            print(capture, flush=True)
    finish(parts).to_parquet(out, index=False)


if __name__ == "__main__":
    main(*sys.argv[1:])
