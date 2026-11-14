#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: 2025-2026 Sinkó Gábor Zoltán / CentralInfraCore
#
# Közös könyvtár: mit veszítene el egy job-workspace törlése / felülírása.
# Sourceolja a run-job.sh és a work-open.sh -- egy definíció, két hívó.
#
# Mit veszítene el a workspace törlése? Soronként egy leletet ír; üres kimenet =
# nincs mit elveszíteni. A hívó dönt (blokkol vagy --force-clean).
#
#   - élő folyamat, aminek a munkakönyvtára a workspace-ban van (tmux szál,
#     interaktív agent, bárki shellje) -- a /proc/<pid>/cwd-ből, nem a `work`
#     nevéből: nem függ attól, mi indította;
#   - klón nem commitolt vagy pusholatlan munkával;
#   - ami nem git klón, vagy nem olvasható: nem ellenőrizhető, tehát blokkol.
workspace_loss_report() {
    local ws="$1" p pid cwd e n
    for p in /proc/[0-9]*; do
        pid="${p#/proc/}"
        [[ "$pid" == "$$" ]] && continue
        cwd=$(readlink "$p/cwd" 2>/dev/null) || continue
        case "$cwd" in
            "$ws"|"$ws"/*) echo "  élő folyamat a workspace-ban: pid $pid ($(tr '\0' ' ' < "$p/cmdline" 2>/dev/null | cut -c1-60)) cwd=$cwd" ;;
        esac
    done
    for e in "$ws"/* "$ws"/.[!.]*; do
        [[ -e "$e" ]] || continue
        # A work-open.sh egyetlen saját fájlja: az agent profilját rögzítő
        # .envrc. Csak a pontos alakját engedjük át -- bármi más tartalom nem
        # ellenőrizhető, tehát blokkol.
        if [[ "$(basename "$e")" == ".envrc" && -f "$e" ]] \
           && [[ "$(wc -l < "$e")" -eq 1 ]] \
           && grep -qE '^export CLAUDE_CONFIG_DIR=[^ ;&|$`]+$' "$e"; then
            continue
        fi
        if [[ -d "$e/.git" || -f "$e/.git" ]]; then
            if ! n=$(git -C "$e" status --porcelain 2>/dev/null); then
                echo "  $e: a git állapota nem olvasható"; continue
            fi
            [[ -n "$n" ]] && echo "  $e: nem commitolt változás ($(printf '%s\n' "$n" | wc -l) sor)"
            n=$(git -C "$e" rev-list --count HEAD --not --remotes 2>/dev/null) \
                || { echo "  $e: a pusholatlan commitok száma nem olvasható"; continue; }
            [[ "$n" -gt 0 ]] && echo "  $e: $n pusholatlan commit"
        else
            echo "  $e: nem git klón, a tartalma nem ellenőrizhető"
        fi
    done
    return 0
}
