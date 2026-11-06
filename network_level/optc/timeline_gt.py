"""Ground-truth part (b) for OpTC: hosts named in the red-team report timeline, per UTC hour.

Input: redteam_report.txt (pdftotext -layout of OpTCRedTeamGroundTruth.pdf). Each entry starts with
"MM/DD/YY HH:MM:SS --" (local time, UTC-4) and continues until the next entry or a blank line.
Hosts: Sysclient#### (also the report's typo "Sysclinet") and DC1. Mapping verified on eCAR (PILOT_P3.md).
Output: timeline_host_hours.csv (host_ip, hostname, utc_hour, utc_time, entry).
"""
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ENTRY = re.compile(r"^(\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) -- (.*)$")
HOST = re.compile(r"(?i)\bsys\s*cli(?:ent|net)\s*(\d{4})\b|\bDC1\b")


def host_ip(m):
    if m.group(1) is None:
        return "DC1", "142.20.61.130"
    n = int(m.group(1)) + 1
    return f"SysClient{m.group(1)}", f"142.20.{56 + n // 256}.{n % 256}"


def main(src, out):
    entries, cur = [], None
    for line in Path(src).read_text().splitlines():
        m = ENTRY.match(line.strip())
        if m:
            cur = [m.group(1), m.group(2)]
            entries.append(cur)
        elif cur is not None and line.strip() and not line.startswith("   "):
            cur[1] += " " + line.strip()
        else:
            cur = None
    rows = []
    for t, text in entries:
        utc = datetime.strptime(t, "%m/%d/%y %H:%M:%S") + timedelta(hours=4)
        for m in HOST.finditer(text):
            name, ip = host_ip(m)
            rows.append({"host_ip": ip, "hostname": name, "utc_time": utc.isoformat(),
                         "utc_hour": int(utc.timestamp() // 3600) if utc.tzinfo else int((utc - datetime(1970, 1, 1)).total_seconds() // 3600),
                         "entry": f"{t} -- {text}"[:200]})
    df = pd.DataFrame(rows).drop_duplicates(["host_ip", "utc_hour", "entry"])
    df.to_csv(out, index=False)
    print(len(entries), "entries;", len(df), "host-entry rows;", df[["host_ip", "utc_hour"]].drop_duplicates().shape[0],
          "host-hours;", df["host_ip"].nunique(), "hosts")


if __name__ == "__main__":
    main(*sys.argv[1:])
