#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Harness reader for the phase 0 positive-control run (pk-canary-channels).

  read-pk.py DIR --expect-repo OWNER/REPO --expect-run-id ID --expect-attempt N \
             --expect-head-sha SHA --expect-sha256 HEX   evaluate fetched evidence
  read-pk.py --write-manifest DIR RUN_JSON OWNER/REPO HEAD ATTEMPT PREV_JSON ARTIFACTS_JSON ZIP_SHA256
                                                             (used by fetch-pk.sh) validate the run
                                                             and bind the fetched files to it
  read-pk.py --check-run RUN_JSON OWNER/REPO HEAD ATTEMPT PREV_JSON
                                                             (used by fetch-pk.sh) refuse a wrong run
  read-pk.py --pick-artifact RUN_JSON ARTIFACTS_JSON HEAD    (used by fetch-pk.sh) print the id of THE
                                                             artifact created inside the attempt window
  read-pk.py --attach-summary DIR FILE RUN_ID ATTEMPT        bind an owner-copied job summary to the
                                                             run AND the attempt the owner names
  read-pk.py --selftest                                      the reader must accept a good
                                                             fixture and reject every planted
                                                             defect (it can fail)

DIR is produced by fetch-pk.sh (a NEW directory per run) and holds: manifest.json
(run id, attempt, head SHA, event, branch, conclusion, SHA-256 of every fetched file),
log.txt, annotations.json, artifact/pk-artifact.txt, and optionally summary.txt
(the job summary is not read through the API; it exists only if the owner copied it
and bound it with --attach-summary; absent = NOT-READ, never a pass).

Per-check result: MET / NOT-MET / NOT-READ. These describe the MEASURING INSTRUMENT
only (positive controls); they are not verdicts on the platform property and not
measurement results of H1/H2.

