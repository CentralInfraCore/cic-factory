#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Harness reader for the phase 0 positive-control run (pk-canary-channels).

  read-pk.py DIR [--expect-sha256 HEX]   evaluate fetched files
  read-pk.py --selftest                  the reader must accept a good fixture and
                                         reject every planted defect (it can fail)

DIR holds: log.txt, annotations.json, artifact/pk-artifact.txt, and optionally
summary.txt (the job summary is not read through the API in this package; absent
= NOT-READ for that channel, never a pass).

Per-check result: MET / NOT-MET / NOT-READ. These describe the MEASURING
INSTRUMENT only (positive controls); they are not verdicts on the platform
property and not measurement results of H1/H2.
"""
import json
import os
import re
import sys
import tempfile

TOKEN = "CANARY-212-PK-UNMASKED-00000000000000000000"
EXPECTED_LEN = len("CANARY-212-") + 32
EXPECTED_NAMES = ["CANARY_UNRESTRICTED", "github_token"]


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def evaluate(d, expect_sha=None):
    res = []  # (check, result, note)
    log = read(os.path.join(d, "log.txt"))
    ann = read(os.path.join(d, "annotations.json"))
    art = read(os.path.join(d, "artifact", "pk-artifact.txt"))
    summ = read(os.path.join(d, "summary.txt"))

    # (U) the unmasked, known canary must be seen on each channel
    if log is None:
        res.append(("U log", "NOT-READ", "log.txt missing"))
    else:
        # the run echoes it as its own output line; the environment header line
        # and the annotation echo do not count
        out_lines = [l for l in log.splitlines()
                     if l.rstrip().endswith(TOKEN)
                     and "PK_UNMASKED" not in l and "##[notice]" not in l]
        res.append(("U log", "MET" if out_lines else "NOT-MET",
                    "%d output line(s)" % len(out_lines)))
    if art is None:
        res.append(("U artifact", "NOT-READ", "artifact missing"))
    else:
        res.append(("U artifact", "MET" if art.strip() == TOKEN else "NOT-MET", ""))
    if ann is None:
        res.append(("U annotation", "NOT-READ", "annotations.json missing"))
    else:
        res.append(("U annotation", "MET" if TOKEN in ann else "NOT-MET", ""))
    if summ is None:
        res.append(("U summary", "NOT-READ", "summary channel not read in this package"))
    else:
        res.append(("U summary", "MET" if TOKEN in summ else "NOT-MET", ""))

    # (U) the unrestricted repository secret is readable inside a job (length, digest)
    if log is None:
        res.append(("U secret readable", "NOT-READ", "log.txt missing"))
    else:
        m = re.search(r"PK-U length=(\d+) sha256=([0-9a-f]{64})\b", log)
        if not m:
            res.append(("U secret readable", "NOT-MET", "no PK-U line"))
        elif int(m.group(1)) != EXPECTED_LEN:
            res.append(("U secret readable", "NOT-MET", "length %s" % m.group(1)))
        elif expect_sha and m.group(2) != expect_sha:
            res.append(("U secret readable", "NOT-MET", "digest differs from the expected"))
        else:
            res.append(("U secret readable", "MET",
                        "length ok" + ("; digest matches" if expect_sha else "; digest not compared")))

    # (J) a registered secret is masked in the log and no other canary-looking value leaks
    if log is None:
        res.append(("J masked", "NOT-READ", "log.txt missing"))
        res.append(("J no other canary", "NOT-READ", "log.txt missing"))
        res.append(("J secret names", "NOT-READ", "log.txt missing"))
    else:
        masked = any(re.search(r"masked-test: \*\*\*\s*$", l) for l in log.splitlines())
        res.append(("J masked", "MET" if masked else "NOT-MET", ""))
        rest = log.replace(TOKEN, "")
        other = re.findall(r"CANARY-212-[0-9A-Za-z-]*", rest)
        res.append(("J no other canary", "MET" if not other else "NOT-MET",
                    "%d other occurrence(s)" % len(other)))
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
        print("%-20s %-9s %s" % (c, r, n))
    print("OVERALL: %s" % overall(res))


def good_fixture(d, sha="a" * 64):
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
    open(os.path.join(d, "annotations.json"), "w").write(json.dumps([{"message": TOKEN}]))
    open(os.path.join(d, "artifact", "pk-artifact.txt"), "w").write(TOKEN + "\n")
    open(os.path.join(d, "summary.txt"), "w").write(TOKEN + "\n")


def selftest():
    def build(mutate):
        d = tempfile.mkdtemp()
        good_fixture(d)
        mutate(d)
        return d

    def edit(name, fn):
        def m(d):
            p = os.path.join(d, name)
            open(p, "w").write(fn(open(p).read()))
        return m

    cases = [
        ("good, summary included", lambda d: None, "PK MET"),
        ("summary not read", lambda d: os.remove(os.path.join(d, "summary.txt")), "PK INCOMPLETE (not read)"),
        ("log missing", lambda d: os.remove(os.path.join(d, "log.txt")), "PK INCOMPLETE (not read)"),
        ("unmasked token missing from log output",
         edit("log.txt", lambda t: "\n".join(l for l in t.splitlines() if not (l.endswith(TOKEN) and "PK_UNMASKED" not in l and "##[notice]" not in l)) + "\n"), "PK NOT MET"),
        ("only the env header and the notice carry the token", edit("log.txt", lambda t: t.replace("Z " + TOKEN + "\n", "Z x\n")), "PK NOT MET"),
        ("artifact differs", edit("artifact/pk-artifact.txt", lambda t: "other\n"), "PK NOT MET"),
        ("annotation lacks token", edit("annotations.json", lambda t: "[]"), "PK NOT MET"),
        ("summary lacks token", edit("summary.txt", lambda t: "x\n"), "PK NOT MET"),
        ("secret not masked", edit("log.txt", lambda t: t.replace("masked-test: ***", "masked-test: CANARY-212-0123456789abcdef0123456789abcdef")), "PK NOT MET"),
        ("another canary leaks into the log", edit("log.txt", lambda t: t + "x CANARY-212-ffffffffffffffffffffffffffffffff\n"), "PK NOT MET"),
        ("wrong secret length", edit("log.txt", lambda t: t.replace("length=%d" % EXPECTED_LEN, "length=0")), "PK NOT MET"),
        ("no PK-U line", edit("log.txt", lambda t: re.sub(r".*PK-U .*\n", "", t)), "PK NOT MET"),
        ("extra visible secret name", edit("log.txt", lambda t: t.replace('"github_token"]', '"github_token","CANARY_BRANCHONLY"]')), "PK NOT MET"),
        ("secret names line missing", edit("log.txt", lambda t: re.sub(r".*PK-J .*\n", "", t)), "PK NOT MET"),
    ]
    bad = 0
    for label, m, want in cases:
        got = overall(evaluate(build(m)))
        ok = got == want
        print("%-4s %-52s want=%s got=%s" % ("ok" if ok else "FAIL", label, want, got))
        bad += 0 if ok else 1
    # digest comparison is itself a check that can fail
    d = build(lambda d: None)
    got = overall(evaluate(d, expect_sha="b" * 64))
    print("%-4s %-52s want=PK NOT MET got=%s" % ("ok" if got == "PK NOT MET" else "FAIL", "expected digest differs", got))
    bad += 0 if got == "PK NOT MET" else 1
    got = overall(evaluate(d, expect_sha="a" * 64))
    print("%-4s %-52s want=PK MET got=%s" % ("ok" if got == "PK MET" else "FAIL", "expected digest matches", got))
    bad += 0 if got == "PK MET" else 1
    print("SELFTEST %s (%d cases)" % ("FAILED" if bad else "OK", len(cases) + 2))
    return 1 if bad else 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    expect = None
    args = argv[1:]
    if "--expect-sha256" in args:
        i = args.index("--expect-sha256")
        expect = args[i + 1]
        del args[i:i + 2]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    res = evaluate(args[0], expect)
    report(res)
    return 0 if overall(res) == "PK MET" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
