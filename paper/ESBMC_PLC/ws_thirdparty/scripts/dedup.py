"""Group fetched files by normalized content and describe each distinct program.

Two files count as one program when their <types> and <instances> sections agree after
dropping timestamps and whitespace: tutorials and course repos copy projects verbatim,
and the file header (company, dates) is all that differs.
"""
import collections, hashlib, json, re, sys
from pathlib import Path

MANIFEST, RAW, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])

DATE_ATTR = re.compile(r'\s(creationDateTime|modificationDateTime)="[^"]*"')
BODY = re.compile(r"<body[^>]*>\s*<(LD|FBD|ST|IL|SFC)\b")


def normalize(text):
    m = re.search(r"<types\b.*</instances>", text, re.S) or re.search(r"<types\b.*</types>", text, re.S)
    core = m.group(0) if m else text
    return re.sub(r"\s+", "", DATE_ATTR.sub("", core))


def describe(text):
    bodies = collections.Counter(BODY.findall(text))
    return {
        "bodies": dict(bodies),
        "pous": len(re.findall(r"<pou\b", text)),
        "contacts": len(re.findall(r"<contact\b", text)),
        "coils": len(re.findall(r"<coil\b", text)),
        "blocks": len(re.findall(r"<block\b", text)),
        "user_fbs": len(re.findall(r'pouType="functionBlock"', text)),
        "has_config": "<configuration" in text,
        "ns": (re.search(r"plcopen\.org/xml/(tc6_\d+)", text) or [None, None])[1],
        "bytes": len(text.encode()),
    }


hits = [h for h in json.loads(MANIFEST.read_text()) if h.get("fetched")]
groups = {}
for h in hits:
    text = (RAW / f"{h['sha']}.xml").read_text(encoding="utf-8", errors="replace").lstrip("﻿")
    key = hashlib.sha256(normalize(text).encode()).hexdigest()[:16]
    g = groups.setdefault(key, {"id": key, "sha": h["sha"], "copies": [], **describe(text)})
    g["copies"].append({"repo": h["repo"], "path": h["path"], "sha": h["sha"],
                        "license": (h.get("repo_meta") or {}).get("license"),
                        "commit": (h.get("repo_meta") or {}).get("head_commit")})

progs = sorted(groups.values(), key=lambda g: g["id"])
for g in progs:
    g["repos"] = sorted({c["repo"] for c in g["copies"]})
OUT.write_text(json.dumps(progs, indent=1))

ld = [g for g in progs if g["bodies"].get("LD")]
print(f"{len(hits)} files -> {len(progs)} distinct programs; {len(ld)} with an LD body")
print("bodies over distinct programs:", collections.Counter(k for g in progs for k in g["bodies"]))
print("LD-only programs:", sum(1 for g in ld if set(g["bodies"]) == {"LD"}))
print("LD programs by first repo:", collections.Counter(g["repos"][0] for g in ld).most_common(15))
