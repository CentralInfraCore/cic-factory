#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# Claude Code runner. Contract: docs/RUNNER-CONTRACT.md
#
# Everything Claude-specific in the factory lives here: the CLI flags, the
# CLAUDE_CONFIG_DIR convention, and the shape of `claude --output-format json`.
# run-job.sh knows none of it.

set -uo pipefail

PROMPT_FILE="${CIC_PROMPT_FILE:?}"
RESULT_JSON="${CIC_RESULT_JSON:?}"
RUN_LOG="${CIC_RUN_LOG:?}"
AGENT_CONFIG="${CIC_AGENT_CONFIG:-}"
MODEL="${CIC_MODEL:-}"
MAX_TURNS="${CIC_MAX_TURNS:-}"
RESUME_SESSION="${CIC_RESUME_SESSION:-}"
MCP_CONFIG="${CIC_MCP_CONFIG:-}"

FLAGS=(--print --output-format json)
[[ -n "$MCP_CONFIG"    ]] && FLAGS+=(--mcp-config "$MCP_CONFIG")
[[ -n "$MAX_TURNS"     ]] && FLAGS+=(--max-turns "$MAX_TURNS")
[[ -n "$MODEL"         ]] && FLAGS+=(--model "$MODEL")
[[ -n "$RESUME_SESSION" ]] && FLAGS+=(--resume "$RESUME_SESSION")

RAW=$(mktemp)
trap 'rm -f "$RAW"' EXIT

# stdin is closed: a background job reading the terminal would take SIGTTIN.
CLAUDE_CONFIG_DIR="$AGENT_CONFIG" claude "${FLAGS[@]}" "$(cat "$PROMPT_FILE")" \
    < /dev/null > "$RAW" 2>"$RUN_LOG" &
AGENT_PID=$!
wait "$AGENT_PID"
EXIT_CODE=$?

# Translation into the normalised result. The token accounting is the part worth
# keeping: `usage.input_tokens` is the UNCACHED input only -- on a cached run
# that is a tiny number (measured: 2, while the real input was 15912 cache_read
# + 8634 cache_creation). `modelUsage` is the per-model breakdown and includes
# auxiliary models; sum(modelUsage[*].costUSD) matched total_cost_usd exactly on
# a probe run, so it is the correct aggregate.
python3 - "$RAW" "$RESULT_JSON" <<'PYEOF'
import json, sys

raw_path, out_path = sys.argv[1], sys.argv[2]
raw = open(raw_path, encoding="utf-8", errors="replace").read()


def write(obj):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


try:
    data = json.loads(raw)
    if isinstance(data, list):          # stream-json safety net
        data = data[-1]
    if not isinstance(data, dict):
        raise ValueError("unexpected shape")
except Exception:
    # Not JSON: a crash, an auth prompt, or a session-limit banner. The contract
    # still needs a valid result, so the raw text goes in and nothing is invented
    # around it.
    write({"result": raw})
    sys.exit(0)

model_usage = data.get("modelUsage") or {}
if model_usage:
    def s(field):
        return sum(int(m.get(field) or 0) for m in model_usage.values())
    tokens = {"input": s("inputTokens"), "output": s("outputTokens"),
              "cache_read": s("cacheReadInputTokens"),
              "cache_creation": s("cacheCreationInputTokens")}
    models = ",".join(sorted(model_usage))
else:
    u = data.get("usage") or {}
    tokens = {"input": int(u.get("input_tokens") or 0),
              "output": int(u.get("output_tokens") or 0),
              "cache_read": int(u.get("cache_read_input_tokens") or 0),
              "cache_creation": int(u.get("cache_creation_input_tokens") or 0)}
    models = data.get("model") or ""

out = {"result": str(data.get("result", "")), "tokens": tokens}
# Only what the agent actually reported. A missing field is honest; a zero is a
# measurement that never happened.
if data.get("session_id"):      out["session_id"] = str(data["session_id"])
if data.get("total_cost_usd") is not None: out["cost_usd"] = data["total_cost_usd"]
if data.get("num_turns") is not None:      out["turns"] = int(data["num_turns"])
if data.get("duration_ms") is not None:    out["duration_ms"] = int(data["duration_ms"])
reason = data.get("stop_reason") or data.get("terminal_reason")
if reason:                      out["stop_reason"] = str(reason)
if models:                      out["models"] = models
write(out)
PYEOF

exit "$EXIT_CODE"
