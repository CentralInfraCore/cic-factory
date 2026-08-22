#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# Reference runner that runs no agent. Contract: docs/RUNNER-CONTRACT.md
#
# Two jobs, both serious:
#
#   1. It proves the runner contract is real. A second implementation is the
#      only thing that distinguishes an abstraction from a rename -- if the core
#      still only ever ran Claude, "pluggable" would be a claim.
#
#   2. It makes the lifecycle testable end to end. Until this existed, nothing
#      could run a whole job: every gate checked a decision in isolation, and the
#      release notes had to say so. Now a job can go pending -> done in a test,
#      with no agent, no network and no cost.
#
# Behaviour is steerable so tests can exercise the failure paths:
#
#   CIC_ECHO_EXIT=<n>       exit with n instead of 0
#   CIC_ECHO_RESULT=<text>  use this instead of echoing the prompt
#   CIC_ECHO_GARBAGE=1      write something that is not valid JSON, to exercise
#                           the "agent produced nothing parseable" path

set -uo pipefail

PROMPT_FILE="${CIC_PROMPT_FILE:?}"
RESULT_JSON="${CIC_RESULT_JSON:?}"
RUN_LOG="${CIC_RUN_LOG:?}"

echo "echo runner: no agent was run" >> "$RUN_LOG"

if [[ "${CIC_ECHO_GARBAGE:-0}" == "1" ]]; then
    printf 'this is not json\n' > "$RESULT_JSON"
    exit "${CIC_ECHO_EXIT:-0}"
fi

RESULT="${CIC_ECHO_RESULT-$(cat "$PROMPT_FILE")}"

# No cost, no turns, no tokens: this runner measured nothing, so it reports
# nothing. Emitting zeros would put a fabricated measurement into meta.yaml.
python3 - "$RESULT_JSON" "$RESULT" <<'PYEOF'
import json, sys
out_path, result = sys.argv[1], sys.argv[2]
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({"result": result, "models": "echo", "stop_reason": "end_turn"},
              f, ensure_ascii=False)
PYEOF

exit "${CIC_ECHO_EXIT:-0}"
