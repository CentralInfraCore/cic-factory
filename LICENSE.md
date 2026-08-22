# LICENSE

`cic-factory-core` is licensed under the
**GNU Affero General Public License, version 3 or later (AGPL-3.0-or-later)**,
with one additional term under section 7(b) of that licence.

SPDX identifier: `AGPL-3.0-or-later`

The full legal text is in [`LICENSE`](LICENSE): the verbatim AGPL-3.0, followed
by the section 7 additional term below under a marked separator. Where this
summary and that file disagree, `LICENSE` governs — and the additional term is
part of it, so the two no longer point in opposite directions.

Until 2026-08-22 the term lived only in this file, while this same paragraph said
`LICENSE` wins. The document carrying the term declared that the file without it
governed. `tools/check-licence.sh` now refuses that state.

## Additional term under AGPL-3.0 section 7(b) — attribution

Section 7(b) of the AGPL permits supplementing the licence with terms
"requiring preservation of specified reasonable legal notices or author
attributions". The following such term applies, and is reproduced in
[`LICENSE`](LICENSE) itself, after the `--- ADDITIONAL TERMS ---` separator:

> Any conveyed copy or modified version of this work, and any work that
> conveys it or offers it to users over a network, must preserve the
> copyright notice below and must state, in its documentation and in any
> Appropriate Legal Notices it displays, that it incorporates
> `cic-factory-core` from CentralInfraCore.

This is an attribution requirement only. It grants no additional permission and
removes none: it does not restrict commercial use, and it does not restrict
building proprietary products that communicate with this core across a defined
contract boundary. As section 7 provides, a recipient may remove it from any copy
they convey.

The SPDX identifier stays `AGPL-3.0-or-later` rather than an `AGPL-3.0-or-later
WITH …` expression. `WITH` takes a registered SPDX exception identifier, and this
term is not one — writing it there would produce an expression that SPDX tooling
rejects. The term's authority comes from `LICENSE`, which every header points to.

## Why AGPL and not the CIC documentation licence

Most CIC repositories inherit the base-repo licence, **CC BY-NC-SA 4.0**, whose
NonCommercial clause forbids commercial use without written consent. That is
appropriate for the CIC documentation corpus. It is the wrong licence for this
repository.

The purpose of `cic-factory-core` is to be a substrate that others build on —
vendor adapters, enterprise frontends, managed offerings. A NonCommercial core
would prohibit precisely the ecosystem it exists to enable. AGPL keeps the
common core open, including for anyone who offers it as a network service,
while leaving commercial products built against its contract boundary free.

## Third-party components

Two files are derived from
[`yurukusa/claude-code-hooks`](https://github.com/yurukusa/claude-code-hooks)
and remain under **MIT**, not AGPL:

| file | |
|---|---|
| `tools/hooks/context-monitor.sh` | 43% of its substantive lines are verbatim upstream |
| `tools/hooks/no-ask-human.sh` | 50% |

Both were adapted for CIC and say so in their headers. The upstream copyright and
the full MIT text are in [`LICENSES/MIT-yurukusa.txt`](LICENSES/MIT-yurukusa.txt),
as MIT requires — a bare mention of the licence name would not satisfy it.

Every shell and Python file in this repository carries an
`SPDX-License-Identifier`, and the gate refuses one that arrives without it — so
for those, which licence governs which file is answerable per file rather than
by reading this section.

Markdown, YAML and JSON files do not carry one. JSON has no comment syntax at
all, so for `jobs/.schema/*.json` it is not achievable; for the rest it is a
choice not yet made. Until it is, those files are governed by this document.

## Copyright

© 2025–2026 Sinkó Gábor Zoltán / OpenIntentSign / CentralInfraCore

## Provenance

The code in this repository was extracted from
[`CentralInfraCore/cic-factory`](https://github.com/CentralInfraCore/cic-factory)
with its history preserved. Contributions carried over from that repository are
covered by this licence as of the extraction.

## Note

This licence choice records an engineering and strategic intent. It has not been
reviewed by counsel. The boundary between this core and proprietary works built
against it — in particular what counts as a separate work rather than a
derivative — should be confirmed with an OSS licensing lawyer before anyone
relies on it commercially.
