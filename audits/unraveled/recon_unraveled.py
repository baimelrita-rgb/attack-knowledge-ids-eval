"""Phase 1 recon of Unraveled (DAPT2021) labelled NFStream flows.

Usage: python recon_unraveled.py DIR   (DIR = data_raw/unraveled/processed/network-flows)
Capture point = file name prefix (net1011x ... net1015x, netgw); day folder = folder name.
Writes raw counts to dep/audit/unraveled/out/. No estimate, no model.
"""
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
# Some rows carry unquoted commas inside trailing text fields (user_agent, fingerprints), so they have more
# fields than the header. The leading numeric fields are never affected and the 4 labels are always last:
# read leading fields by position and labels from the end; count the malformed rows.
LEAD = {"src_ip": 2, "dst_ip": 6, "dst_port": 9, "protocol": 10, "bidirectional_first_seen_ms": 14}
LABELS = ["Activity", "Stage", "DefenderResponse", "Signature"]
malformed = Counter()


def read_rows(path, chunk=1_000_000):
    with open(path, newline="") as fh:
        r = csv.reader(fh)
        header = next(r)
        assert [header[i] for i in LEAD.values()] == list(LEAD) and header[-4:] == LABELS, path
        buf = []
        for row in r:
            if len(row) != len(header):
                malformed[path.name.split("_")[0]] += 1
            buf.append([row[i] for i in LEAD.values()] + row[-4:])
            if len(buf) == chunk:
                yield pd.DataFrame(buf, columns=list(LEAD) + LABELS)
                buf = []
        if buf:
            yield pd.DataFrame(buf, columns=list(LEAD) + LABELS)


def main(root):
    OUT.mkdir(exist_ok=True)
    rows = Counter()                     # (capture, folder, is_benign) -> flows
    labels = Counter()                   # (capture, Activity, Stage, Signature, DefenderResponse) -> flows
    benign_src = defaultdict(set)
    benign_port = defaultdict(Counter)
    attacks = []
    for f in sorted(Path(root).rglob("*_Flow_labeled.csv")):
        capture, folder = f.name.split("_")[0], f.parent.name
        for df in read_rows(f):
            ben = df["Stage"] == "Benign"
            for k, n in df.groupby(["Activity", "Stage", "Signature", "DefenderResponse"]).size().items():
                labels[(capture,) + k] += int(n)
            rows[(capture, folder, "benign")] += int(ben.sum())
            rows[(capture, folder, "attack")] += int((~ben).sum())
            benign_src[capture].update(df.loc[ben, "src_ip"].unique())
            benign_port[capture].update(df.loc[ben, "dst_port"].value_counts().to_dict())
            a = df[~ben].copy()
            a["capture"], a["folder"] = capture, folder
            attacks.append(a)
        print(f, flush=True)

    r = pd.Series(rows).rename("flows")
    r.index.names = ["capture", "folder", "class"]
    r.unstack(fill_value=0).to_csv(OUT / "rows_by_folder.csv")
    lc = pd.Series(labels).rename("flows")
    lc.index.names = ["capture", "Activity", "Stage", "Signature", "DefenderResponse"]
    lc.to_csv(OUT / "label_counts.csv")

    att = pd.concat(attacks, ignore_index=True)
    att["hour"] = pd.to_numeric(att["bidirectional_first_seen_ms"]) // 3_600_000
    att["day"] = pd.to_datetime(pd.to_numeric(att["bidirectional_first_seen_ms"]), unit="ms").dt.date
    att.groupby(["capture", "Activity", "Signature", "src_ip", "dst_ip", "dst_port", "protocol"]).size().rename(
        "flows").to_csv(OUT / "attack_endpoints.csv")
    att.groupby(["capture", "Activity", "Stage", "Signature", "day"]).agg(
        flows=("hour", "size"), hour_windows=("hour", "nunique")).to_csv(OUT / "attack_by_day.csv")

    profiles = []
    for capture, a in att.groupby("capture"):
        g = a.groupby("Activity")
        t = pd.DataFrame({
            "flows": g.size(), "days": g["day"].nunique(), "hour_windows": g["hour"].nunique(),
            "signatures": g["Signature"].nunique(), "src_ips": g["src_ip"].nunique(),
            "dst_ips": g["dst_ip"].nunique(), "dst_ports": g["dst_port"].nunique(),
            "modal_dst_port": g["dst_port"].agg(lambda s: s.value_counts().index[0]),
            "modal_dst_port_flows": g["dst_port"].agg(lambda s: int(s.value_counts().iloc[0])),
        })
        t["benign_flows_on_modal_port"] = [benign_port[capture].get(p, 0) for p in t["modal_dst_port"]]
        t.insert(0, "capture", capture)
        profiles.append(t)
    prof = pd.concat(profiles)
    prof.to_csv(OUT / "activity_profile.csv")

    summary = []
    for capture in sorted({k[0] for k in rows}):
        a = att[att["capture"] == capture]
        attack_folders = {k[1] for k, v in rows.items() if k[0] == capture and k[2] == "attack" and v}
        summary.append({
            "capture": capture,
            "folders": len({k[1] for k in rows if k[0] == capture}),
            "flows": sum(v for k, v in rows.items() if k[0] == capture),
            "attack_flows": len(a),
            "attack_folders": len(attack_folders),
            "benign_flows_in_attack_folders": sum(v for k, v in rows.items()
                                                  if k[0] == capture and k[2] == "benign" and k[1] in attack_folders),
            "malformed_rows": malformed[capture],
            "benign_src_ips": len(benign_src[capture]),
            "attack_hosts_src_or_dst": len(set(a["src_ip"]) | set(a["dst_ip"])),
            "activities_ge_50_flows_and_ge_3_hours": int(((prof.loc[prof["capture"] == capture, "flows"] >= 50)
                                                          & (prof.loc[prof["capture"] == capture, "hour_windows"] >= 3)).sum()),
        })
    s = pd.DataFrame(summary)
    s.to_csv(OUT / "summary.csv", index=False)
    print(s.to_string(), flush=True)
    print(prof.to_string(), flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
