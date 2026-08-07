# Git kezelés és fejlesztési workflow (magyar)

Ez a dokumentum a CIC Relay projekt Git-alapú fejlesztési szabályait, branch-kezelési elveit és commit-konvencióit rögzíti.

---

## Általános elvek

- **Minden fejlesztés Git verziókezelés alatt történik.**
- A fő fejlesztési ág a `main` vagy `master` branch (projektbeállítástól függően).
- Új funkciók, hibajavítások, kísérleti fejlesztések **külön branch**-en készülnek.
- **Pull request (merge request)** kötelező minden branch beolvasztásához a fő ágba.

---

## Branch-elnevezési szabályok

- **feature/** – Új funkciók:  
  Pl.: `feature/relay-plugin-support`
- **fix/** – Hibajavítások:  
  Pl.: `fix/yaml-schema-validation`
- **doc/** – Dokumentáció:  
  Pl.: `doc/hu-readme-update`
- **hotfix/** – Kritikus javítások:  
  Pl.: `hotfix/registry-lookup-error`
- **experiment/** – Kísérleti, proof-of-concept ágak:  
  Pl.: `experiment/async-mq-adapter`

---

## Commit üzenet konvenció

- **Tömör, leíró commit üzenet angolul vagy magyarul (project policy szerint).**
- Ha lehetséges, a commit első sora utaljon az adott issue-ra vagy feature-re.
- Példa:  
  `fix: javítva a plugin registry init race condition`

---

## Release és verziózás

- **Release előtt** minden fejlesztői branch merge-ölése a fő ágba kötelező.
- **Release tagek**: `v1.0.0`, `v2.1.3`, stb.
- A fő (main/master) ágban csak stabil, integrált, tesztelt verzió lehet.

---

## Visszagörgetés / hiba esetén

- **Rollback:** szükség esetén a megfelelő commit-ra való visszaállás (pl. `git revert` vagy `git reset`).
- **Hotfix:** hibás release esetén azonnali javítás külön hotfix branch-ről.

---

## Pull request (merge request) folyamat

1. Fejlesztés külön branch-en.
2. Kód review vagy dokumentáció review (minimum 1 team tag).
3. Automatikus és/vagy manuális tesztek.
4. Beolvasztás a fő ágba csak review után.

---

## Egyéb javaslatok

- Kódbázis egységesség: minden új fejlesztés illeszkedjen a meglévő projektstruktúrához.
- **README** és dokumentációk frissítése minden releváns változtatásnál kötelező.

---

Ha kérdésed van a workflow-val kapcsolatban, először mindig nézd meg a projekt docs/hu/concept/git-management.md vagy docs/en/concept/git-management.md állományát!
