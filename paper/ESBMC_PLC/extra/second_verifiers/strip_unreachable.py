#!/usr/bin/env python3
"""Drop function definitions that main cannot reach from a preprocessed C file: strip_unreachable.py IN.i OUT.i

CPAchecker rejects __builtin_va_arg, which MATIEC's standard library uses in variadic functions that the
harness never calls. Top-level items are split by brace depth; an item whose text before its first depth-0 '{'
ends in ')' is a function definition. Reachability follows identifiers from main and from every kept
non-function item (global initializers can name functions). Declarations, types, and globals are kept.
"""
import re
import sys

IDENT = re.compile(r"[A-Za-z_]\w*")


def top_level_items(src):
    items, start, depth, i, n = [], 0, 0, 0, len(src)
    while i < n:
        c = src[i]
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            i = j + 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                k = i + 1
                while k < n and src[k] in " \t\n":
                    k += 1
                if k < n and src[k] == ";":
                    i = k
                else:
                    items.append(src[start:i + 1])
                    start = i + 1
                    i += 1
                    continue
        elif c == ";" and depth == 0:
            items.append(src[start:i + 1])
            start = i + 1
        i += 1
    items.append(src[start:])
    return items


def function_name(item):
    brace = item.find("{")
    if brace < 0:
        return None
    head = re.sub(r"__attribute__\s*\(\(.*?\)\)", "", item[:brace], flags=re.S).rstrip()
    if not head.endswith(")"):
        return None
    depth, j = 0, len(head) - 1
    while j >= 0:
        depth += head[j] == ")"
        depth -= head[j] == "("
        if depth == 0:
            break
        j -= 1
    names = IDENT.findall(head[:j])
    return names[-1] if names else None


def main():
    src = open(sys.argv[1], encoding="utf-8").read()
    items = top_level_items(src)
    funcs = {}
    for idx, it in enumerate(items):
        name = function_name(it)
        if name:
            funcs.setdefault(name, []).append(idx)
    func_idx = {i for idxs in funcs.values() for i in idxs}
    seen, todo = set(), ["main"]
    for idx, it in enumerate(items):
        if idx not in func_idx:
            todo += [t for t in IDENT.findall(it) if t in funcs]
    while todo:
        f = todo.pop()
        if f in seen or f not in funcs:
            continue
        seen.add(f)
        for idx in funcs[f]:
            todo += [t for t in IDENT.findall(items[idx]) if t in funcs and t not in seen]
    keep = [it for idx, it in enumerate(items) if idx not in func_idx or function_name(it) in seen]
    open(sys.argv[2], "w", encoding="utf-8").write("".join(keep))
    print(f"{len(funcs)} functions defined, {len(seen)} kept, {len(funcs) - len(seen)} dropped")


if __name__ == "__main__":
    main()
