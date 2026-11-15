#!/usr/bin/env python3
"""PR-05 B: rustdoc JSON (pinned nightly-2026-07-01, format_version 60) as an independent Rust object inventory, compared with the record."""
import json, re, glob, collections, sys
B5 = sys.argv[1]
rec = json.load(open(f"{B5}/evidence.json"))
objs = [o["id"] for o in rec["objects"] if o["lang"] == "rust"]
def tyname(t):
    if not isinstance(t, dict): return "?"
    if "resolved_path" in t: return t["resolved_path"].get("path") or t["resolved_path"].get("name", "?")
    return t.get("primitive") or t.get("generic") or next(iter(t), "?")
docs = []  # (kind, crate, name, container)
fv = set()
for f in sorted(glob.glob(f"{B5}/rustdoc/*.json")):
    d = json.load(open(f)); fv.add(d["format_version"]); idx = d["index"]
    crate = idx[str(d["root"])]["name"]
    # free functions: every local function item that is not a member of an impl/trait
    members = set()
    for it in idx.values():
        k = next(iter(it["inner"]), None)
        if k in ("impl", "trait"):
            members |= {str(i) for i in it["inner"][k].get("items", [])}
    for iid, it in idx.items():
        if it.get("crate_id") != 0: continue
        k = next(iter(it["inner"]), None)
        if k == "function" and iid not in members:
            docs.append(("free", crate, it["name"], ""))
        elif k == "impl":
            im = it["inner"]["impl"]
            if im.get("is_synthetic") or im.get("blanket_impl"): continue
            fo = tyname(im["for"]); tr = im.get("trait")
            for mid in im["items"]:
                mi = idx[str(mid)]
                if "function" in mi["inner"]:
                    docs.append(("trait" if tr else "inherent", crate, mi["name"], fo))
print("format_version:", sorted(fv), "| function items:", dict(collections.Counter(k for k, *_ in docs)), "total", len(docs))
def kind(k):
    b = k[len("rust:"):]
    return "trait" if b.startswith("<") and " as " in b else "inherent" if b.startswith("<") else "free"
def crate_of(k):
    b = k[len("rust:"):].lstrip("<"); 
    return b if "::" not in b and " " not in b else re.split(r"::| ", b)[0]
def name_of(k): return re.sub(r"<[^<>]*>$", "", k[len("rust:"):]).split("::")[-1]
print("record objects:", len(objs), dict(collections.Counter(kind(k) for k in objs)))
unq = [k for k in objs if kind(k) == "free" and "::" not in k[len("rust:"):]]
print("record ids WITHOUT a crate path (the #[no_mangle] symbols):", len(unq), sorted(unq))
D = collections.Counter((c, n) for _, c, n, _ in docs)
R = collections.Counter((crate_of(k), name_of(k)) for k in objs if k not in unq)
for k in unq: R[("cic_ffi", name_of(k))] += 1   # the no_mangle symbols live in cic_ffi
inter = sum((D & R).values())
print(f"(crate, name) multiset: rustdoc {sum(D.values())}, record {sum(R.values())}, in both {inter}")
print("  in the record, not in rustdoc:", sum((R - D).values()), dict(list((R - D).items())[:8]))
print("  in rustdoc, not in the record:", sum((D - R).values()), dict(list((D - R).items())[:8]))