PK MET needs ALL of: manifest bound to the owner-chosen repository, run id and ATTEMPT
(--expect-repo, --expect-run-id, --expect-attempt: independent inputs; one head SHA can have
several runs and one run id several attempts: a web approval of a held run makes attempt 2)
and to the approved head SHA (--expect-head-sha),
the expected secret digest (--expect-sha256) compared, every channel read and
free of any other CANARY-212- value. A missing expectation is INCOMPLETE, never MET.
"""
import hashlib
import json
import os
import re
import sys
import tempfile

TOKEN = "CANARY-212-PK-UNMASKED-00000000000000000000"
EXPECTED_LEN = len("CANARY-212-") + 32
EXPECTED_NAMES = ["CANARY_UNRESTRICTED", "github_token"]
WORKFLOW_PATH = ".github/workflows/pk-canary-channels.yml"
OTHER_CANARY = re.compile(r"CANARY-212-[0-9A-Za-z-]*")
# Only two attempt histories are accepted: attempt 1 with no earlier attempt, or attempt 2
# whose attempt 1 was held by the platform (completed / action_required, zero jobs).
HELD_ATTEMPT_1 = {"run_attempt": 1, "status": "completed",
                  "conclusion": "action_required", "jobs": 0}
FETCHED = ["log.txt", "annotations.json", "artifact/pk-artifact.txt"]
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def sha256_file(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def strings_of(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from strings_of(k)
            yield from strings_of(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings_of(v)


ISO = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")


def window_of(run):
    w = {"start": run.get("run_started_at"), "end": run.get("updated_at")}
    ok = all(isinstance(v, str) and ISO.match(v) for v in w.values()) and w["start"] <= w["end"]
    return w, ok


def pick_artifact(run, artifacts, head):
    """The artifact of THIS attempt: right name, run, head, not expired, created inside the
    attempt window. Returns (record, error-or-None); exactly one must qualify."""
    w, ok = window_of(run)
    if not ok:
        return None, "attempt window unreadable"
    lst = artifacts.get("artifacts") if isinstance(artifacts, dict) else None
    if not isinstance(lst, list):
        return None, "artifact list unreadable"
    hit = []
    for a in lst:
        wr = a.get("workflow_run") or {}
        ca = a.get("created_at")
        if (a.get("name") == "pk-channels" and wr.get("id") == run.get("id")
                and wr.get("head_sha") == head and a.get("expired") is False
                and isinstance(ca, str) and ISO.match(ca) and w["start"] <= ca <= w["end"]
                and isinstance(a.get("id"), int) and not isinstance(a.get("id"), bool)):
            hit.append(a)
    if len(hit) != 1:
        return None, "%d artifact(s) qualify for this attempt (need exactly 1)" % len(hit)
    a = hit[0]
    return {"id": a["id"], "name": a["name"], "workflow_run_id": run["id"], "head_sha": head,
            "created_at": a["created_at"], "size_in_bytes": a.get("size_in_bytes")}, None


def artifact_ok(m):
    w = m.get("attempt_window")
    a = m.get("artifact")
    if not (isinstance(w, dict) and isinstance(w.get("start"), str) and isinstance(w.get("end"), str)
            and ISO.match(w["start"]) and ISO.match(w["end"]) and w["start"] <= w["end"]):
        return "attempt window missing or unreadable"
    if not isinstance(a, dict):
        return "artifact record missing"
    if not isinstance(a.get("id"), int) or isinstance(a.get("id"), bool) or a["id"] <= 0:
        return "artifact id"
    if a.get("name") != "pk-channels":
        return "artifact name"
    if a.get("workflow_run_id") != m.get("run_id") or a.get("head_sha") != m.get("head_sha"):
        return "artifact run or head differs from the manifest"
    ca = a.get("created_at")
    if not (isinstance(ca, str) and ISO.match(ca) and w["start"] <= ca <= w["end"]):
        return "artifact created outside the attempt window"
    if not (isinstance(a.get("zip_sha256"), str) and re.match(r"^[0-9a-f]{64}$", a["zip_sha256"])):
        return "artifact zip digest"
    return None


def previous_ok(attempt, prev):
    """Returns an error text or None."""
    if attempt == 1:
        return None if prev == [] else "attempt 1 must have no earlier attempt, got %r" % (prev,)
    if attempt == 2:
        return None if prev == [HELD_ATTEMPT_1] else (
            "attempt 2 needs attempt 1 completed/action_required with 0 jobs, got %r" % (prev,))
    return "attempt %r is not accepted (only 1, or 2 after a held attempt 1)" % (attempt,)


def check_manifest(d, expect_head, expect_repo=None, expect_run_id=None, expect_attempt=None):
    """Returns (rows, manifest-or-None)."""
    rows = []
    mtxt = read(os.path.join(d, "manifest.json"))
    if mtxt is None:
        rows.append(("run binding", "NOT-MET", "manifest.json missing: the evidence is not bound to a run"))
        return rows, None
    try:
        m = json.loads(mtxt)
        assert isinstance(m, dict)
    except (ValueError, AssertionError):
        rows.append(("run binding", "NOT-MET", "manifest.json is not a JSON object"))
        return rows, None
    problems = []
    want = {"workflow_path": WORKFLOW_PATH, "event": "workflow_dispatch",
            "status": "completed", "conclusion": "success", "head_branch": "main"}
    for k, v in want.items():
        if m.get(k) != v:
            problems.append("%s=%r" % (k, m.get(k)))
    if not isinstance(m.get("run_id"), int) or isinstance(m.get("run_id"), bool):
        problems.append("run_id")
    hs = m.get("head_sha")
    if not isinstance(hs, str) or not SHA_RE.match(hs):
        problems.append("head_sha")
    files = m.get("files")
    if not isinstance(files, dict) or sorted(files) != sorted(FETCHED):
        problems.append("files set")
        files = {}
    for rel, dig in files.items():
        if sha256_file(os.path.join(d, rel)) != dig:
            problems.append("file %s differs from the manifest digest" % rel)
    known = set(FETCHED) | {"manifest.json", "summary.txt"}
    present = set()
    for root, _, fs in os.walk(d):
        for f in fs:
            present.add(os.path.relpath(os.path.join(root, f), d))
    extra = sorted(present - known)
    if extra:
        problems.append("unlisted file(s) %s" % extra)
    rows.append(("run binding", "NOT-MET" if problems else "MET",
                 "; ".join(problems) if problems else
                 "run %s attempt %s, workflow_dispatch, completed/success, branch main" % (m.get("run_id"), m.get("run_attempt"))))
    if expect_repo is None:
        rows.append(("repository", "NOT-READ", "--expect-repo not given"))
    else:
        rows.append(("repository", "MET" if m.get("repository") == expect_repo else "NOT-MET",
                     "manifest repository %r" % (m.get("repository"),)))
    if expect_run_id is None:
        rows.append(("run id", "NOT-READ", "--expect-run-id not given"))
    elif not re.match(r"^[0-9]+$", str(expect_run_id)):
        rows.append(("run id", "NOT-MET", "expected run id is not numeric"))
    else:
        rid = m.get("run_id")
        rows.append(("run id", "MET" if isinstance(rid, int) and not isinstance(rid, bool)
                     and rid == int(expect_run_id) else "NOT-MET",
                     "manifest run id %r" % (rid,)))
    att = m.get("run_attempt")
    if expect_attempt is None:
        rows.append(("attempt", "NOT-READ", "--expect-attempt not given"))
    elif not re.match(r"^[0-9]+$", str(expect_attempt)):
        rows.append(("attempt", "NOT-MET", "expected attempt is not numeric"))
    else:
        rows.append(("attempt", "MET" if isinstance(att, int) and not isinstance(att, bool)
                     and att == int(expect_attempt) else "NOT-MET",
                     "manifest attempt %r" % (att,)))
    perr = previous_ok(att, m.get("previous_attempts")) if isinstance(att, int) and not isinstance(att, bool) else "attempt missing"
    rows.append(("earlier attempts", "MET" if perr is None else "NOT-MET",
                 perr or "history acceptable for attempt %r" % (att,)))
    aerr = artifact_ok(m)
    rows.append(("artifact origin", "MET" if aerr is None else "NOT-MET",
                 aerr or "artifact %s created inside the attempt window" % m["artifact"]["id"]))
    if expect_head is None:
        rows.append(("approved head SHA", "NOT-READ", "--expect-head-sha not given"))
    elif not SHA_RE.match(expect_head):
        rows.append(("approved head SHA", "NOT-MET", "expected value is not a 40-hex SHA"))
    else:
        rows.append(("approved head SHA", "MET" if m.get("head_sha") == expect_head else "NOT-MET",
                     "run head %s" % m.get("head_sha")))
    return rows, m


def evaluate(d, expect_head=None, expect_sha=None, expect_repo=None, expect_run_id=None,
             expect_attempt=None):
    res = []  # (check, result, note)
    mrows, man = check_manifest(d, expect_head, expect_repo, expect_run_id, expect_attempt)
    res += mrows
    log = read(os.path.join(d, "log.txt"))
    ann_txt = read(os.path.join(d, "annotations.json"))
    art = read(os.path.join(d, "artifact", "pk-artifact.txt"))
    summ = read(os.path.join(d, "summary.txt"))

    # the summary is evidence only when the owner bound it to THIS run
    if summ is not None:
        s = (man or {}).get("summary")
        ok = (isinstance(s, dict) and man is not None
              and s.get("run_id") == man.get("run_id")
              and isinstance(s.get("attempt"), int) and not isinstance(s.get("attempt"), bool)
              and s.get("attempt") == man.get("run_attempt")
              and (expect_attempt is None or str(s.get("attempt")) == str(expect_attempt))
              and s.get("sha256") == sha256_file(os.path.join(d, "summary.txt")))
        if not ok:
            res.append(("summary binding", "NOT-MET",
                        "summary.txt is not attached to this run AND attempt in the manifest"))
            summ = None
        else:
            res.append(("summary binding", "MET", "owner-attested copy for run %s attempt %s" % (man["run_id"], man["run_attempt"])))

    ann_strings = None
    ann_ok = False
    if ann_txt is not None:
        try:
            ann = json.loads(ann_txt)
            if isinstance(ann, list) and all(isinstance(a, dict) for a in ann):
                ann_ok = True
                ann_strings = list(strings_of(ann))
        except ValueError:
            pass

    # (U) the unmasked, known canary must be seen on each channel
    if log is None:
        res.append(("U log", "NOT-READ", "log.txt missing"))
    else:
        out_lines = [l for l in log.splitlines()
                     if l.rstrip().endswith(TOKEN)
                     and "PK_UNMASKED" not in l and "##[notice]" not in l]
        res.append(("U log", "MET" if out_lines else "NOT-MET",
                    "%d output line(s)" % len(out_lines)))
    if art is None:
        res.append(("U artifact", "NOT-READ", "artifact missing"))
    else:
        res.append(("U artifact", "MET" if art.strip() == TOKEN else "NOT-MET", ""))
    if ann_txt is None:
        res.append(("U annotation", "NOT-READ", "annotations.json missing"))
    elif not ann_ok:
        res.append(("U annotation", "NOT-MET", "annotations.json is not a JSON list of objects"))
    else:
        hit = any(isinstance(a.get("message"), str) and a["message"] == TOKEN for a in ann)
        res.append(("U annotation", "MET" if hit else "NOT-MET", "message field compared"))
    if summ is None:
        res.append(("U summary", "NOT-READ", "no run-bound summary (not read in this package)"))
    else:
        res.append(("U summary", "MET" if TOKEN in summ else "NOT-MET", ""))

    # (U) the unrestricted repository secret is readable inside a job
    if log is None:
        res.append(("U secret readable", "NOT-READ", "log.txt missing"))
        res.append(("U secret digest", "NOT-READ", "log.txt missing"))
    else:
        m = re.search(r"PK-U length=(\d+) sha256=([0-9a-f]{64})\b", log)
        if not m:
            res.append(("U secret readable", "NOT-MET", "no PK-U line"))
            res.append(("U secret digest", "NOT-MET", "no PK-U line"))
        else:
            res.append(("U secret readable",
                        "MET" if int(m.group(1)) == EXPECTED_LEN else "NOT-MET",
                        "length %s" % m.group(1)))
            if expect_sha is None:
                res.append(("U secret digest", "NOT-READ", "--expect-sha256 not given"))
            elif not re.match(r"^[0-9a-f]{64}$", expect_sha):
                res.append(("U secret digest", "NOT-MET", "expected value is not a 64-hex digest"))
            else:
                res.append(("U secret digest",
                            "MET" if m.group(2) == expect_sha else "NOT-MET",
                            "compared with the owner's expected digest"))

    # (J) the registered secret is masked; no other canary value on ANY channel
    if log is None:
        res.append(("J masked", "NOT-READ", "log.txt missing"))
        res.append(("J secret names", "NOT-READ", "log.txt missing"))
    else:
        masked = any(re.search(r"masked-test: \*\*\*\s*$", l) for l in log.splitlines())
        res.append(("J masked", "MET" if masked else "NOT-MET", ""))
        n = re.search(r"PK-J visible-secret-names=(\[.*?\])", log)
        if not n:
            res.append(("J secret names", "NOT-MET", "no PK-J line"))
        else:
            try:
                names = json.loads(n.group(1))
            except ValueError:
                names = None
            res.append(("J secret names", "MET" if names == EXPECTED_NAMES else "NOT-MET",
                        "got %s" % (names,)))

    def other(label, text):
        if text is None:
            res.append(("J no other canary " + label, "NOT-READ", "channel not read"))
            return
        found = OTHER_CANARY.findall(text.replace(TOKEN, ""))
        res.append(("J no other canary " + label, "MET" if not found else "NOT-MET",
                    "%d other occurrence(s)" % len(found)))

    other("log", log)
    if ann_txt is None:
        other("annotation", None)
    elif not ann_ok:
        res.append(("J no other canary annotation", "NOT-MET", "annotations.json not parseable"))
    else:
        other("annotation", "\n".join(ann_strings))
    other("artifact", art)
    other("summary", summ)
    return res


def overall(res):
    r = [x[1] for x in res]
    if "NOT-MET" in r:
        return "PK NOT MET"
    if "NOT-READ" in r:
        return "PK INCOMPLETE (not read)"
    return "PK MET"


def report(res):
    for c, r, n in res:
        print("%-30s %-9s %s" % (c, r, n))
    print("OVERALL: %s" % overall(res))


def check_run(run_json, repo, head, attempt, prev_json):
    """Returns (run, got, error-or-None)."""
    try:
        run = json.loads(read(run_json))
    except (TypeError, ValueError):
        return None, None, "run JSON unreadable"
    if not SHA_RE.match(head or ""):
        return None, None, "approved head is not a 40-hex SHA"
    if not re.match(r"^[0-9]+$", str(attempt)):
        return None, None, "attempt is not numeric"
    attempt = int(attempt)
    try:
        prev = json.loads(read(prev_json))
    except (TypeError, ValueError):
        return None, None, "earlier-attempts JSON unreadable"
    perr = previous_ok(attempt, prev)
    if perr:
        return None, None, perr
    got = {"workflow_path": run.get("path"), "event": run.get("event"),
           "status": run.get("status"), "conclusion": run.get("conclusion"),
           "head_branch": run.get("head_branch"), "run_attempt": run.get("run_attempt"),
           "head_sha": run.get("head_sha")}
    want = {"workflow_path": WORKFLOW_PATH, "event": "workflow_dispatch",
            "status": "completed", "conclusion": "success", "head_branch": "main",
            "run_attempt": attempt, "head_sha": head}
    bad = ["%s=%r (want %r)" % (k, got[k], v) for k, v in want.items() if got[k] != v]
    if (run.get("repository") or {}).get("full_name") != repo:
        bad.append("repository=%r (want %r)" % ((run.get("repository") or {}).get("full_name"), repo))
    if (run.get("head_repository") or {}).get("full_name") != repo:
        bad.append("head_repository differs")
    if not isinstance(run.get("id"), int) or isinstance(run.get("id"), bool):
        bad.append("run id")
    if bad:
        return None, None, "the run is not the approved one: " + "; ".join(bad)
    got["previous_attempts"] = prev
    return run, got, None


def check_run_main(run_json, repo, head, attempt, prev_json):
    _, _, err = check_run(run_json, repo, head, attempt, prev_json)
    if err:
        print("refusing: " + err, file=sys.stderr)
        return 1
    print("run is the approved one")
    return 0


def pick_artifact_main(run_json, artifacts_json, head):
    try:
        run = json.loads(read(run_json))
        arts = json.loads(read(artifacts_json))
    except (TypeError, ValueError):
        print("refusing: run or artifact JSON unreadable", file=sys.stderr)
        return 1
    rec, err = pick_artifact(run, arts, head)
    if err:
        print("refusing: " + err, file=sys.stderr)
        return 1
    print(rec["id"])
    return 0


def write_manifest_from_run(d, run_json, repo, head, attempt, prev_json, artifacts_json, zip_sha):
    run, got, err = check_run(run_json, repo, head, attempt, prev_json)
    if err:
        print("refusing: " + err, file=sys.stderr)
        return 1
    try:
        arts = json.loads(read(artifacts_json))
    except (TypeError, ValueError):
        print("refusing: artifact JSON unreadable", file=sys.stderr)
        return 1
    rec, aerr = pick_artifact(run, arts, head)
    if aerr:
        print("refusing: " + aerr, file=sys.stderr)
        return 1
    if not re.match(r"^[0-9a-f]{64}$", zip_sha or ""):
        print("refusing: zip digest malformed", file=sys.stderr)
        return 1
    rec["zip_sha256"] = zip_sha
    got["attempt_window"] = window_of(run)[0]
    got["artifact"] = rec
    m = dict(got, run_id=run["id"], repository=repo,
             files={rel: sha256_file(os.path.join(d, rel)) for rel in FETCHED})
    if any(v is None for v in m["files"].values()):
        print("refusing: a fetched file is missing", file=sys.stderr)
        return 1
    with open(os.path.join(d, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=2, sort_keys=True)
    print("manifest written for run %s (attempt %s, head %s)" % (m["run_id"], m["run_attempt"], head))
    return 0


def attach_summary(d, src, run_id, attempt):
    mp = os.path.join(d, "manifest.json")
    mtxt = read(mp)
    text = read(src)
    if mtxt is None or text is None:
        print("refusing: manifest.json or the summary file is unreadable", file=sys.stderr)
        return 2
    m = json.loads(mtxt)
    if str(m.get("run_attempt")) != str(attempt):
        print("refusing: attempt %s differs from the manifest attempt %s" % (attempt, m.get("run_attempt")), file=sys.stderr)
        return 2
    if str(m.get("run_id")) != str(run_id):
        print("refusing: run id %s differs from the manifest run %s" % (run_id, m.get("run_id")), file=sys.stderr)
        return 2
    if "summary" in m or os.path.exists(os.path.join(d, "summary.txt")):
        print("refusing: a summary is already attached", file=sys.stderr)
        return 2
    dst = os.path.join(d, "summary.txt")
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(text)
    m["summary"] = {"run_id": m["run_id"], "attempt": m["run_attempt"], "sha256": sha256_file(dst),
                    "source": "owner copy from the web UI (attested by the owner, not machine-verified)"}
    with open(mp, "w", encoding="utf-8") as fh:
        json.dump(m, fh, indent=2, sort_keys=True)
    print("attached summary to run %s attempt %s" % (m["run_id"], m["run_attempt"]))
    return 0


HEAD = "a1" * 20
WINDOW = {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T00:01:00Z"}
ARTIFACT = {"id": 777, "name": "pk-channels", "workflow_run_id": 123456, "head_sha": HEAD,
            "created_at": "2026-01-01T00:00:30Z", "size_in_bytes": 200, "zip_sha256": "c" * 64}
REPO = "o/r"
RUN = 123456
SHA = "a" * 64


def write_manifest(d, **over):
    m = {"workflow_path": WORKFLOW_PATH, "event": "workflow_dispatch", "status": "completed",
         "conclusion": "success", "head_branch": "main", "run_attempt": 1,
         "previous_attempts": [], "run_id": 123456, "head_sha": HEAD, "repository": REPO,
         "attempt_window": dict(WINDOW), "artifact": dict(ARTIFACT),
         "files": {rel: sha256_file(os.path.join(d, rel)) for rel in FETCHED}}
    m.update(over)
    json.dump(m, open(os.path.join(d, "manifest.json"), "w"))


def good_fixture(d, sha=SHA):
    os.makedirs(os.path.join(d, "artifact"))
    log = "\n".join([
        "pk-channels\tpk channels\t2026-01-01T00:00:00Z PK_UNMASKED: " + TOKEN,
        "pk-channels\tpk channels\t2026-01-01T00:00:00Z CANARY_UNRESTRICTED: ***",
        "pk-channels\tpk channels\t2026-01-01T00:00:01Z PK-MARK start",
        "pk-channels\tpk channels\t2026-01-01T00:00:01Z " + TOKEN,
        "pk-channels\tpk channels\t2026-01-01T00:00:01Z ##[notice]" + TOKEN,
        "pk-channels\tpk channels\t2026-01-01T00:00:01Z masked-test: ***",
        "pk-channels\tpk channels\t2026-01-01T00:00:01Z PK-U length=%d sha256=%s" % (EXPECTED_LEN, sha),
        "pk-channels\tpk channels\t2026-01-01T00:00:01Z PK-J visible-secret-names=" + json.dumps(EXPECTED_NAMES, separators=(",", ":")),
    ]) + "\n"
    open(os.path.join(d, "log.txt"), "w").write(log)
    open(os.path.join(d, "annotations.json"), "w").write(json.dumps([{"title": "pk", "message": TOKEN}]))
    open(os.path.join(d, "artifact", "pk-artifact.txt"), "w").write(TOKEN + "\n")
    write_manifest(d)
    open(os.path.join(d, "summary.txt"), "w").write(TOKEN + "\n")
    m = json.load(open(os.path.join(d, "manifest.json")))
    m["summary"] = {"run_id": m["run_id"], "attempt": m["run_attempt"],
                    "sha256": sha256_file(os.path.join(d, "summary.txt"))}
    json.dump(m, open(os.path.join(d, "manifest.json"), "w"))


DEL = object()


def selftest():
    if os.environ.get("PK_SELFTEST_CHILD"):
        # a command-line test case started the selftest again: report it, never recurse
        print("selftest started from inside a selftest (recursion guard)", file=sys.stderr)
        return 99
    def build(mutate):
        d = tempfile.mkdtemp()
        good_fixture(d)
        mutate(d)
        return d

    def edit(name, fn, remanifest=True):
        # remanifest=True: the defect is in the content, the manifest is regenerated;
        # False: the file changes after the manifest was written (stale / swapped evidence)
        def m(d):
            p = os.path.join(d, name)
            open(p, "w").write(fn(open(p).read()))
            if remanifest and name in FETCHED:
                old = json.load(open(os.path.join(d, "manifest.json")))
                write_manifest(d)
                new = json.load(open(os.path.join(d, "manifest.json")))
                new["summary"] = old["summary"]
                json.dump(new, open(os.path.join(d, "manifest.json"), "w"))
        return m

    def manifest(**over):
        def m(d):
            old = json.load(open(os.path.join(d, "manifest.json")))
            old.update(over)
            if "run_attempt" in over and "summary" not in over and isinstance(old.get("summary"), dict):
                old["summary"]["attempt"] = over["run_attempt"]   # keep the attachment consistent
            json.dump(old, open(os.path.join(d, "manifest.json"), "w"))
        return m

    def sub(key, **over):
        """change one field of a nested manifest record (or delete it with value DEL)"""
        def m(d):
            old = json.load(open(os.path.join(d, "manifest.json")))
            for k, v in over.items():
                if v is DEL:
                    old[key].pop(k, None)
                else:
                    old[key][k] = v
            json.dump(old, open(os.path.join(d, "manifest.json"), "w"))
        return m

    NOT, INC, MET = "PK NOT MET", "PK INCOMPLETE (not read)", "PK MET"
    cases = [
        ("good, all channels, bound", lambda d: None, MET),
        ("summary not read", lambda d: (os.remove(os.path.join(d, "summary.txt")),
                                        manifest(summary=None)(d)), INC),
        ("log missing", lambda d: os.remove(os.path.join(d, "log.txt")), NOT),
        ("unmasked token missing from log output",
         edit("log.txt", lambda t: "\n".join(l for l in t.splitlines() if not (l.endswith(TOKEN) and "PK_UNMASKED" not in l and "##[notice]" not in l)) + "\n"), NOT),
        ("only the env header and the notice carry the token", edit("log.txt", lambda t: t.replace("Z " + TOKEN + "\n", "Z x\n")), NOT),
        ("artifact differs", edit("artifact/pk-artifact.txt", lambda t: "other\n"), NOT),
        ("annotation lacks token", edit("annotations.json", lambda t: "[]"), NOT),
        ("annotation token only in another field", edit("annotations.json", lambda t: json.dumps([{"title": TOKEN, "message": "x"}])), NOT),
        ("annotations not JSON", edit("annotations.json", lambda t: "not json " + TOKEN), NOT),
        ("annotation other canary", edit("annotations.json", lambda t: json.dumps([{"message": TOKEN}, {"message": "CANARY-212-ffffffffffffffffffffffffffffffff"}])), NOT),
        ("summary lacks token", edit("summary.txt", lambda t: "x\n"), NOT),
        ("summary other canary", edit("summary.txt", lambda t: t + "CANARY-212-ffffffffffffffffffffffffffffffff\n"), NOT),
        ("artifact other canary", edit("artifact/pk-artifact.txt", lambda t: t + "CANARY-212-ffffffffffffffffffffffffffffffff\n"), NOT),
        ("secret not masked", edit("log.txt", lambda t: t.replace("masked-test: ***", "masked-test: CANARY-212-0123456789abcdef0123456789abcdef")), NOT),
        ("another canary leaks into the log", edit("log.txt", lambda t: t + "x CANARY-212-ffffffffffffffffffffffffffffffff\n"), NOT),
        ("wrong secret length", edit("log.txt", lambda t: t.replace("length=%d" % EXPECTED_LEN, "length=0")), NOT),
        ("no PK-U line", edit("log.txt", lambda t: re.sub(r".*PK-U .*\n", "", t)), NOT),
        ("extra visible secret name", edit("log.txt", lambda t: t.replace('"github_token"]', '"github_token","CANARY_BRANCHONLY"]')), NOT),
        ("secret names line missing", edit("log.txt", lambda t: re.sub(r".*PK-J .*\n", "", t)), NOT),
        # F2: binding to the run
        ("manifest missing", lambda d: os.remove(os.path.join(d, "manifest.json")), NOT),
        ("run head differs from the approved head", manifest(head_sha="b2" * 20), NOT),
        ("event is not workflow_dispatch", manifest(event="push"), NOT),
        ("run not successful", manifest(conclusion="failure"), NOT),
        ("run not completed", manifest(status="in_progress"), NOT),
        ("branch is not main", manifest(head_branch="feature/x"), NOT),
        ("rerun attempt 2 without a held attempt 1", manifest(run_attempt=2), NOT),
        # --- attempt binding (06n): the owner chooses the attempt independently ---
        ("attempt 2 after a held attempt 1", manifest(run_attempt=2, previous_attempts=[HELD_ATTEMPT_1]), MET, {"expect_attempt": 2}),
        ("attempt 2, earlier attempts not recorded", manifest(run_attempt=2, previous_attempts=[]), NOT, {"expect_attempt": 2}),
        ("attempt 2, attempt 1 failed", manifest(run_attempt=2, previous_attempts=[dict(HELD_ATTEMPT_1, conclusion="failure")]), NOT, {"expect_attempt": 2}),
        ("attempt 2, attempt 1 had a job", manifest(run_attempt=2, previous_attempts=[dict(HELD_ATTEMPT_1, jobs=1)]), NOT, {"expect_attempt": 2}),
        ("attempt 2, attempt 1 not completed", manifest(run_attempt=2, previous_attempts=[dict(HELD_ATTEMPT_1, status="in_progress")]), NOT, {"expect_attempt": 2}),
        ("attempt 2, attempt 1 succeeded", manifest(run_attempt=2, previous_attempts=[dict(HELD_ATTEMPT_1, conclusion="success", jobs=1)]), NOT, {"expect_attempt": 2}),
        ("manifest attempt 2, owner expects 1", manifest(run_attempt=2, previous_attempts=[HELD_ATTEMPT_1]), NOT),
        ("manifest attempt 1, owner expects 2", lambda d: None, NOT, {"expect_attempt": 2}),
        ("attempt 3 is not accepted", manifest(run_attempt=3, previous_attempts=[HELD_ATTEMPT_1, dict(HELD_ATTEMPT_1, run_attempt=2)]), NOT, {"expect_attempt": 3}),
        ("attempt 1 with an earlier attempt recorded", manifest(previous_attempts=[HELD_ATTEMPT_1]), NOT),
        # --- summary bound to the attempt (06n F2) ---
        ("summary without an attempt", sub("summary", attempt=DEL), NOT),
        ("summary attached to another attempt", sub("summary", attempt=2), NOT),
        ("summary attempt differs from the expected", lambda d: None, NOT, {"expect_attempt": 2}),
        ("summary of attempt 2 on an attempt-2 manifest", manifest(run_attempt=2, previous_attempts=[HELD_ATTEMPT_1]), MET, {"expect_attempt": 2}),
        # --- artifact origin (06n F1) ---
        ("artifact record missing", manifest(artifact=None), NOT),
        ("attempt window missing", manifest(attempt_window=None), NOT),
        ("artifact created before the attempt window", sub("artifact", created_at="2025-12-31T23:59:59Z"), NOT),
        ("artifact created after the attempt window", sub("artifact", created_at="2026-01-01T00:02:00Z"), NOT),
        ("artifact of another run", sub("artifact", workflow_run_id=999), NOT),
        ("artifact of another head", sub("artifact", head_sha="b2" * 20), NOT),
        ("artifact id not an integer", sub("artifact", id="777"), NOT),
        ("artifact zip digest malformed", sub("artifact", zip_sha256="zz"), NOT),
        ("expected attempt not given", lambda d: None, INC, {"expect_attempt": None}),
        ("expected attempt not numeric", lambda d: None, NOT, {"expect_attempt": "x"}),
        ("manifest repository differs from the expected", manifest(repository="o/other"), NOT),
        ("manifest repository missing", manifest(repository=None), NOT),
        ("manifest run id differs from the expected", manifest(run_id=123457), NOT),
        ("workflow path differs", manifest(workflow_path=".github/workflows/lab-gate-pr.yml"), NOT),
        ("log replaced after the manifest (stale mix)", edit("log.txt", lambda t: t + "# other run\n", remanifest=False), NOT),
        ("stale extra file in the directory", lambda d: open(os.path.join(d, "old-summary.txt"), "w").write(TOKEN), NOT),
        ("summary replaced after attachment", edit("summary.txt", lambda t: TOKEN + "\n\n", remanifest=False), NOT),
        ("summary attached to another run", lambda d: manifest(summary={"run_id": 999, "sha256": sha256_file(os.path.join(d, "summary.txt"))})(d), NOT),
        ("summary file without attachment record", manifest(summary=None), NOT),
    ]
    bad = 0
    for item in cases:
        label, m, want = item[:3]
        kw = item[3] if len(item) > 3 else {}
        args = dict(expect_head=HEAD, expect_sha=SHA, expect_repo=REPO, expect_run_id=RUN,
                    expect_attempt=1)
        args.update(kw)
        got = overall(evaluate(build(m), **args))
        ok = got == want
        print("%-4s %-52s want=%s got=%s" % ("ok" if ok else "FAIL", label, want, got))
        bad += 0 if ok else 1
    extra = [
        ("expected digest differs", dict(expect_sha="b" * 64), NOT),
        ("expected digest not given (F4)", dict(expect_sha=None), INC),
        ("approved head SHA not given", dict(expect_head=None), INC),
        ("approved head SHA differs", dict(expect_head="c3" * 20), NOT),
        ("expected digest malformed", dict(expect_sha="zz"), NOT),
        ("different repository (F2.1)", dict(expect_repo="o/other"), NOT),
        ("repository not given", dict(expect_repo=None), INC),
        ("same head, other run id (F2.1)", dict(expect_run_id=123457), NOT),
        ("run id not given", dict(expect_run_id=None), INC),
        ("run id not numeric", dict(expect_run_id="12x"), NOT),
    ]
    d = build(lambda d: None)
    for label, kw, want in extra:
        base = dict(expect_head=HEAD, expect_sha=SHA, expect_repo=REPO, expect_run_id=RUN,
                    expect_attempt=1)
        base.update(kw)
        got = overall(evaluate(d, **base))
        ok = got == want
        print("%-4s %-52s want=%s got=%s" % ("ok" if ok else "FAIL", label, want, got))
        bad += 0 if ok else 1
    # manifest writer: accepts the approved run, refuses every other
    def run_json(**over):
        r = {"id": 123456, "path": WORKFLOW_PATH, "event": "workflow_dispatch",
             "status": "completed", "conclusion": "success", "head_branch": "main",
             "run_attempt": 1, "head_sha": HEAD,
             "run_started_at": WINDOW["start"], "updated_at": WINDOW["end"],
             "repository": {"full_name": "o/r"}, "head_repository": {"full_name": "o/r"}}
        r.update(over)
        return r
    A_OK = {"artifacts": [{"id": 777, "name": "pk-channels", "expired": False,
                           "created_at": "2026-01-01T00:00:30Z", "size_in_bytes": 200,
                           "workflow_run": {"id": 123456, "head_sha": HEAD}}]}

    def arts(**over):
        a = json.loads(json.dumps(A_OK))
        a["artifacts"][0].update(over)
        return a

    ZIP = "c" * 64
    mcases = [
        ("manifest writer: approved run, attempt 1", run_json(), 0, 1, [], A_OK, ZIP),
        ("manifest writer: other head", run_json(head_sha="b2" * 20), 1, 1, [], A_OK, ZIP),
        ("manifest writer: push event", run_json(event="push"), 1, 1, [], A_OK, ZIP),
        ("manifest writer: failed run", run_json(conclusion="failure"), 1, 1, [], A_OK, ZIP),
        ("manifest writer: attempt 2 not asked for", run_json(run_attempt=2), 1, 1, [], A_OK, ZIP),
        ("manifest writer: other branch", run_json(head_branch="x"), 1, 1, [], A_OK, ZIP),
        ("manifest writer: other repository", run_json(repository={"full_name": "o/other"}), 1, 1, [], A_OK, ZIP),
        ("manifest writer: fork head", run_json(head_repository={"full_name": "f/r"}), 1, 1, [], A_OK, ZIP),
        ("manifest writer: other workflow", run_json(path=".github/workflows/lab-gate-pr.yml"), 1, 1, [], A_OK, ZIP),
        ("manifest writer: attempt 2 after held attempt 1", run_json(run_attempt=2), 0, 2, [HELD_ATTEMPT_1], A_OK, ZIP),
        ("manifest writer: attempt 2, no history", run_json(run_attempt=2), 1, 2, [], A_OK, ZIP),
        ("manifest writer: attempt 2, attempt 1 had a job", run_json(run_attempt=2), 1, 2, [dict(HELD_ATTEMPT_1, jobs=1)], A_OK, ZIP),
        ("manifest writer: run says 1, owner says 2", run_json(), 1, 2, [HELD_ATTEMPT_1], A_OK, ZIP),
        ("manifest writer: attempt 3", run_json(run_attempt=3), 1, 3, [HELD_ATTEMPT_1, dict(HELD_ATTEMPT_1, run_attempt=2)], A_OK, ZIP),
        ("manifest writer: attempt not numeric", run_json(), 1, "x", [], A_OK, ZIP),
        # artifact origin
        ("manifest writer: artifact created before the window", run_json(), 1, 1, [], arts(created_at="2025-12-31T23:59:00Z"), ZIP),
        ("manifest writer: artifact created after the window", run_json(), 1, 1, [], arts(created_at="2026-01-01T00:05:00Z"), ZIP),
        ("manifest writer: artifact of another head", run_json(), 1, 1, [], arts(workflow_run={"id": 123456, "head_sha": "b2" * 20}), ZIP),
        ("manifest writer: artifact of another run", run_json(), 1, 1, [], arts(workflow_run={"id": 5, "head_sha": HEAD}), ZIP),
        ("manifest writer: artifact expired", run_json(), 1, 1, [], arts(expired=True), ZIP),
        ("manifest writer: no artifact", run_json(), 1, 1, [], {"artifacts": []}, ZIP),
        ("manifest writer: two artifacts in the window", run_json(), 1, 1, [],
         {"artifacts": A_OK["artifacts"] + [dict(A_OK["artifacts"][0], id=778)]}, ZIP),
        ("manifest writer: one in, one outside the window", run_json(), 0, 1, [],
         {"artifacts": A_OK["artifacts"] + [dict(A_OK["artifacts"][0], id=778, created_at="2025-01-01T00:00:00Z")]}, ZIP),
        ("manifest writer: attempt window unreadable", run_json(updated_at=None), 1, 1, [], A_OK, ZIP),
        ("manifest writer: zip digest malformed", run_json(), 1, 1, [], A_OK, "zz"),
    ]
    import contextlib, io
    for label, rj, want, att, prev, ar, zsha in mcases:
        d = build(lambda d: None)
        os.remove(os.path.join(d, "manifest.json"))
        os.remove(os.path.join(d, "summary.txt"))   # the writer does not attach a summary
        rp = os.path.join(d, "..", "run-%d.json" % id(rj))
        pp = os.path.join(d, "..", "prev-%d.json" % id(rj))
        ap = os.path.join(d, "..", "arts-%d.json" % id(rj))
        json.dump(rj, open(rp, "w"))
        json.dump(prev, open(pp, "w"))
        json.dump(ar, open(ap, "w"))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            got = write_manifest_from_run(d, rp, "o/r", HEAD, att, pp, ap, zsha)
        ok = got == want
        print("%-4s %-52s want=%s got=%s" % ("ok" if ok else "FAIL", label, want, got))
        bad += 0 if ok else 1
        if want == 0:
            ck = overall(evaluate(d, HEAD, SHA, "o/r", 123456, att))
            ok = ck == INC   # every channel but the not-yet-attached summary is read
            print("%-4s %-52s want=%s got=%s" % ("ok" if ok else "FAIL", "  (the written manifest is accepted by the reader)", INC, ck))
            bad += 0 if ok else 1
    # owner-supplied attempt on the summary attachment
    for label, att_arg, want in (("attach-summary: right run and attempt", 1, 0),
                                 ("attach-summary: wrong attempt", 2, 2),
                                 ("attach-summary: attempt not numeric", "x", 2)):
        d = build(lambda d: None)
        os.remove(os.path.join(d, "summary.txt"))
        mm = json.load(open(os.path.join(d, "manifest.json"))); mm.pop("summary")
        json.dump(mm, open(os.path.join(d, "manifest.json"), "w"))
        sp = os.path.join(d, "..", "sum-%d.txt" % id(label))
        open(sp, "w").write(TOKEN + "\n")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            got = attach_summary(d, sp, 123456, att_arg)
        ok = got == want
        print("%-4s %-52s want=%s got=%s" % ("ok" if ok else "FAIL", label, want, got))
        bad += 0 if ok else 1
        if want == 0:
            ck = overall(evaluate(d, HEAD, SHA, "o/r", 123456, 1))
            ok = ck == "PK MET"
            print("%-4s %-52s want=PK MET got=%s" % ("ok" if ok else "FAIL", "  (the attached summary is read as MET)", ck))
            bad += 0 if ok else 1
    # --- command-line level: the real entry points, as the scripts call them ---
    import subprocess

    def cli(*argv):
        p = subprocess.run([sys.executable, "-I", os.path.abspath(__file__)] + [str(a) for a in argv],
                           capture_output=True, text=True,
                           env=dict(os.environ, PK_SELFTEST_CHILD="1"))
        return p.returncode, p.stdout + p.stderr

    def cli_case(label, got, want):
        nonlocal bad
        ok = got == want
        print("%-4s %-52s want=%s got=%s" % ("ok" if ok else "FAIL", label, want, got))
        bad += 0 if ok else 1

    d = build(lambda d: None)
    os.remove(os.path.join(d, "summary.txt"))
    mm = json.load(open(os.path.join(d, "manifest.json"))); mm.pop("summary")
    json.dump(mm, open(os.path.join(d, "manifest.json"), "w"))
    sp = os.path.join(d, "..", "cli-summary.txt")
    open(sp, "w").write(TOKEN + "\n")
    cli_case("CLI attach-summary: missing the attempt argument", cli("--attach-summary", d, sp, 123456)[0], 2)
    cli_case("CLI attach-summary: wrong attempt", cli("--attach-summary", d, sp, 123456, 2)[0], 2)
    cli_case("CLI attach-summary: summary file does not exist", cli("--attach-summary", d, "/nonexistent/summary.txt", 123456, 1)[0], 2)
    cli_case("CLI attach-summary: right run and attempt", cli("--attach-summary", d, sp, 123456, 1)[0], 0)
    rc, out = cli(d, "--expect-repo", REPO, "--expect-run-id", RUN, "--expect-attempt", 1,
                  "--expect-head-sha", HEAD, "--expect-sha256", SHA)
    cli_case("CLI evaluate after attach: PK MET, exit 0", (rc, "OVERALL: PK MET" in out), (0, True))
    cli_case("CLI evaluate without --expect-attempt: INCOMPLETE, exit 1",
             cli(d, "--expect-repo", REPO, "--expect-run-id", RUN, "--expect-head-sha", HEAD, "--expect-sha256", SHA)[0], 1)
    t = tempfile.mkdtemp()
    json.dump(run_json(), open(os.path.join(t, "run.json"), "w"))
    json.dump([], open(os.path.join(t, "prev.json"), "w"))
    json.dump(A_OK, open(os.path.join(t, "arts.json"), "w"))
    cli_case("CLI check-run: approved run", cli("--check-run", t + "/run.json", "o/r", HEAD, 1, t + "/prev.json")[0], 0)
    cli_case("CLI check-run: missing argument", cli("--check-run", t + "/run.json", "o/r", HEAD, 1)[0], 2)
    rc, out = cli("--pick-artifact", t + "/run.json", t + "/arts.json", HEAD)
    cli_case("CLI pick-artifact: prints the id", (rc, out.strip()), (0, "777"))
    cli_case("CLI pick-artifact: missing argument", cli("--pick-artifact", t + "/run.json", t + "/arts.json")[0], 2)
    d2 = build(lambda d: None)
    os.remove(os.path.join(d2, "manifest.json")); os.remove(os.path.join(d2, "summary.txt"))
    cli_case("CLI write-manifest: approved run", cli("--write-manifest", d2, t + "/run.json", "o/r", HEAD, 1, t + "/prev.json", t + "/arts.json", "c" * 64)[0], 0)
    cli_case("CLI write-manifest: missing argument", cli("--write-manifest", d2, t + "/run.json", "o/r", HEAD, 1, t + "/prev.json", t + "/arts.json")[0], 2)
    # --- command line: wrong VALUES per entry point, an attempt-2 end to end, --selftest mixed ---
    def bad_json(name, text):
        pth = os.path.join(t, name)
        open(pth, "w").write(text)
        return pth

    broken = bad_json("broken.json", "{not json")
    cli_case("CLI check-run: wrong head", cli("--check-run", t + "/run.json", "o/r", "b2" * 20, 1, t + "/prev.json")[0], 1)
    cli_case("CLI check-run: head not a SHA", cli("--check-run", t + "/run.json", "o/r", "zz", 1, t + "/prev.json")[0], 1)
    cli_case("CLI check-run: wrong repository", cli("--check-run", t + "/run.json", "o/other", HEAD, 1, t + "/prev.json")[0], 1)
    cli_case("CLI check-run: attempt not numeric", cli("--check-run", t + "/run.json", "o/r", HEAD, "x", t + "/prev.json")[0], 1)
    cli_case("CLI check-run: attempt 2 without history", cli("--check-run", t + "/run.json", "o/r", HEAD, 2, t + "/prev.json")[0], 1)
    cli_case("CLI check-run: run JSON broken", cli("--check-run", broken, "o/r", HEAD, 1, t + "/prev.json")[0], 1)
    cli_case("CLI check-run: file does not exist", cli("--check-run", "/nonexistent.json", "o/r", HEAD, 1, t + "/prev.json")[0], 1)
    cli_case("CLI pick-artifact: wrong head", cli("--pick-artifact", t + "/run.json", t + "/arts.json", "b2" * 20)[0], 1)
    cli_case("CLI pick-artifact: artifact list broken", cli("--pick-artifact", t + "/run.json", broken, HEAD)[0], 1)
    json.dump({"artifacts": []}, open(os.path.join(t, "none.json"), "w"))
    cli_case("CLI pick-artifact: no artifact", cli("--pick-artifact", t + "/run.json", t + "/none.json", HEAD)[0], 1)
    cli_case("CLI pick-artifact: run JSON missing", cli("--pick-artifact", "/nonexistent.json", t + "/arts.json", HEAD)[0], 1)
    for label, over in (("wrong head", {"head": "b2" * 20}), ("attempt not numeric", {"att": "x"}),
                        ("zip digest malformed", {"zip": "zz"}), ("history file broken", {"prev": broken}),
                        ("artifact list broken", {"arts": broken})):
        dd = build(lambda d: None)
        os.remove(os.path.join(dd, "manifest.json")); os.remove(os.path.join(dd, "summary.txt"))
        cli_case("CLI write-manifest: " + label,
                 cli("--write-manifest", dd, t + "/run.json", "o/r", over.get("head", HEAD), over.get("att", 1),
                     over.get("prev", t + "/prev.json"), over.get("arts", t + "/arts.json"), over.get("zip", "c" * 64))[0], 1)
        cli_case("CLI write-manifest: " + label + " leaves no manifest", os.path.exists(os.path.join(dd, "manifest.json")), False)
    base = [d, "--expect-repo", REPO, "--expect-run-id", RUN, "--expect-attempt", 1, "--expect-head-sha", HEAD, "--expect-sha256", SHA]

    def with_(flag, value):
        a = list(base)
        a[a.index(flag) + 1] = value
        return a
    cli_case("CLI evaluate: wrong digest", cli(*with_("--expect-sha256", "b" * 64))[0], 1)
    cli_case("CLI evaluate: digest malformed", cli(*with_("--expect-sha256", "zz"))[0], 1)
    cli_case("CLI evaluate: wrong run id", cli(*with_("--expect-run-id", RUN + 1))[0], 1)
    cli_case("CLI evaluate: run id not numeric", cli(*with_("--expect-run-id", "x"))[0], 1)
    cli_case("CLI evaluate: wrong attempt", cli(*with_("--expect-attempt", 2))[0], 1)
    cli_case("CLI evaluate: wrong repository", cli(*with_("--expect-repo", "o/other"))[0], 1)
    cli_case("CLI evaluate: wrong head", cli(*with_("--expect-head-sha", "b2" * 20))[0], 1)
    cli_case("CLI evaluate: flag without a value", cli(d, "--expect-repo")[0], 2)
    cli_case("CLI evaluate: extra positional argument", cli(*(base + ["extra"]))[0], 2)
    cli_case("CLI evaluate: directory does not exist", cli("/nonexistent-dir", *base[1:])[0], 1)
    # attempt 2 end to end through real subprocess calls
    d3 = build(manifest(run_attempt=2, previous_attempts=[HELD_ATTEMPT_1]))
    os.remove(os.path.join(d3, "summary.txt"))
    m3 = json.load(open(os.path.join(d3, "manifest.json"))); m3.pop("summary")
    json.dump(m3, open(os.path.join(d3, "manifest.json"), "w"))
    sp3 = os.path.join(d3, "..", "cli-summary-2.txt")
    open(sp3, "w").write(TOKEN + "\n")
    cli_case("CLI attempt 2: attach with attempt 1 is refused", cli("--attach-summary", d3, sp3, 123456, 1)[0], 2)
    cli_case("CLI attempt 2: attach with attempt 2", cli("--attach-summary", d3, sp3, 123456, 2)[0], 0)
    rc, out = cli(d3, "--expect-repo", REPO, "--expect-run-id", RUN, "--expect-attempt", 2,
                  "--expect-head-sha", HEAD, "--expect-sha256", SHA)
    cli_case("CLI attempt 2: evaluate gives PK MET, exit 0", (rc, "OVERALL: PK MET" in out), (0, True))
    cli_case("CLI attempt 2: evaluate expecting attempt 1 is NOT MET",
             cli(d3, "--expect-repo", REPO, "--expect-run-id", RUN, "--expect-attempt", 1,
                 "--expect-head-sha", HEAD, "--expect-sha256", SHA)[0], 1)
    # --selftest only as the sole argument
    cli_case("CLI --selftest mixed with --attach-summary is refused (exit 2)", cli("--selftest", "--attach-summary", d3, sp3, 123456, 2)[0], 2)
    cli_case("CLI --selftest mixed with a directory is refused (exit 2)", cli(d3, "--selftest")[0], 2)
    cli_case("CLI --selftest with an extra argument is refused (exit 2)", cli("--selftest", "extra")[0], 2)
    print("SELFTEST %s" % ("FAILED" if bad else "OK"))
    return 1 if bad else 0


def main(argv):
    if "--selftest" in argv:
        if argv[1:] != ["--selftest"]:
            print("refusing: --selftest must be the only argument", file=sys.stderr)
            return 2
        return selftest()
    args = argv[1:]
    if args and args[0] == "--write-manifest":
        if len(args) != 9:
            print(__doc__, file=sys.stderr)
            return 2
        return write_manifest_from_run(*args[1:])
    if args and args[0] == "--pick-artifact":
        if len(args) != 4:
            print(__doc__, file=sys.stderr)
            return 2
        return pick_artifact_main(*args[1:])
    if args and args[0] == "--check-run":
        if len(args) != 6:
            print(__doc__, file=sys.stderr)
            return 2
        return check_run_main(*args[1:])
    if args and args[0] == "--attach-summary":
        if len(args) != 5:
            print(__doc__, file=sys.stderr)
            return 2
        return attach_summary(*args[1:])
    opts = {}
    for flag, key in (("--expect-head-sha", "expect_head"), ("--expect-sha256", "expect_sha"),
                      ("--expect-repo", "expect_repo"), ("--expect-run-id", "expect_run_id"),
                      ("--expect-attempt", "expect_attempt")):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                print(__doc__, file=sys.stderr)
                return 2
            opts[key] = args[i + 1]
            del args[i:i + 2]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    res = evaluate(args[0], **opts)
    report(res)
    return 0 if overall(res) == "PK MET" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
