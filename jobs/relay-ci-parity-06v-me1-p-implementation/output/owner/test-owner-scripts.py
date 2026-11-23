#!/usr/bin/env python3
# SPDX-License-Identifier: CC-BY-NC-SA-4.0
"""Mock tests of the two owner scripts (no network, no lab access, no GitHub).

deliver-p-probe.sh runs against a LOCAL bare repository standing in for the lab repo and a LOCAL factory
repository; open-p-probe-pr.sh runs against a fake `gh`. Every refusal must exit non-zero and leave the
world untouched (no probe commit, no PR, no state file).   python3 -I test-owner-scripts.py
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
P1 = os.path.join(OUT, "payload", "p1", ".github", "workflows", "me1-evidence.yml")
P2 = os.path.join(OUT, "payload", "p2", ".github", "workflows", "me1-evidence-twin.yml")
BASE_WF = os.path.join(OUT, "..", "..", "relay-ci-parity-06q-me1-measurement-package", "output", "payload", ".github", "workflows", "me1-evidence.yml")
MAIN_SHA_PLACEHOLDER = None


def sh(cmd, cwd=None, env=None, check=True):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, check=check)


def git_env(home):
    cfg = os.path.join(home, "gitconfig")
    open(cfg, "w").write("[user]\n\tname = t\n\temail = t@example.invalid\n[commit]\n\tgpgsign = false\n[core]\n\thooksPath = /nonexistent\n[init]\n\tdefaultBranch = main\n[protocol \"file\"]\n\tallow = always\n")
    return dict(os.environ, HOME=home, GIT_CONFIG_GLOBAL=cfg, GIT_CONFIG_SYSTEM="/dev/null")


def make_home(org="CIC-Security-Lab"):
    home = tempfile.mkdtemp()
    os.makedirs(os.path.join(home, ".cache", "ci-lab"))
    open(os.path.join(home, ".cache", "ci-lab", "env.sh"), "w").write("ORG=%s\nX=r\nY=y\nexport ORG X Y\n" % org)
    return home


def make_factory(env, p1=P1, p2=P2):
    f = tempfile.mkdtemp()
    sh(["git", "init", "-q"], cwd=f, env=env)
    shutil.copy(p1, os.path.join(f, "p1.yml"))
    shutil.copy(p2, os.path.join(f, "p2.yml"))
    sh(["git", "add", "."], cwd=f, env=env)
    sh(["git", "commit", "-q", "-m", "factory"], cwd=f, env=env)
    return f, sh(["git", "rev-parse", "HEAD"], cwd=f, env=env).stdout.strip()


def make_remote(env, extra_files=None, base_wf=BASE_WF):
    bare = os.path.join(tempfile.mkdtemp(), "lab.git")
    sh(["git", "init", "-q", "--bare", bare], env=env)
    w = tempfile.mkdtemp()
    sh(["git", "clone", "-q", bare, w], env=env)
    os.makedirs(os.path.join(w, ".github", "workflows"))
    shutil.copy(base_wf, os.path.join(w, ".github", "workflows", "me1-evidence.yml"))
    open(os.path.join(w, ".github", "workflows", "lab-gate.yml"), "w").write("name: lab-gate\n")
    for name, text in (extra_files or {}).items():
        open(os.path.join(w, ".github", "workflows", name), "w").write(text)
    sh(["git", "add", "."], cwd=w, env=env)
    sh(["git", "commit", "-q", "-m", "main"], cwd=w, env=env)
    sh(["git", "push", "-q", "origin", "HEAD:main"], cwd=w, env=env)
    return bare, sh(["git", "rev-parse", "HEAD"], cwd=w, env=env).stdout.strip()


GH = r'''#!/bin/bash
f() { echo "$1" | sed 's#/#__#g'; }
case "$1" in
  api) p=$2; shift 2; q=""; [ "${1:-}" = --jq ] && q=$2
       file="$MOCK/$(f "$p").json"; [ -e "$file" ] || { echo "mock: no fixture for $p" >&2; exit 1; }
       if [ -n "$q" ]; then jq -r "$q" "$file"; else cat "$file"; fi;;
  pr) case "$2" in
        list) cat "$MOCK/pr-count";;
        create) echo "$*" >> "$MOCK/create.log";;
        *) exit 1;;
      esac;;
  *) echo "mock: unexpected gh $*" >&2; exit 1;;
esac
'''
GOOD_FILES = [{"status": "modified", "filename": ".github/workflows/me1-evidence.yml"},
              {"status": "added", "filename": ".github/workflows/me1-evidence-twin.yml"}]
PROBE = "ab" * 20
MAIN = "4d432f5e8250948af83ff909a7314eeddadb1c29"


def open_pr(home, mock, go=True, arg=PROBE, extra_env=None):
    bindir = tempfile.mkdtemp()
    p = os.path.join(bindir, "gh")
    open(p, "w").write(GH)
    os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC)
    env = dict(os.environ, HOME=home, MOCK=mock, PATH=bindir + ":" + os.environ["PATH"], P_PROBE_STATE=os.path.join(home, "p.state"))
    if go:
        env["ME1_I_HAVE_THE_GO"] = "yes"
    env.update(extra_env or {})
    r = subprocess.run(["bash", os.path.join(HERE, "open-p-probe-pr.sh"), arg], env=env, capture_output=True, text=True)
    return r


def mock_dir(main=MAIN, branch=PROBE, prs="0", files=None):
    m = tempfile.mkdtemp()
    json.dump({"commit": {"sha": main}}, open(os.path.join(m, "repos__CIC-Security-Lab__r__branches__main.json"), "w"))
    json.dump({"commit": {"sha": branch}}, open(os.path.join(m, "repos__CIC-Security-Lab__r__branches__p-probe.json"), "w"))
    json.dump({"files": GOOD_FILES if files is None else files}, open(os.path.join(m, "repos__CIC-Security-Lab__r__compare__main...p-probe.json"), "w"))
    open(os.path.join(m, "pr-count"), "w").write(prs)
    return m


def main():
    bad = 0

    def check(label, ok, note=""):
        nonlocal bad
        print("%-4s %-92s %s" % ("ok" if ok else "FAIL", label, note))
        bad += 0 if ok else 1

    # ------------------------------------------------------------ deliver-p-probe.sh
    home = make_home()
    env = git_env(home)
    factory, fsha = make_factory(env)
    bare, main_sha = make_remote(env)
    base_env = dict(env, FACTORY=factory, APPROVED_FACTORY_SHA=fsha, P1_SRC="p1.yml", P2_SRC="p2.yml",
                    ME1_REMOTE=bare, EXPECTED_MAIN_HEAD=main_sha)

    def deliver(**over):
        e = dict(base_env)
        e.update(over)
        for k in [k for k, v in e.items() if v is None]:
            del e[k]
        return subprocess.run(["bash", os.path.join(HERE, "deliver-p-probe.sh")], env=e, capture_output=True, text=True)

    r = deliver()
    check("deliver: the approved inputs produce a probe commit", r.returncode == 0 and "probe commit:" in r.stdout, r.stderr.strip()[-80:])
    if r.returncode == 0:
        line = [l for l in r.stdout.splitlines() if l.startswith("next")][0]
        work = line.split("git -C ")[1].split(" push")[0]
        files = sh(["git", "-C", work, "diff", "--name-status", "HEAD~1", "HEAD"], env=env).stdout.split("\n")
        check("deliver: exactly two files changed, M me1-evidence.yml and A me1-evidence-twin.yml",
              sorted(l for l in files if l) == ["A\t.github/workflows/me1-evidence-twin.yml", "M\t.github/workflows/me1-evidence.yml"], str(files))
        check("deliver: the remote was not written (no push, no probe branch)", sh(["git", "-C", bare, "branch", "--list", "p-probe"], env=env).stdout.strip() == "")
    r2 = subprocess.run(["bash", os.path.join(HERE, "deliver-p-probe.sh")], env=dict(base_env, HOME=make_home("CentralInfraCore")), capture_output=True, text=True)
    check("deliver refused: the organisation is not the lab", r2.returncode != 0 and "not the lab" in r2.stderr)
    check("deliver refused: APPROVED_FACTORY_SHA missing", deliver(APPROVED_FACTORY_SHA=None).returncode != 0)
    check("deliver refused: the lab main moved (not the approved head)", deliver(EXPECTED_MAIN_HEAD="a1" * 20).returncode != 0)
    f2, fsha2 = make_factory(env, p1=BASE_WF)  # a factory whose P1 file is not the approved blob
    check("deliver refused: the P1 blob on the factory commit differs", deliver(FACTORY=f2, APPROVED_FACTORY_SHA=fsha2).returncode != 0)
    f3, fsha3 = make_factory(env, p2=BASE_WF)
    check("deliver refused: the P2 blob on the factory commit differs", deliver(FACTORY=f3, APPROVED_FACTORY_SHA=fsha3).returncode != 0)
    bare2, main2 = make_remote(env, base_wf=P1)  # the protected workflow on main is not the approved base blob
    check("deliver refused: the protected workflow on main is not the approved base blob", deliver(ME1_REMOTE=bare2, EXPECTED_MAIN_HEAD=main2).returncode != 0)
    bare3, main3 = make_remote(env, extra_files={"me1-evidence-twin.yml": "name: x\n"})
    r3 = deliver(ME1_REMOTE=bare3, EXPECTED_MAIN_HEAD=main3)
    check("deliver refused: the twin file already exists on main (the probe would not be 'A twin, M protected')", r3.returncode != 0 and "more or other" in r3.stderr, r3.stderr.strip()[-70:])

    # ------------------------------------------------------------ open-p-probe-pr.sh
    h = make_home()
    m = mock_dir()
    r = open_pr(h, m)
    check("open: all pre-conditions hold, ONE PR is created and the state is written",
          r.returncode == 0 and os.path.exists(os.path.join(h, "p.state")) and len(open(os.path.join(m, "create.log")).read().splitlines()) == 1, r.stderr.strip()[-80:])
    r = open_pr(h, m)
    check("open: a second opening is refused (state), no second PR", r.returncode != 0 and len(open(os.path.join(m, "create.log")).read().splitlines()) == 1)

    def refused(label, **kw):
        hh = kw.pop("home", None) or make_home()
        mm = kw.pop("mock", None) or mock_dir()
        rr = open_pr(hh, mm, **kw)
        clean = rr.returncode != 0 and not os.path.exists(os.path.join(hh, "p.state")) and not os.path.exists(os.path.join(mm, "create.log"))
        check("open refused: " + label, clean, rr.stderr.strip()[-80:])
    refused("no explicit GO in the environment", go=False)
    refused("the probe commit is not a 40-hex SHA", arg="abc")
    refused("the lab main moved", mock=mock_dir(main="b2" * 20))
    refused("the remote p-probe is at another commit", mock=mock_dir(branch="c3" * 20))
    refused("a PR from p-probe already exists", mock=mock_dir(prs="1"))
    refused("the branch differs from main in an extra file", mock=mock_dir(files=GOOD_FILES + [{"status": "added", "filename": "README.md"}]))
    refused("the branch lacks one of the two files", mock=mock_dir(files=GOOD_FILES[:1]))
    refused("a file has another status than approved", mock=mock_dir(files=[{"status": "added", "filename": ".github/workflows/me1-evidence.yml"}, GOOD_FILES[1]]))
    refused("the organisation is not the lab", home=make_home("CentralInfraCore"))
    print("TEST %s" % ("FAILED" if bad else "OK"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
