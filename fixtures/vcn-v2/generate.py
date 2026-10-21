#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-SA-4.0
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""Generates fixtures/vcn-v2: the scope-aware common OCI VCN fixture of the Intent -> Observed -> Conformance -> Evidence slice.

    generate.py            write the files next to this script
    generate.py --check    fail if the files on disk differ from what is generated

v2 encodes the owner decisions of 2026-10-21 on top of what v1 proved (v1 stays as it is; see README.md for the exact diff):

  * a field the intent does not declare is UNMANAGED: its OCI value alone is not drift. The conformance plan is DERIVED PER CASE
    from the intent and its management scope (expected/plan.json), not from the fields of the observed object;
  * observed state, conformance scope and evidence are separate: observed.* keeps everything seen, the verdict covers only the
    declared scope, the evidence states that CONFORMANT applies to the declared scope only;
  * tags: only the tag keys the intent declares are compared (management.tags_scope = "declared-keys", the default), unless the
    intent declares a full-set supervision ("full-set");
  * an empty cidrBlocks in a successful GetVcn answer is not a trustworthy CIDR state: coverage unknown, the raw value is kept.

Stages, per case (cases/<id>/):

  intent.registry.json             {"config": registry-named wanted values, "management": {"tags_scope": ...}}
  oci/response.json | oci/error.json   what OCI answered to GetVcn (or why it did not)
  expected/observed.oci.json       3. the oracle module's normalization: effective_config, state, coverage, observed_raw (OCI names)
  expected/observed.registry.json  4. the same in registry names; EVERYTHING seen, managed or not; coverage per seen path
  expected/plan.json               4b. the conformance plan derived from the intent
  expected/scope.json              4b. managed paths / unmanaged observed paths
  expected/engine-input.json       4c. exactly what the engine is given (intent, observed PROJECTED to the declared scope,
                                       observation list, plan) in the shape of the engine's differential vectors
  expected/verdict.fields.json     5. the verdict per path and for the object (engine semantics)
  expected/evidence.claims.json    6. what an evidence record may claim

Why 4c exists: the engine's collection elements are the UNION of the element identities of the intent and the observed list
(cic-primitive-engine plan.rs element_keys), and a collection plan has no key filter. "Only the declared tag keys" can therefore
not be said in the plan; the environment must project the observed list to the declared keys before the engine sees it. The full
observed list stays in observed.registry.json and in the evidence.

Engine semantics used (cic-primitive-engine origin/main conformance.rs / plan.rs): classify_field (coverage Observed: matched ->
CONFORMANT else DRIFT; Absent: intent present -> DRIFT else OBSERVED_ABSENT; Unobserved/Unknown -> UNOBSERVED), compare_exact
(different JSON kinds -> NOT_COMPARABLE, a null intent counts as a kind), aggregate (DRIFT/NOT_COMPARABLE > UNOBSERVED >
CONFORMANT). The reference rules below restate them; they are not an implementation to reuse.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

SCALARS = ["cidr_block", "dns_label", "ipv6_enabled"]    # the scalar config fields a plan can carry
NOT_PLANNABLE = ["/secondary_cidr_blocks", "/display_name", "/compartment_id", "/lifecycle_state", "/ipv6_cidr_blocks"]
LIFECYCLE = {
    "PROVISIONING": "pending", "AVAILABLE": "available", "UPDATING": "unknown", "TERMINATING": "deleting", "TERMINATED": "deleted",
}
LIFECYCLE_OTHER = "unknown"
OCI_PATHS = ["/cidrBlocks", "/dnsLabel", "/freeformTags", "/isIpv6Enabled"]

BASE_CONFIG = {"cidr_block": "10.0.0.0/16", "dns_label": "prod", "ipv6_enabled": False,
               "tags": [{"key": "env", "value": "prod"}, {"key": "owner", "value": "net"}]}
DECLARED = {"tags_scope": "declared-keys"}
FULL_SET = {"tags_scope": "full-set"}
BASE_RESPONSE = {
    "id": "ocid1.vcn.oc1.eu-frankfurt-1.aaaaaaaaexample", "compartmentId": "ocid1.compartment.oc1..bbbbbbbbexample",
    "displayName": "prod-vcn", "dnsLabel": "prod", "lifecycleState": "AVAILABLE", "cidrBlocks": ["10.0.0.0/16"],
    "ipv6CidrBlocks": [], "freeformTags": {"env": "prod", "owner": "net"}, "definedTags": {},
    "defaultRouteTableId": "ocid1.routetable.oc1.eu-frankfurt-1.cccccccexample", "timeCreated": "2026-07-19T00:00:00Z",
}


def without(d, *keys):
    return {k: v for k, v in d.items() if k not in keys}


def with_(d, **kw):
    out = dict(d)
    out.update(kw)
    return out


