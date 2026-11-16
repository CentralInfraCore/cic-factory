# Az #212 tulajdonosi döntései (a #195 és #214 review-k alapján, 2026-11-16/17)

- A #195 funkcionális pin-védelme APPROVE; a **#207 workflow-integritási rés új, kötelező issue** (#212), külön trust-határ.
- **Első lépésben csak job-spec**, implementáció a spec review-ja után. A **#207 a javítás kötelező negatív bizonyítéka.**
- A megoldásnak a **vizsgált PR bizalmi határán kívül** kell működnie, és bizonyíthatóan meg kell akadályoznia a kötelező ellenőrzések **eltávolítását, gyengítését vagy megkerülését**.
- **Külön vizsgálandó:** az action, a `GATE`/`MR_GATE` kiválasztás, a `BOOTSTRAP`, az `object_model.py` integritása.
- **Kiemelt követelmény:** nemcsak az ellenőrzési **szabályokat** kell védeni, hanem az ellenőrzés **végrehajtásának kötelezettségét** is.
- **Sorrend:** #212 → #213 (commit-aláírás kikényszerítése; a verifier kapuja nem a vizsgált PR saját verifierét futtatja) → PR-07 (FULL/DIFF). A PR-07 implementációja az #212 lezárása után indul; az ütemezett workflow-k bizonyítása a PR-07 elfogadási feltétele.
- **Külön, nem ez a job:** a `base@0.8.0` kiadás, a közös hook v1 fallbackjének lecserélése, a `cargo-mutants`/`cargo-llvm-cov` telepítési pin.
- A repository-beállítások (ruleset, branch protection) módosítása **tulajdonosi döntés és beállítás**; a job javasolhat és mérhet, nem állíthat.
