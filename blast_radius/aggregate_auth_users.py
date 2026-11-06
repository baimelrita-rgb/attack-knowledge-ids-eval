"""Second pass over LANL auth (streamed from stdin, gzip): user-level sessions for credential-exposure modelling.

Kept: orientation == LogOn, success == Success, source user is not a machine account (does not end with '$').
Same-computer logons (src == dst) are kept: they leave credentials on that computer.
Output (parquet): day, user, src, dst, logon_type, n, first_t, last_t.
Usage: curl ... | gzip -dc | awk prefilter | python aggregate_auth_users.py OUT_PARQUET  (add --gzip for compressed stdin)
"""
import sys

import pandas as pd

COMPRESSION = "gzip" if "--gzip" in sys.argv else None
COLS = ["t", "su", "du", "sc", "dc", "at", "lt", "ori", "ok"]


def main(out):
    parts, rows = [], 0
    reader = pd.read_csv(sys.stdin.buffer, names=COLS, header=None, chunksize=10_000_000, dtype=str,
                         compression=COMPRESSION, usecols=["t", "su", "sc", "dc", "lt", "ori", "ok"])
    for i, c in enumerate(reader):
        rows += len(c)
        c = c[(c["ori"] == "LogOn") & (c["ok"] == "Success")]
        user = c["su"].str.split("@").str[0]
        c = c[~user.str.endswith("$")].assign(user=user[~user.str.endswith("$")])
        c["t"] = c["t"].astype("int64")
        c["day"] = (c["t"] - 1) // 86400 + 1
        g = c.groupby(["day", "user", "sc", "dc", "lt"]).agg(n=("t", "size"), first_t=("t", "min"), last_t=("t", "max")).reset_index()
        parts.append(g)
        print(f"chunk {i} rows {rows} kept {len(c)} groups {len(g)}", flush=True)
    a = pd.concat(parts, ignore_index=True).groupby(["day", "user", "sc", "dc", "lt"]).agg(
        n=("n", "sum"), first_t=("first_t", "min"), last_t=("last_t", "max")).reset_index()
    a.rename(columns={"sc": "src", "dc": "dst", "lt": "logon_type"}).to_parquet(out, index=False)
    print("total rows", rows, "aggregated", len(a), flush=True)


if __name__ == "__main__":
    main(*[a for a in sys.argv[1:] if a != "--gzip"])