def intent(config=None, management=None):
    return {"config": BASE_CONFIG if config is None else config, "management": DECLARED if management is None else management}


# case id -> (description, intent, response | None, error | None)
CASES = {
    "conformant": ("everything wanted is there", intent(), BASE_RESPONSE, None),
    "drift": ("the dns label and one tag value differ", intent(),
              with_(BASE_RESPONSE, dnsLabel="staging", freeformTags={"env": "dev", "owner": "net"}), None),
    "field-absent": ("a wanted dns label that OCI does not report (not set): DRIFT, not 'unknown'", intent(),
                     without(BASE_RESPONSE, "dnsLabel"), None),
    "desired-absent": ("the dns label is not declared and OCI has none: it is not planned, there is no verdict entry",
                       intent(without(BASE_CONFIG, "dns_label")), without(BASE_RESPONSE, "dnsLabel"), None),
    "desired-absent-observed-present": (
        "DECISION CASE: the dns label is not declared and OCI has one: unmanaged, not planned, not drift; seen and listed as unmanaged",
        intent(without(BASE_CONFIG, "dns_label")), BASE_RESPONSE, None),
    "partial-read": ("the answer has no ipv6CidrBlocks at all: ipv6_enabled was not observed, it is not 'false'", intent(),
                     without(BASE_RESPONSE, "ipv6CidrBlocks"), None),
    "malformed-cidr": ("cidrBlocks is not a list: it was read but cannot be trusted: unknown", intent(),
                       with_(BASE_RESPONSE, cidrBlocks="10.0.0.0/16"), None),
    "empty-cidr-blocks": ("a successful answer with cidrBlocks [] : OCI requires one IPv4 block, so the empty list is not a "
                          "trustworthy state: unknown, the raw [] is kept", intent(), with_(BASE_RESPONSE, cidrBlocks=[]), None),
    "not-found": ("HTTP 404 NotAuthorizedOrNotFound: OCI does not tell 'deleted' from 'not allowed', so absence is NOT authoritative",
                  intent(), None, {"kind": "http", "status": 404, "code": "NotAuthorizedOrNotFound"}),
    "transport-error": ("no answer (timeout): nothing was observed", intent(), None, {"kind": "transport", "message": "timeout"}),
    "extra-tag-undeclared": ("OCI has a tag the intent does not declare; declared-keys scope: seen, unmanaged, not compared", intent(),
                             with_(BASE_RESPONSE, freeformTags={"env": "prod", "owner": "net", "cost-center": "42"}), None),
    "extra-tag-full-set": ("the same extra tag under an explicit full-set tag supervision: it is in the scope, and an observed tag "
                           "the intent does not carry is NOT_COMPARABLE in the engine (object DRIFT)", intent(management=FULL_SET),
                           with_(BASE_RESPONSE, freeformTags={"env": "prod", "owner": "net", "cost-center": "42"}), None),
    "declared-tag-missing": ("a declared tag key that OCI does not have, while the tags were read: authoritative absence, DRIFT",
                             intent(), with_(BASE_RESPONSE, freeformTags={"env": "prod"}), None),
}


# --- stage 3: the module's normalization (reference) ----------------------------------------------------------------------
def stage3(resp, err):
    cov, eff, state, raw = {}, {}, {}, {}
    if resp is None:
        c = "unknown" if err["kind"] == "http" else "unobserved"   # 404 cannot be told from 403; a timeout simply was not an answer
        return {"coverage": {p: c for p in OCI_PATHS}, "effective_config": {}, "observed_raw": {}, "state": {}}
    cb = resp.get("cidrBlocks")
    if isinstance(cb, list) and cb and all(isinstance(x, str) for x in cb):
        cov["/cidrBlocks"], eff["cidrBlocks"] = "observed", cb
    else:
        cov["/cidrBlocks"] = "unknown"
        if "cidrBlocks" in resp:
            raw["/cidrBlocks"] = cb                      # kept as seen: [] or the malformed value
    dl = resp.get("dnsLabel")
    if isinstance(dl, str):
        cov["/dnsLabel"], eff["dnsLabel"] = "observed", dl
    else:
        cov["/dnsLabel"] = "absent"
    ft = resp.get("freeformTags")
    if isinstance(ft, dict):
        cov["/freeformTags"], eff["freeformTags"] = "observed", ft
    else:
        cov["/freeformTags"] = "unknown"
        if "freeformTags" in resp:
            raw["/freeformTags"] = ft
    v6 = resp.get("ipv6CidrBlocks")
    if isinstance(v6, list):
        cov["/isIpv6Enabled"], eff["isIpv6Enabled"] = "observed", bool(v6)     # derived; a partial read never fabricates a value
    else:
        cov["/isIpv6Enabled"] = "unobserved"
    for k in ("id", "lifecycleState", "ipv6CidrBlocks"):
        if k in resp:
            state[k] = resp[k]
    return {"coverage": cov, "effective_config": eff, "observed_raw": raw, "state": state}


