"""Add ground-truth part (b) (report timeline host-hours) to the OpTC host-hour table and apply the
pre-registered rule for train/calibration: host-hours with attack flows on those days are reported and removed.

Usage: python add_gt.py HOST_HOUR_GNN_PARQUET TIMELINE_CSV OUT_PARQUET TRAIN_START CAL_END
"""
import json
import sys

import pandas as pd


def main(src, timeline, out, tr0, ca1):
    f = pd.read_parquet(src)
    t = pd.read_csv(timeline)[["host_ip", "utc_hour"]].drop_duplicates()
    t["timeline"] = True
    f = f.merge(t, left_on=["host", "hour"], right_on=["host_ip", "utc_hour"], how="left").drop(columns=["host_ip", "utc_hour"])
    f["timeline"] = f["timeline"].fillna(False).astype(bool)
    rep = {"timeline_host_hours": int(len(t)), "timeline_host_hours_with_traffic_row": int(f["timeline"].sum()),
           "c2_flow_host_hours": int((f["n_attack_flows"] > 0).sum())}
    add = f["timeline"] & (f["n_attack_flows"] == 0)
    f.loc[add, "n_attack_flows"] = 1
    f.loc[add, "tactics"] = "timeline"
    pre = (f["day"] >= tr0) & (f["day"] <= ca1) & (f["n_attack_flows"] > 0)
    rep["attack_host_hours_in_train_or_cal_removed"] = f.loc[pre, ["host", "day", "hour", "n_attack_flows"]].to_dict("records")
    f = f[~pre]
    rep["positive_host_hours_total"] = int((f["n_attack_flows"] > 0).sum())
    f.to_parquet(out, index=False)
    print(json.dumps(rep, indent=1, default=str))


if __name__ == "__main__":
    main(*sys.argv[1:])
