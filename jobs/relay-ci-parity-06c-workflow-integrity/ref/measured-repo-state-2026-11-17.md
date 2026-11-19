# CIC_Relay: mért védelmi állapot (csak olvasás, 2026-11-17, `main` `ad1ca54`)

Forrás: `gh api` olvasó hívások a `CentralInfraCore/CIC_Relay` repóra. Amit nem tudtam olvasni, azt a végén jelzem.

## Repository ruleset `main: required checks` (id 26873807)

- `enforcement: active`, cél: `~DEFAULT_BRANCH`, `bypass_actors: []` (nincs mentesített szereplő).
- Szabálytípusok: `deletion`, `non_fast_forward`, `required_status_checks`. **Nincs** `workflows` (required workflow), nincs `pull_request` (kötelező review / code owner review) szabály.
- Kötelező státusz-checkek **név szerint**, integration id 15368 (GitHub Actions): `verify`, `coverage`, `python`, `rust`, `ffi`, `manifest`, `mutation-pr`. `strict_required_status_checks_policy: false`.
- **Nem kötelező:** `object-evidence`, `gate-selftest` (report-only), `baseline-guard` (a `mutation-pr` aggregátum függ tőle), a `pin-reference` lépés (a jobokon belüli lépés).

## Egyéb

- A `main` klasszikus branch protection-je: nincs (`Branch not protected`).
- Merge módszerek: csak merge commit (`allow_squash_merge: false`, `allow_rebase_merge: false`).
- Actions: `allowed_actions: all`, `sha_pinning_required: false`; **`default_workflow_permissions: write`** és **`can_approve_pull_request_reviews: true`**.
- `.github/CODEOWNERS`: `* @sinkog`; **nincs szabály, amely a code owner review-t megköveteli**, ezért a fájl nem kényszerít semmit.
- Az organizáció **free** csomagon van; az **organizációs ruleset nem elérhető** (`Upgrade to GitHub Team to enable this feature`), így az org-szintű required workflow sem.
- Környezetek (`environments`): 0.

## A workflow-k triggerei (`origin/main`)

| Workflow | Trigger |
|---|---|
| `verify.yml` | `push`, `pull_request` |
| `mutation-pr.yml` | `pull_request` |
| `manifest-check.yml` | `pull_request`, `push` |
| `object-evidence.yml` | `pull_request`, `workflow_dispatch` |
| `gate-selftest.yml` | `pull_request`, `workflow_dispatch` |
| `mutation.yml` | `schedule`, `workflow_dispatch` |
| `nightly.yml` | `schedule`, `workflow_dispatch` |
| `renovate.yml` | `schedule`, `workflow_dispatch` |

Egyik sem `pull_request_target`.

## Amit nem tudtam mérni

- Hogy a **repository-szintű `workflows` ruleset-szabály** ezen a csomagon elérhető-e: az API nem jelzi előre; csak egy próbafeltöltés mutatja meg (ehhez kísérleti repó kell, a tulajdonos engedélyével).
- Hogy a **public repo** a free csomagon is támogat-e `pull_request` ruleset-szabályt kötelező review-val (a mostani ruleset három szabályt használ, ez negyedik lenne): nem próbáltam.
- A fork-PR-ok `GITHUB_TOKEN` jogosultságai (a repo nyilvános, `members_can_fork: true`).
