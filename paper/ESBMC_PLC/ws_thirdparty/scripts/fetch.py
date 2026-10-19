"""Download each hit's blob (content-addressed by git blob sha) and each repo's license and head commit."""
import base64, json, subprocess, sys, time
from pathlib import Path

HITS, RAW, MANIFEST = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OWN = {"pierredantas", "esbmc", "lucasccordeiro"}


def api(path):
    for attempt in range(4):
        r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
        if r.returncode == 0:
            return json.loads(r.stdout)
        if "404" in r.stderr or "451" in r.stderr:
            return None
        time.sleep(10 * (attempt + 1))
    return None


hits = [h for h in json.loads(HITS.read_text()) if h["repo"].split("/")[0].lower() not in OWN]
repos = {}
for repo in sorted({h["repo"] for h in hits}):
    meta = api(f"repos/{repo}")
    if meta is None:
        repos[repo] = None
        continue
    head = api(f"repos/{repo}/commits/{meta['default_branch']}")
    repos[repo] = {"license": (meta.get("license") or {}).get("spdx_id"), "default_branch": meta["default_branch"],
                   "head_commit": head["sha"] if head else None, "stars": meta.get("stargazers_count")}

for i, h in enumerate(hits):
    dest = RAW / f"{h['sha']}.xml"
    h["repo_meta"] = repos.get(h["repo"])
    if not dest.exists():
        blob = api(f"repos/{h['repo']}/git/blobs/{h['sha']}")
        if blob is None:
            h["fetched"] = False
            continue
        dest.write_bytes(base64.b64decode(blob["content"]))
    h["fetched"] = True
    if i % 100 == 0:
        print(f"{i}/{len(hits)}", flush=True)

MANIFEST.write_text(json.dumps(hits, indent=1))
print(f"{sum(h['fetched'] for h in hits)} of {len(hits)} fetched from {len(repos)} repos")
