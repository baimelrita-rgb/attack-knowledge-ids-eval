"""Stream LANL auth.txt.gz once and aggregate successful cross-computer LogOn events per day.

Input fields: time, src user@domain, dst user@domain, src computer, dst computer, auth type, logon type,
auth orientation, success/failure. Kept: orientation == LogOn, success == Success, src computer != dst computer.
Output (parquet): day, src, dst, logon_type, auth_type, machine_account (src user ends with '$'), n, first_t, last_t.
Usage: python aggregate_auth.py AUTH_GZ OUT_PARQUET
"""
import sys

import pandas as pd

COLS = ["t", "su", "du", "sc", "dc", "at", "lt", "ori", "ok"]


def main(src, out):
    parts, rows = [], 0
    reader = pd.read_csv(src, names=COLS, header=None, chunksize=10_000_000, dtype=str,
                         compression="gzip", engine="c")
    for i, c in enumerate(reader):
        rows += len(c)
        c = c[(c["ori"] == "LogOn") & (c["ok"] == "Success") & (c["sc"] != c["dc"])]
        c["t"] = c["t"].astype("int64")
        c["day"] = (c["t"] - 1) // 86400 + 1
        c["machine_account"] = c["su"].str.split("@").str[0].str.endswith("$")
        g = c.groupby(["day", "sc", "dc", "lt", "at", "machine_account"]).agg(
            n=("t", "size"), first_t=("t", "min"), last_t=("t", "max")).reset_index()
        parts.append(g)
        print(f"chunk {i} rows {rows} kept {len(c)} groups {len(g)}", flush=True)
    a = pd.concat(parts, ignore_index=True).groupby(["day", "sc", "dc", "lt", "at", "machine_account"]).agg(
        n=("n", "sum"), first_t=("first_t", "min"), last_t=("last_t", "max")).reset_index()
    a = a.rename(columns={"sc": "src", "dc": "dst", "lt": "logon_type", "at": "auth_type"})
    a.to_parquet(out, index=False)
    print("total rows", rows, "aggregated", len(a), flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
