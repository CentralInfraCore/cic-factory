# pr-status — a nyitott PR-ok csak olvasó állapota

A koordinátor eszköze a soros, pontos HEAD-hez kötött integrációhoz (`tools/pr-status.py`). Egy sor PR-onként:
a PR, a **teljes HEAD**, a bázis, amivel készült és ami most van, hogy mozdult-e a bázis, a CI **pontosan erre a HEAD-re**,
a review állapota és hogy a GitHub össze tudja-e mergelni. **Nem ír semmit**: minden hívása `gh api -X GET`, és ezt a tesztje
ellenőrzi (`tools/test_pr_status.py`, 14 teszt; 10 szándékos hibájának mindegyikén elbukik).

```
tools/pr-status.py                       # az alapértelmezett repók (PR_STATUS_REPOS=a/b,c/d felülírja)
tools/pr-status.py OWNER/REPO ...        # ezek a repók
tools/pr-status.py --pr OWNER/REPO#N     # egy PR
tools/pr-status.py --json                # géppel olvasható
```

## Mit jelent az egy szavas ítélet

| Ítélet | Jelentés |
|---|---|
| `ready` | a CI minden check-je zöld erre a HEAD-re, a PR mergelhető, nincs változtatást kérő review, a bázis nem mozdult |
| `ready-base-moved` | ugyanez, de a bázis mozdult a PR készítése óta: merge előtt újra kell nézni, érinti-e a tesztelt eredményt |
| `ci-pending` / `ci-failing` / `ci-none` | fut / bukott / nincs check erre a HEAD-re — a hiányzó CI **nem** zöld |
| `mergeable-no` / `mergeable-unknown` | konfliktus / a GitHub még számolja (kérdezd újra) |
| `changes-requested` | egy reviewer a legutóbbi verdiktjével változtatást kért |
| `HEAD-MOVED` | olvasás közben mozdult a HEAD: amit látsz, nem biztos, hogy erre vonatkozik |
| `draft`, `UNREAD` | piszkozat; vagy valami nem volt olvasható (a sor megmondja, mi) |

Az ítélet **tanács, hogy nézz rá, nem merge-engedély**. A merge a tulajdonos döntése, a kiírt HEAD-hez kötve:
`gh pr merge N --squash --match-head-commit <teljes HEAD>`.

## Amit a CI-oszlop számol

Az adott commit check-run-jai (befejezett és fut) és a commit-státuszai. Ismeretlen befejezési állapot nem zöld. A review
oszlopban egy korábbi commitra adott jóváhagyás `approved_stale`, nem `approved`.

## Korlát

A GitHub `mergeable` mezője lusta: egy friss push után `unknown` lehet. A kötelező check-ek listáját az eszköz nem ismeri
(a branch-védelem nincs olvasva), ezért a „minden check zöld" nem azonos a „minden kötelező check zöld"-del.
