# Futási történet: forms-oracle-provider-integration-01a

Az indítási kísérletek **mind** részei a végrehajtási történetnek; a későbbi sikeres futás nem teszi meg nem történtté a korábbi hibákat. Időpontok UTC, 2026-11-07. A rekord a `jobs/index.yaml`/`meta.yaml` alapján és a futási naplókból készült; titkot nem tartalmaz.

| # | Mi történt | Állapot a metában | Token / költség | Ok és kezelés |
|---|---|---|---|---|
| 0 | `run-job.sh` az agent-konfiguráció ellenőrzésénél kilépett (exit 1), **mielőtt bármit elindított vagy pusholt volna** | nem változott (`pending`), nem számít kísérletnek | nincs | a `meta.yaml` `agent.config_dir` értéke `~`-vel kezdődött; a `run-job.sh` a #42 óta olvassa a mezőt, és **nem bontja ki a `~`-t**, ezért a `[[ -d ]]` ellenőrzés elbukott. Kezelés: abszolút út (helyi commit `9c43d02`) |
| 1 | Az agent elindult és azonnal leállt (10:47:49 → 10:48:16, `duration_ms` 490, a metába írt `turns` 1) | `error` (a lifecycle-push ezt is kivitte a remote `main`-re) | **0 token, 0 USD**; `stop_reason: stop_sequence` | az ágens-profil hitelesítése megszűnt: a `.credentials.json` nem a dokumentált szimbolikus link volt, hanem külön fájl `loginEnded` mezővel; a közvetlen próbahívás `terminal_reason: api_error`-t adott 0 tokennel. A feature branch nem került a remote-ra |
| – | Hitelesítés helyreállítása | – | – | a profil fájlja biztonsági mentésbe (`.credentials.json.bak-20261107T104943Z`, jogosultság 600, a profil könyvtárában, **nem** git-repóban), a helyén a dokumentált szimbolikus link a fő profil hitelesítésére; egy rövid próbahívás (`claude-opus-5`, 0,09 USD) `completed`-et adott |
| 2 | Újraindítás ugyanazzal a specifikációval (10:49:59-től) | `running` | a futás végén kerül be | a spec-gate GO; ugyanaz a modell és `max_turns` |

**Következmények, amiket rögzítek.** (a) Az 1. kísérlet 0 tokenes volt, ezért semmilyen munka nem veszett el, de a remote `main` rövid ideig `error` állapotot mutatott. (b) A `usage` blokk a `run-job.sh`-ban az utolsó futásé; az 1. kísérlet adatai csak ebben a rekordban és a `jobs/index.yaml` történetében maradnak meg. (c) A `.credentials.json.bak-*` fájl tartalmát **nem** szabad commitolni, evidence-csomagba tenni vagy idézni; a fájl jogosultsága 600.

## Attempt 2 outcome (recorded 2026-11-07, orchestrator)

- Ended `error` at 2026-11-07T11:20:10Z after 108/150 turns, 13.95 USD, 16 617 164 input tokens (16 296 353 cache read), 103 769 output tokens, `stop_reason: stop_sequence`.
- **Cause of the stop (measured):** `output/agent-output.md` contains exactly one line of text, the harness message "You've hit your 5-hour limit · resets 2pm (Europe/Budapest)". The run was cut by the account usage limit, not by the turn limit and not by an agent decision. The `stop_sequence` label is the harness's label for that event.
- Delivered in the local workspace only (feature branch NOT on the remote; no push happened): `baseline.md` (865 lines), `contract-mapping.md` (298 lines). `agent-output.md` is the limit message, not a report. `relay-requirements.md` and `claim-evidence.md` are absent.
- Credential symlink survived the run (still points to the main profile file; no `.bak-*` credential file; the invalid backup was shredded earlier).
- Workspace kept; no resume, no new job, no push.

## Attempt 3 — controlled `--resume` (owner GO 2026-11-07; method A, no push)

