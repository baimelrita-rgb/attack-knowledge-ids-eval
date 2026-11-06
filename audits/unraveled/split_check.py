"""R4 check for Unraveled: chronological split of days 60/20/20 (by calendar day of the attack flows' first packet).

Counts, per capture point and split, the activities with >= 50 flows and >= 3 one-hour windows.
Input: out/attack_by_day.csv and out/rows_by_folder.csv. Output: out/r4_chronological_split.csv.
"""
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
a = pd.read_csv(OUT / "attack_by_day.csv", parse_dates=["day"])
days = sorted(a["day"].unique())
# Split on the calendar span of the dataset (first to last attack day), 60/20/20.
lo, hi = days[0], days[-1]
span = (hi - lo).days + 1
cut1, cut2 = lo + pd.Timedelta(days=int(span * 0.6)), lo + pd.Timedelta(days=int(span * 0.8))
a["split"] = pd.cut(a["day"], [lo - pd.Timedelta(days=1), cut1 - pd.Timedelta(days=1), cut2 - pd.Timedelta(days=1), hi],
                    labels=["train", "val", "test"])
g = a.groupby(["capture", "split", "Activity"], observed=True).agg(flows=("flows", "sum"), hour_windows=("hour_windows", "sum"))
g["meets_50_and_3h"] = (g["flows"] >= 50) & (g["hour_windows"] >= 3)
g.to_csv(OUT / "r4_chronological_split.csv")
per_split = g.groupby(["capture", "split"], observed=True)["meets_50_and_3h"].sum().unstack(fill_value=0)
in_all = g[g["meets_50_and_3h"]].reset_index().groupby(["capture", "Activity"])["split"].nunique()
per_split["activities_meeting_in_all_3_splits"] = in_all[in_all == 3].groupby("capture").size().reindex(per_split.index, fill_value=0)
per_split.to_csv(OUT / "r4_summary.csv")
print("attack days:", lo.date(), "to", hi.date(), "| cut points:", cut1.date(), cut2.date())
print(per_split.to_string())
print(a.groupby(["Signature", "Stage"])["flows"].sum().to_string())
print(a.groupby("Signature")["day"].agg(["min", "max"]).to_string())
