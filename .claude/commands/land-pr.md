# PR lezárása (land-pr)

Egy PR-t, és ha vannak, a függőség PR-jait végigkövet a mergeig a `tools/ci-gate.py land` paranccsal. Használat:
`/land-pr <PR url> [--after <függőség PR url> ...] [--keep-current]`

## Mit csinálsz

1. Az URL-ekből `OWNER/REPO#N` lesz (`https://github.com/O/R/pull/N`). A PR-hoz tartozó kötelező készlet a repó profilja:
   `tools/ci-required/<repo>.txt`; ha nincs, **állj meg és kérdezd meg**, melyik kapukat várja a PR (üres készlet nem létezik).
   A post-merge profil: `tools/ci-required/<repo>.post-merge.txt`, ha van.
2. Az approver a tulajdonos GitHub-fiókja (`gh api user -q .login`, és a repo tulajdonosa), **soha nem más**.
3. Futtasd a háttérben (nem blokkol, a befejezéséről értesít):

```bash
python3 tools/ci-gate.py land OWNER/REPO#N \
  --require-from tools/ci-required/REPO.txt --post-merge-from tools/ci-required/REPO.post-merge.txt \
  --approver OWNER_LOGIN [--after OWNER/REPO#M ...] [--keep-current]
```

   Előbb `--dry-run`-nal nézd meg, mit tenne, ha a PR elmaradt a célágtól vagy függősége van.
4. A kimenetből jelents: merged (a merge commit, a post-merge eredmény), vagy hol állt meg és miért.

## Szabályok (nem alkudhatók)

- **A jóváhagyást nem te adod.** A `land` GitHubról olvassa: egy `APPROVED` review a HEAD-re, vagy `merge-approved: <teljes sha>` hozzászólás
  a tulajdonostól. Ha nincs, a script vár; te szólsz a tulajdonosnak a pontos HEAD-del. Ha a tulajdonos a chatben mondta ki, és kéri a
  rögzítést, írhatod `merge-approved: <sha>` sorral, alatta megjelölve: „a tulajdonos chat-utasításából rögzítve". A „zöld" vagy
  „lefutott" megállapítás nem engedély, és a reviewer szakmai GO-ja sem.
- Új HEAD (push, `--keep-current` frissítés) = új jóváhagyás. Ne feltételezd, hogy átvihető.
- Konfliktusnál, piros CI-nál és lezárt függőségnél a script megáll: nem újrafuttatod vakon, hanem megmondod, mi a hiba, és ha javítás kell,
  azt külön kéred, új HEAD-del.
- A merge után a napló frissítése és commitja (`theads/`) a lezárás része.
