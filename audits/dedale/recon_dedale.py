"""Phase 1 recon of DEDALE network labels (Zeek conn_labeled.csv inside zeek_<zone>.zip).

Usage: python recon_dedale.py ZIP [ZIP ...]
Aggregates file by file (router1 is ~8 GB of CSV) and writes raw counts to
dep/audit/dedale/out/<zone>_*.csv, one capture point (zone or router interface) per row group.
No estimate, no model.
"""
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
COLS = ["ts", "ip_src", "port_src", "ip_dst", "port_dst", "proto", "service", "label", "step",
        "attack_step", "tactic", "technique", "comments"]
DAY = re.compile(r"D(\d+)_(\d{4}-\d{2}-\d{2})_output_(.+)_Zeek/conn_labeled\.csv$")


def scan(zpath):
    rows = Counter()                  # (capture, day, label) -> flows
    benign_src = defaultdict(set)     # capture -> benign source IPs
    benign_port = defaultdict(Counter)  # capture -> dst port -> benign flows
    attacks = []
    with zipfile.ZipFile(zpath) as z:
        for name in sorted(n for n in z.namelist() if n.endswith("conn_labeled.csv")):
            m = DAY.search(name)
            day, capture = m.group(2), m.group(3)
            with z.open(name) as f:
                for df in pd.read_csv(f, sep=";", usecols=COLS, dtype=str, keep_default_na=False,
                                      chunksize=2_000_000):
                    for lab, n in df["label"].value_counts().items():
                        rows[(capture, day, lab)] += int(n)
                    ben = df[df["label"] == "0"]
                    benign_src[capture].update(ben["ip_src"].unique())
                    benign_port[capture].update(ben["port_dst"].value_counts().to_dict())
                    att = df[df["label"] != "0"].copy()
                    att["capture"], att["day"] = capture, day
                    attacks.append(att)
            print(name, flush=True)
    return rows, benign_src, benign_port, pd.concat(attacks, ignore_index=True)


def main(zips):
    OUT.mkdir(exist_ok=True)
    for zpath in zips:
        zone = Path(zpath).stem.replace("zeek_", "")
        rows, benign_src, benign_port, att = scan(zpath)

        r = pd.Series(rows).rename("flows")
        r.index.names = ["capture", "day", "label"]
        r.unstack(fill_value=0).to_csv(OUT / f"{zone}_rows_by_day_label.csv")

        att["ts"] = pd.to_numeric(att["ts"])
        att["hour"] = (att["ts"] // 3600).astype("int64")
        att["technique"] = att["technique"].replace({"": "none", "0": "none"})
        att.groupby(["capture", "label", "attack_step", "tactic", "technique"]).size().rename("flows").to_csv(
            OUT / f"{zone}_label_counts.csv")
        att.groupby(["capture", "technique", "ip_src", "ip_dst", "port_dst", "proto", "service"]).size().rename(
            "flows").to_csv(OUT / f"{zone}_attack_endpoints.csv")

        profiles = []
        for capture, a in att.groupby("capture"):
            g = a.groupby("technique")
            t = pd.DataFrame({
                "flows": g.size(), "days": g["day"].nunique(), "hour_windows": g["hour"].nunique(),
                "src_ips": g["ip_src"].nunique(), "dst_ips": g["ip_dst"].nunique(),
                "dst_ports": g["port_dst"].nunique(), "steps": g["step"].nunique(),
                "modal_dst_port": g["port_dst"].agg(lambda s: s.value_counts().index[0]),
                "modal_dst_port_flows": g["port_dst"].agg(lambda s: int(s.value_counts().iloc[0])),
            })
            t["benign_flows_on_modal_port"] = [benign_port[capture].get(p, 0) for p in t["modal_dst_port"]]
            t.insert(0, "capture", capture)
            profiles.append(t)
        pd.concat(profiles).to_csv(OUT / f"{zone}_technique_profile.csv")

        summary = []
        for capture in sorted({k[0] for k in rows}):
            a = att[att["capture"] == capture]
            attack_days = set(a["day"])
            summary.append({
                "capture": capture,
                "days": len({k[1] for k in rows if k[0] == capture}),
                "rows": sum(v for k, v in rows.items() if k[0] == capture),
                "attack_rows_label_ne_0": len(a),
                "attack_days": len(attack_days),
                "benign_rows_on_attack_days": sum(v for k, v in rows.items()
                                                  if k[0] == capture and k[2] == "0" and k[1] in attack_days),
                "benign_src_ips": len(benign_src[capture]),
                "attack_hosts_src_or_dst": len(set(a["ip_src"]) | set(a["ip_dst"])),
            })
        pd.DataFrame(summary).to_csv(OUT / f"{zone}_summary.csv", index=False)
        print(pd.DataFrame(summary).to_string(), flush=True)
        print(pd.concat(profiles).to_string(), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
