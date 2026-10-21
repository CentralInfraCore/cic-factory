#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-SA-4.0
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""Generates fixtures/vcn-v1: the common OCI VCN fixture of the Intent -> Observed -> Conformance -> Evidence slice.

    generate.py            write the files next to this script
    generate.py --check    fail if the files on disk differ from what is generated

The raw inputs are written down here by hand (the intent and the OCI responses of each case). Everything under `expected/` is
derived by the small reference rules below, which restate, in one place, what the four repositories must agree on:

  stage 1  intent.registry.json          what is wanted, in the names of the registry schema (NetworkSpaceOracleCloud)
  stage 2  oci/response.json | oci/error.json   what OCI answered to GetVcn (or why it did not)
  stage 3  expected/observed.oci.json     the oracle module's normalization: effective config, state, coverage, in OCI names
  stage 4  expected/observed.registry.json  the same in registry names (the binding of the registry), with coverage per compared path
  stage 5  expected/verdict.fields.json   the conformance verdict per path and for the object (the engine semantics)
  stage 6  expected/evidence.claims.json  what an evidence record may claim about this case

The reference rules are NOT an implementation to be reused: each repository implements its own stage and its tests compare the
result with these files. The semantics of stage 5 are those of cic-primitive-engine `classify_field` and `aggregate`
(origin/main): coverage Absent + intent present = DRIFT, Absent + intent absent = OBSERVED_ABSENT, Unobserved or Unknown =
UNOBSERVED, never CONFORMANT; the object is DRIFT if any field is DRIFT or NOT_COMPARABLE, else INCOMPLETE if any field is
UNOBSERVED, else CONFORMANT.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# --- the plan: what is compared (case independent) ------------------------------------------------------------------------
PLAN = {
    "scalars": [
        {"path": "/cidr_block", "compare": "exact"},
        {"path": "/dns_label", "compare": "exact"},
        {"path": "/ipv6_enabled", "compare": "exact"},
    ],
    "collections": [
        {"path": "/tags", "topology": "map", "keys": ["key"], "elements": [{"path": "value", "compare": "exact"}]},
    ],
}
# secondary_cidr_blocks, display_name, compartment_id and the state fields are NOT in the plan: the verdict says nothing about them.
NOT_PLANNED = ["/secondary_cidr_blocks", "/display_name", "/compartment_id", "/lifecycle_state", "/ipv6_cidr_blocks"]

LIFECYCLE = {  # OCI lifecycleState -> registry lifecycle_state enum [pending, available, deleting, deleted, unknown]
    "PROVISIONING": "pending", "AVAILABLE": "available", "UPDATING": "unknown", "TERMINATING": "deleting", "TERMINATED": "deleted",
}
LIFECYCLE_OTHER = "unknown"

BASE_INTENT = {"cidr_block": "10.0.0.0/16", "dns_label": "prod", "ipv6_enabled": False,
               "tags": [{"key": "env", "value": "prod"}, {"key": "owner", "value": "net"}]}
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


# case id -> (description, intent, response | None, error | None)
CASES = {
    "conformant": ("everything wanted is there", BASE_INTENT, BASE_RESPONSE, None),
    "drift": ("the dns label and one tag value differ", BASE_INTENT,
              with_(BASE_RESPONSE, dnsLabel="staging", freeformTags={"env": "dev", "owner": "net"}), None),
    "field-absent": ("a wanted dns label that OCI does not report (not set): DRIFT, not 'unknown'", BASE_INTENT,
                     without(BASE_RESPONSE, "dnsLabel"), None),
    "desired-absent": ("the dns label is not managed (not in the intent) and OCI has none: OBSERVED_ABSENT, the object conforms",
                       without(BASE_INTENT, "dns_label"), without(BASE_RESPONSE, "dnsLabel"), None),
    "desired-absent-observed-present": ("OPEN QUESTION: the dns label is not in the intent but is in the plan and OCI has one; the engine says NOT_COMPARABLE (object DRIFT), the module's 'absent = unmanaged' would say fine",
                                        without(BASE_INTENT, "dns_label"), BASE_RESPONSE, None),
    "partial-read": ("the answer has no ipv6CidrBlocks at all: ipv6_enabled was not observed, it is not 'false'", BASE_INTENT,
                     without(BASE_RESPONSE, "ipv6CidrBlocks"), None),
    "malformed-cidr": ("cidrBlocks is not a list: it was read but cannot be trusted: unknown", BASE_INTENT,
                       with_(BASE_RESPONSE, cidrBlocks="10.0.0.0/16"), None),
    "not-found": ("HTTP 404 NotAuthorizedOrNotFound: OCI does not tell 'deleted' from 'not allowed', so absence is NOT authoritative",
                  BASE_INTENT, None, {"kind": "http", "status": 404, "code": "NotAuthorizedOrNotFound"}),
    "transport-error": ("no answer (timeout): nothing was observed", BASE_INTENT, None, {"kind": "transport", "message": "timeout"}),
}

OCI_PATHS = ["/cidrBlocks", "/dnsLabel", "/freeformTags", "/isIpv6Enabled"]


