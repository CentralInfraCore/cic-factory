# LICENSE

This repository is **not under a single licence**. Three sets of files, three
licences. Every source file carries an `SPDX-License-Identifier` header, so the
answer for any given file is in the file itself.

| what | licence | where |
|---|---|---|
| the factory's own content | **CC BY-NC-SA 4.0** | `jobs/`, `docs/` (except where noted), `README.md`, `CLAUDE.md`, `theads/`, `ai/` |
| tooling adopted from `cic-factory-core` | **AGPL-3.0-or-later** | `tools/`, `.claude/commands/`, `jobs/.schema/`, `SPEC.md` |
| two vendored hook scripts | **MIT** | `tools/hooks/context-monitor.sh`, `tools/hooks/no-ask-human.sh` |

## Why it is mixed

`cic-factory` adopts its tooling from
[`cic-factory-core`](https://github.com/CentralInfraCore/cic-factory-core), which
is AGPL-3.0-or-later with a section 7(b) attribution term. **Those files keep
their licence** — that is not a choice this repository gets to make, and their
SPDX headers say so.

The factory's own content is a different kind of thing: job specifications,
agent output, reviews, a working log of how CIC was built. That is documentation,
and it follows the CIC documentation licence.

## The factory's own content — CC BY-NC-SA 4.0

**Attribution** — credit the original authors.
**NonCommercial** — no commercial use without written permission.
**ShareAlike** — derivatives under the same licence.

Full text: <https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode>

## The adopted tooling — AGPL-3.0-or-later

Verbatim text in [`LICENSE`](LICENSE), followed by the section 7 additional term
under a marked separator.

That term is an attribution requirement, and it applies to this part:

> Any conveyed copy or modified version of this work, and any work that
> conveys it or offers it to users over a network, must preserve the
> copyright notice below and must state, in its documentation and in any
> Appropriate Legal Notices it displays, that it incorporates
> `cic-factory-core` from CentralInfraCore.

It grants no additional permission and removes none: it does not restrict
commercial use, and it does not restrict building proprietary products that
communicate with the core across a defined contract boundary. As section 7
provides, a recipient may remove it from any copy they convey.

Until `core/@v0.2.0` this term lived only in the core repository's own
`LICENSE.md`, and was referenced here by link. It is stated here now because a
licence obligation carried by a link is not carried at all —
`tools/check-licence.sh` refuses the state where `LICENSE` and this file
disagree about it.

The other two parts below are **not** affected by it.

## The vendored hooks — MIT

Derived from
[`yurukusa/claude-code-hooks`](https://github.com/yurukusa/claude-code-hooks).
Upstream copyright and full text: [`LICENSES/MIT-yurukusa.txt`](LICENSES/MIT-yurukusa.txt).

## Copyright

© 2025–2026 Sinkó Gábor Zoltán / OpenIntentSign / CentralInfraCore

## Note

This arrangement records an engineering intent and has not been reviewed by
counsel. Two points worth confirming with an OSS licensing lawyer: whether a
CC licence is appropriate for any file here that is closer to software than to
documentation, and where exactly the AGPL boundary falls for work built against
the adopted tooling.
