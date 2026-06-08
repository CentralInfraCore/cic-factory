#!/bin/bash
# no-ask-human.sh — Autonomous decision enforcement for CIC agents.
# Source: https://github.com/yurukusa/claude-code-hooks/blob/main/hooks/no-ask-human.sh (MIT)
# Adapted for CIC: decision framework references input.md, output/, feature branch workflow.
#
# Trigger: PostToolUse (all tools) + Notification
# Matcher: "" (every event)
#
# Detects when the agent asks the user a question during headless job execution.
# In CIC, agents run via `claude --print` — there is no human to answer.
# Every unanswered question is a deadlock.
#
# Never blocks (always exits 0). Issues a reminder so the agent self-corrects.

[ "${CIC_NO_ASK_ENABLED:-1}" == "0" ] && exit 0

INPUT=$(cat)

# Extract text: Notification → .message, PostToolUse → .tool_response.content or .tool_output
TEXT=""
if echo "$INPUT" | jq -e '.message' &>/dev/null; then
    TEXT=$(echo "$INPUT" | jq -r '.message // empty' 2>/dev/null)
elif echo "$INPUT" | jq -e '.tool_response' &>/dev/null; then
    TEXT=$(echo "$INPUT" | jq -r '.tool_response.content // .tool_output // empty' 2>/dev/null)
fi

[ -z "$TEXT" ] && exit 0

PATTERNS=(
    'should [iI] '
    'would you like'
    'do you want'
    'which (approach|option|method|way)'
    'what do you think'
    'shall [iI] '
    'do you prefer'
    'can you confirm'
    'is that (okay|ok|alright)'
    'let me know if'
    'please (confirm|advise|let me know)'
    'your (preference|thoughts|input)'
    'waiting for.*(input|response|feedback)'
)

MATCHED=""
for pattern in "${PATTERNS[@]}"; do
    if echo "$TEXT" | grep -qiE "$pattern"; then
        MATCHED="$pattern"
        break
    fi
done

if [[ -n "$MATCHED" ]]; then
    JOB="${CIC_JOB_ID:-(no job)}"
    echo ""
    echo "REMINDER [CIC]: Agent is running headless (job: ${JOB}). Do not ask the user questions."
    echo "  Detected pattern: \"${MATCHED}\""
    echo "  Decision framework:"
    echo "    1. Unclear spec → re-read jobs/${JOB}/input.md and ref/ for intent"
    echo "    2. Technical choice → pick the standard/conventional option"
    echo "    3. Implementation detail → follow existing code conventions in the repo"
    echo "    4. Error → investigate and fix (up to 3 attempts), then document in output/"
    echo "    5. Truly blocked → write blocker to output/blockers.md and move to next task"
    echo "  Do not wait for human input. Decide and continue."
fi

exit 0