# --- stage 3: the module's normalization (reference) ----------------------------------------------------------------------
def stage3(resp, err):
    cov, eff, state = {}, {}, {}
    if resp is None:
        c = "unknown" if err["kind"] == "http" else "unobserved"   # 404 cannot be told from 403; a timeout simply was not an answer
        return {"effective_config": {}, "state": {}, "coverage": {p: c for p in OCI_PATHS}}
    cb = resp.get("cidrBlocks")
    if isinstance(cb, list) and cb and all(isinstance(x, str) for x in cb):
        cov["/cidrBlocks"], eff["cidrBlocks"] = "observed", cb
    else:
        cov["/cidrBlocks"] = "unknown"
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
    v6 = resp.get("ipv6CidrBlocks")
    if isinstance(v6, list):
        cov["/isIpv6Enabled"], eff["isIpv6Enabled"] = "observed", bool(v6)     # derived; a partial read never fabricates a value
    else:
        cov["/isIpv6Enabled"] = "unobserved"
    for k in ("id", "lifecycleState", "ipv6CidrBlocks"):
        if k in resp:
            state[k] = resp[k]
    return {"effective_config": eff, "state": state, "coverage": cov}


# --- stage 4: the registry binding (reference) ----------------------------------------------------------------------------
def stage4(obs3, intent):
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
    if "freeformTags" in eff:
        config["tags"] = [{"key": k, "value": v} for k, v in sorted(eff["freeformTags"].items())]
    for t in intent.get("tags", []):   # the elements the plan can ask about: the keys of the intent
        cov["/tags/{key=%s}/value" % t["key"]] = cov3["/freeformTags"]
    state = {}
    if "lifecycleState" in obs3["state"]:
        state["lifecycle_state"] = LIFECYCLE.get(obs3["state"]["lifecycleState"], LIFECYCLE_OTHER)
    if "ipv6CidrBlocks" in obs3["state"]:
        state["ipv6_cidr_blocks"] = obs3["state"]["ipv6CidrBlocks"]
    return {"config": config, "state": state, "coverage": cov}


# --- stage 5: the verdict (the engine semantics) --------------------------------------------------------------------------
def intent_value(intent, path):
    if path.startswith("/tags/{key="):
        key = path[len("/tags/{key="):-len("}/value")]
        for t in intent.get("tags", []):
            if t["key"] == key:
                return True, t["value"]
        return False, None
    name = path[1:]
    return (name in intent), intent.get(name)


def observed_value(config, path):
    if path.startswith("/tags/{key="):
        key = path[len("/tags/{key="):-len("}/value")]
        for t in config.get("tags", []):
            if t["key"] == key:
                return True, t["value"]
        return False, None
    name = path[1:]
    return (name in config), config.get(name)


def kind(v):
    return "null" if v is None else "bool" if isinstance(v, bool) else "number" if isinstance(v, (int, float)) else \
        "string" if isinstance(v, str) else "array" if isinstance(v, list) else "object"


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


def stage5(obs4, intent):
    fields = {}
    paths = [s["path"] for s in PLAN["scalars"]] + ["/tags/{key=%s}/value" % t["key"] for t in intent.get("tags", [])]
    for p in paths:
        present, iv = intent_value(intent, p)
        cov = obs4["coverage"][p]
        have, ov = observed_value(obs4["config"], p)
        # the engine compares even when the intent declares nothing for a planned path (its value is then null): an observed value
        # of another kind is NOT_COMPARABLE, not 'unmanaged'. See the README, 'the open question'.
        comparable = kind(iv if present else None) == kind(ov if have else None)
        fields[p] = classify(cov, present, have and iv == ov, comparable)
    return {"object": aggregate(fields), "fields": dict(sorted(fields.items()))}


def stage6(verdict):
    f = verdict["fields"]
    return {"conformance_claimed": verdict["object"] == "CONFORMANT",
            "drift_paths": sorted(p for p, v in f.items() if v in ("DRIFT", "NOT_COMPARABLE")),
            "unobserved_paths": sorted(p for p, v in f.items() if v == "UNOBSERVED"),
            "object": verdict["object"]}


def dump(doc):
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def build():
    files = {"plan.json": dump(PLAN), "lifecycle-map.json": dump({"map": LIFECYCLE, "other": LIFECYCLE_OTHER}),
             "not-planned.json": dump(NOT_PLANNED), "cases.json": dump({k: v[0] for k, v in sorted(CASES.items())})}
    for cid, (_, intent, resp, err) in CASES.items():
        base = "cases/%s/" % cid
        files[base + "intent.registry.json"] = dump(intent)
        files[base + ("oci/response.json" if resp is not None else "oci/error.json")] = dump(resp if resp is not None else err)
        o3 = stage3(resp, err)
        o4 = stage4(o3, intent)
        v = stage5(o4, intent)
        files[base + "expected/observed.oci.json"] = dump(o3)
        files[base + "expected/observed.registry.json"] = dump(o4)
        files[base + "expected/verdict.fields.json"] = dump(v)
        files[base + "expected/evidence.claims.json"] = dump(stage6(v))
    manifest = "".join("%s  %s\n" % (hashlib.sha256(files[k].encode()).hexdigest(), k) for k in sorted(files))
    files["MANIFEST.sha256"] = manifest
    return files


def main(argv):
    files = build()
    if "--check" in argv:
        bad = [k for k, t in files.items() if not os.path.exists(os.path.join(HERE, k)) or open(os.path.join(HERE, k), encoding="utf-8").read() != t]
        on_disk = set()
        for root, _, names in os.walk(HERE):
            for n in names:
                rel = os.path.relpath(os.path.join(root, n), HERE)
                if rel not in ("generate.py", "README.md") and not rel.endswith(".pyc") and "__pycache__" not in rel:
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