Recorded BEFORE the resume (UTC 2026-11-07, orchestrator):
- Session id (meta `agent.session_id`): `8f0c166f-9538-4d27-a2d3-18e51c0d27b0`; the session jsonl exists in the agent profile.
- SHA-256 of the immutable inputs (workspace `output/`): `baseline.md` b66da3e5b21217fd5f4a9308f1321a24ddf87b16a9ffbe210714f151e523e9ea; `contract-mapping.md` a876924c858df3ec3e3510f23ca771b01c7bbd410b2b12dfa63a9562d20ff3e2; `agent-output.md` (the limit message, 60 bytes) 1802bb86aeef7ad25b5059bbe9519f9666595d12fb63752d2ab0983fedabe194.
- Workspace: branch `feature/forms-oracle-provider-integration-01a`, HEAD 000915991e5f; 16 untracked entries (list saved); remote `origin` fetch URL unchanged, **push URL disabled** (`disabled://owner-decision-no-push`, workspace-local git config) so a push cannot succeed whatever the agent tries.
- Workspace `input.md` modified (local, not committed, not pushed): the owner-approved "Controlled Resume Scope" block inserted at the top (hard constraints 1-10, required structures of the two outputs, M2 `PROPOSED / OWNER DECISION REQUIRED`, R1 mechanism undecided), plus a "FOLYTATÁS" marker on the Output and Ellenőrizhető elvárások headings. SHA-256 before aa3a6a38…43dd5ed, after 365cf84dfff38cf52d89eb6d13b033309f22f057473846757a3fbb00c9fa3505. The live `jobs/<id>/input.md` (the spec of record) is unchanged. The block is in English by the owner's approved wording; the rest of the file is Hungarian.
- The two review files copied into the workspace `ref/` (untracked there): `orchestrator-review-partial.md`, `resume-scope-proposal.md`.
- Delivery of the new text to the agent: NOT provable before launch. What is established: `run-job.sh` resume prompt (lines ~642-655) names `$FACTORY_CLONE/jobs/$JOB_ID/input.md` and tells the agent to take its Definition of Done from it; the resume path does not overwrite the workspace input.md (no cp/checkout); the modified file is at exactly that path. Mitigations: push physically disabled; live watcher on the session jsonl that stops the run on a forbidden action (docker/go test/mutation tools/git push) and shows whether the agent read the scope block; post-run hash, symlink and remote checks.
- Credential symlink before: `agents/cic-module-wasm-claude/.credentials.json` -> `/home/sinkog/.claude-personal/.credentials.json`.
- Known lifecycle behaviour (not an agent push): `run-job.sh` itself commits and pushes the job's `meta.yaml`/`jobs/index.yaml` status to the live workdir `origin/main` (push_lifecycle), as in attempts 1-2. origin/main before: 182479766 (= local main).

### Attempt 3 outcome (recorded 2026-11-07, orchestrator, after the run)
- Ended `awaiting_review` at 2026-11-07T14:10:35Z; 19/150 turns, `stop: end_turn` (a normal end, not a limit cut); cost 23.67 USD for this resume (index total 65.90 -> 89.57 USD); 24 052 789 input tokens (23 294 778 cache read), 177 712 output.
- Hashes: `baseline.md`, `contract-mapping.md`, `agent-output.md` bit-identical to the pre-resume values (sha256 compared, 3/3).
- Credential symlink survived (still -> main profile file; one credentials entry in the profile dir).
- Push: none by the agent. The feature branch is NOT on the remote (`ls-remote` 0 hits); workspace push URL still disabled. Remote `origin/main` moved only by the lifecycle: 0eef3b1 (running), 3060773 (awaiting_review), touching only `meta.yaml` and `jobs/index.yaml` (22+/22-).
- Workspace: new local signed commit `b62f624` (3 files: `relay-requirements.md` 627 lines, `claim-evidence.md` 261, `agent-output-resume-2026-11-07.md` 236 lines in the commit; the harness's own `agent-output-resume-20261107T135051Z.md`, 3.6 KB, is an untracked summary). `baseline.md` and `contract-mapping.md` remain untracked (the interrupted run never committed them); workspace `input.md` shows as modified (the scope block, mine). The two orchestrator ref files are untracked in the workspace.
- Scope compliance (session jsonl, parsed tool calls): only read-only `sed`/`grep`/`cat`, one heredoc write per output; no docker/go test/mutation/push executed (the watcher's heredoc hits were quoted text). The agent states it read the scope ("Hatókör világos"); direct proof it read the block itself is indirect.
- `tools/validate-output.sh` on a MARKED STAGING COPY (not the lifecycle output directory): `MECHANIKUS OUTPUT-ELLENŐRZÉS: GO`, 4 files inspected, O5 warning (46 file:line resolvable with `env.sh`, 275 not: they point at repos/commits outside the configured roots). Not the lifecycle gate; the lifecycle location needs the branch pushed or a decision.
- Content spot checks: all disputed numbers (82.7/82.9, 55/26, 7/8, 159/217, govulncheck, Q3/Q6/Q9) carry `NIV`; M2 `PROPOSED / OWNER DECISION REQUIRED`; R1 states the mechanism is not decided; `OV` line references into `ref/orchestrator-review-partial.md` resolve (workspace copy identical to the live file).
- Status of the job: 01a is `awaiting_review` in the meta; per the owner's rule it stays PARTIAL until the review and the open decisions; no `/job-close` run.
