#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
"""Local, read-only OCI VCN pipeline: Intent -> Observed State -> Conformance/Drift -> Evidence, over a fixture.

    run.py [--case ID ...] [--fixture DIR] [--json] [--require-executed STAGES] [--fixture-only]

STAGES is a comma-separated list of normalize,bind,verdict,evidence (or `all`). A required stage whose executed adapter is unavailable
is an error; an executed adapter that was available and failed is always an error. Without --require-executed an unavailable stage falls
back to the fixture and is labelled FIXTURE in the report.

Exit status: 0 every case ok; 1 a case failed (mismatch, handoff, required stage not executed, adapter error); 2 usage or fixture error.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import adapters  # noqa: E402
import vcnpipe  # noqa: E402


def main(argv=None, env=None, adapter_set=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--case", action="append")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--fixture", default=os.path.join(HERE, "fixtures", "vcn-v1"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--require-executed", default="")
    ap.add_argument("--fixture-only", action="store_true")
    a = ap.parse_args(argv)
    try:
        fx = vcnpipe.Fixture(a.fixture)
        problems = fx.check_manifest()
        if problems:
            print("fixture manifest: %s" % "; ".join(problems[:5]), file=sys.stderr)
            return 2
        req = vcnpipe.STAGES if a.require_executed == "all" else tuple(s for s in a.require_executed.split(",") if s)
        runner = vcnpipe.Runner(fx, adapter_set or adapters.default_adapters(), env=env, require_executed=req, fixture_only=a.fixture_only)
        cases = a.case or fx.cases()
        unknown = [c for c in cases if c not in fx.cases()]
        if unknown:
            print("unknown case(s): %s" % ", ".join(unknown), file=sys.stderr)
            return 2
    except vcnpipe.StageError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    reports = [runner.run_case(c) for c in cases]
    if a.json:
        print(json.dumps({"summary": vcnpipe.summary(reports), "cases": [r.as_dict() for r in reports]}, indent=1, sort_keys=True))
    else:
        print(vcnpipe.render(reports))
    return 0 if all(r.ok for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
