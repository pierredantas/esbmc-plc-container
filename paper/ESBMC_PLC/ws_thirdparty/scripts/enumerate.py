"""List PLCopen XML files with LD power rails on GitHub via code search, sliced by size."""
import json, subprocess, sys, time
from pathlib import Path

SLICES = ["<5000", "5000..20000", "20000..50000", "50000..100000", "100000..200000", ">200000"]
OUT = Path(sys.argv[1])


def search(q, page):
    for attempt in range(5):
        r = subprocess.run(["gh", "api", "-X", "GET", "search/code", "-f", f"q={q}",
                            "-f", "per_page=100", "-f", f"page={page}"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return json.loads(r.stdout)
        time.sleep(30 * (attempt + 1))
    raise RuntimeError(r.stderr)


hits = {}
for s in SLICES:
    q = f"leftPowerRail extension:xml size:{s}"
    page = 1
    while True:
        d = search(q, page)
        items = d.get("items", [])
        for it in items:
            key = (it["repository"]["full_name"], it["path"])
            hits[key] = {"repo": it["repository"]["full_name"], "path": it["path"], "sha": it["sha"],
                         "fork": it["repository"]["fork"], "html_url": it["html_url"]}
        print(f"{s} page {page}: {len(items)} (total {d['total_count']}, collected {len(hits)})", flush=True)
        time.sleep(7)
        if len(items) < 100 or page * 100 >= min(d["total_count"], 1000):
            break
        page += 1

OUT.write_text(json.dumps(sorted(hits.values(), key=lambda h: (h["repo"], h["path"])), indent=1))
print(f"wrote {len(hits)} hits")