# --- stage 4: the registry binding (reference): EVERYTHING seen -----------------------------------------------------------
def declared_tag_keys(cfg):
    return [t["key"] for t in cfg.get("tags", [])]


def tag_path(key):
    return "/tags/{key=%s}/value" % key


def stage4(obs3, cfg):
    eff, cov3 = obs3["effective_config"], obs3["coverage"]
    config, cov = {}, {}
    if "cidrBlocks" in eff:
        config["cidr_block"] = eff["cidrBlocks"][0]
    cov["/cidr_block"] = cov3["/cidrBlocks"]
    if "dnsLabel" in eff:
        config["dns_label"] = eff["dnsLabel"]
    cov["/dns_label"] = cov3["/dnsLabel"]
    if "isIpv6Enabled" in eff:
        config["ipv6_enabled"] = eff["isIpv6Enabled"]
    cov["/ipv6_enabled"] = cov3["/isIpv6Enabled"]
    observed_keys = []
    if "freeformTags" in eff:
        config["tags"] = [{"key": k, "value": v} for k, v in sorted(eff["freeformTags"].items())]
        observed_keys = sorted(eff["freeformTags"])
    for k in observed_keys:
        cov[tag_path(k)] = "observed"
    for k in declared_tag_keys(cfg):          # a declared key OCI does not have: absent if the tags were read, else the tags' coverage
        if k not in observed_keys:
            cov[tag_path(k)] = "absent" if cov3["/freeformTags"] == "observed" else cov3["/freeformTags"]
    state = {}
    if "lifecycleState" in obs3["state"]:
        state["lifecycle_state"] = LIFECYCLE.get(obs3["state"]["lifecycleState"], LIFECYCLE_OTHER)
    if "ipv6CidrBlocks" in obs3["state"]:
        state["ipv6_cidr_blocks"] = obs3["state"]["ipv6CidrBlocks"]
    return {"config": config, "coverage": dict(sorted(cov.items())), "state": state}


# --- stage 4b: the plan and the scope, derived from the intent ------------------------------------------------------------
def derive_plan(it):
    cfg, mgmt = it["config"], it["management"]
    scalars = [{"compare": "exact", "path": "/" + k} for k in SCALARS if k in cfg]
    collections = []
    if cfg.get("tags") or mgmt["tags_scope"] == "full-set":
        collections.append({"elements": [{"compare": "exact", "path": "value"}], "keys": ["key"], "path": "/tags", "topology": "map"})
    return {"collections": collections, "scalars": scalars}


def managed_tag_keys(it, obs4):
    declared = declared_tag_keys(it["config"])
    if it["management"]["tags_scope"] == "full-set":
        seen = [p[len("/tags/{key="):-len("}/value")] for p in obs4["coverage"] if p.startswith("/tags/{key=")]
        return sorted(set(declared) | set(seen))
    return sorted(declared)


def planned_paths(it, obs4):
    plan = derive_plan(it)
    paths = [s["path"] for s in plan["scalars"]]
    if plan["collections"]:
        paths += [tag_path(k) for k in managed_tag_keys(it, obs4)]
    return plan, paths


def scope_of(it, obs4):
    _, managed = planned_paths(it, obs4)
    unmanaged = []
    for p, c in obs4["coverage"].items():
        if c != "observed" or p in managed:
            continue
        if p.startswith("/tags/{key="):
            unmanaged.append(p)
        elif p[1:] in obs4["config"]:
            unmanaged.append(p)
    return {"managed_paths": sorted(managed), "tags_scope": it["management"]["tags_scope"], "unmanaged_observed_paths": sorted(unmanaged)}


def engine_input(it, obs4):
    """What the engine is given: the observed list projected to the managed tag keys, the coverage of exactly the planned paths."""
    plan, paths = planned_paths(it, obs4)
    keep = set(managed_tag_keys(it, obs4)) if plan["collections"] else set()
    observed = {k: v for k, v in obs4["config"].items() if k != "tags"}
    if "tags" in obs4["config"] and plan["collections"]:
        observed["tags"] = [t for t in obs4["config"]["tags"] if t["key"] in keep]
    observation = [{"coverage": obs4["coverage"][p], "path": p} for p in paths]
    return {"intent": it["config"], "observation": observation, "observed": observed, "plan": plan}


# --- stage 5: the verdict (the engine semantics) --------------------------------------------------------------------------
def kind(v):
    return "null" if v is None else "bool" if isinstance(v, bool) else "number" if isinstance(v, (int, float)) else \
        "string" if isinstance(v, str) else "array" if isinstance(v, list) else "object"


