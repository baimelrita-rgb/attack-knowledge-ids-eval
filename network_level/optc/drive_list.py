import re, html, sys, urllib.request
def ls(fid):
    t = urllib.request.urlopen(f"https://drive.google.com/embeddedfolderview?id={fid}", timeout=30).read().decode("utf-8", "replace")
    parts = t.split('<div class="flip-entry" id="entry-')[1:]
    out = []
    for p in parts:
        eid = p.split('"', 1)[0]
        kind = "folder" if 'aria-label="Folder"' in p[:600] else "file"
        n = re.search(r'flip-entry-title">([^<]+)<', p)
        out.append((kind, html.unescape(n.group(1)) if n else "?", eid))
    return out
if __name__ == "__main__":
    for fid in sys.argv[1:]:
        for k, n, e in ls(fid): print(k, n, e)
