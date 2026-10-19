# theads — session-naplók

A `YYYY-MM-DD_session-<téma>.md` fájlok egy Claude Code session
**transcriptjei**: csak az interakció (felhasználói üzenetek és válaszok,
időrendben, UTC), eszközhívások és kimenetek nélkül.

Ezek **naplók, nem dokumentáció**. Azt rögzítik, ami a sessionben elhangzott,
nem azt, ami a repóról igaz. Ezért a `tools/check-docs.sh` nem ellenőrzi őket
(D1, D2, D4): egy transcriptben idézett szabály-azonosító, link vagy yaml blokk
nem állítás a repó kapuiról, és utólagos átírása a bizonyítékot rontaná.

A naplók nem helyettesítik a PR-okat és a git-történetet. A vezetés szabálya a
[`CLAUDE.md`](../CLAUDE.md) „Session-napló" szakaszában van.