def lookup(config, path):
    if path.startswith("/tags/{key="):
        key = path[len("/tags/{key="):-len("}/value")]
        for t in config.get("tags", []):
            if t["key"] == key:
                return True, t["value"]
        return False, None
    name = path[1:]
    return (name in config), config.get(name)


def classify(coverage, present, matched, comparable=True):
    if coverage == "observed":
        if not comparable:
            return "NOT_COMPARABLE"          # compare() of two values of different kinds (engine: never a false DRIFT)
        return "CONFORMANT" if matched else "DRIFT"
    if coverage == "absent":
        return "DRIFT" if present else "OBSERVED_ABSENT"
    return "UNOBSERVED"           # unobserved and unknown alike


def aggregate(fields):
    vs = set(fields.values())
    if vs & {"DRIFT", "NOT_COMPARABLE"}:
        return "DRIFT"
    return "INCOMPLETE" if "UNOBSERVED" in vs else "CONFORMANT"


def stage5(ein):
    cov = {o["path"]: o["coverage"] for o in ein["observation"]}
    paths = [s["path"] for s in ein["plan"]["scalars"]]
    if ein["plan"]["collections"]:
        keys = set(declared_tag_keys(ein["intent"])) | {t["key"] for t in ein["observed"].get("tags", [])}   # the engine's union
        paths += [tag_path(k) for k in sorted(keys)]
    fields = {}
    for p in paths:
        present, iv = lookup(ein["intent"], p)
        have, ov = lookup(ein["observed"], p)
        comparable = kind(iv if present else None) == kind(ov if have else None)
        fields[p] = classify(cov.get(p, "unobserved"), present, have and iv == ov, comparable)   # an unlisted path is Unobserved
    return {"fields": dict(sorted(fields.items())), "object": aggregate(fields)}


def stage6(verdict, scope):
    f = verdict["fields"]
    return {"conformance_claimed": verdict["object"] == "CONFORMANT",
            "conformance_scope": "declared",
            "drift_paths": sorted(p for p, v in f.items() if v in ("DRIFT", "NOT_COMPARABLE")),
            "object": verdict["object"],
            "scope": {"managed_paths": scope["managed_paths"], "tags_scope": scope["tags_scope"],
                      "unmanaged_observed_paths": scope["unmanaged_observed_paths"]},
            "unobserved_paths": sorted(p for p, v in f.items() if v == "UNOBSERVED")}


def dump(doc):
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def build():
    files = {"lifecycle-map.json": dump({"map": LIFECYCLE, "other": LIFECYCLE_OTHER}), "not-plannable.json": dump(NOT_PLANNABLE),
             "cases.json": dump({k: v[0] for k, v in sorted(CASES.items())})}
    for cid, (_, it, resp, err) in CASES.items():
        base = "cases/%s/" % cid
        files[base + "intent.registry.json"] = dump(it)
        files[base + ("oci/response.json" if resp is not None else "oci/error.json")] = dump(resp if resp is not None else err)
        o3 = stage3(resp, err)
        o4 = stage4(o3, it["config"])
        plan = derive_plan(it)
        scope = scope_of(it, o4)
        ein = engine_input(it, o4)
        v = stage5(ein)
        files[base + "expected/observed.oci.json"] = dump(o3)
        files[base + "expected/observed.registry.json"] = dump(o4)
        files[base + "expected/plan.json"] = dump(plan)
        files[base + "expected/scope.json"] = dump(scope)
        files[base + "expected/engine-input.json"] = dump(ein)
        files[base + "expected/verdict.fields.json"] = dump(v)
        files[base + "expected/evidence.claims.json"] = dump(stage6(v, scope))
    files["MANIFEST.sha256"] = "".join("%s  %s\n" % (hashlib.sha256(files[k].encode()).hexdigest(), k) for k in sorted(files))
    return files


def main(argv):
    files = build()
    if "--check" in argv:
        bad = []
        for k, t in files.items():
            path = os.path.join(HERE, k)
            if not os.path.exists(path):
                bad.append(k)
                continue
            with open(path, encoding="utf-8") as fh:
                if fh.read() != t:
                    bad.append(k)
        on_disk = set()
        for root, _, names in os.walk(HERE):
            for n in names:
                rel = os.path.relpath(os.path.join(root, n), HERE)
                if rel not in ("generate.py", "README.md") and "__pycache__" not in rel:
                    on_disk.add(rel)
        extra = sorted(on_disk - set(files))
        if bad or extra:
            print("differs: %s; not generated: %s" % (bad, extra))
            return 1
        print("fixture ok: %d files" % len(files))
        return 0
    for k, t in files.items():
        path = os.path.join(HERE, k)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(t)
    print("wrote %d files" % len(files))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
