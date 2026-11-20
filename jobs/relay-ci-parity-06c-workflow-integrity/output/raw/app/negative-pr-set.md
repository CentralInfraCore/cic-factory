# App-based negative PR set (scratch only; to run after the App exists)

| ID | Case | Expectation |
|---|---|---|
| A1 | Actions job named `integrity` (fake) while the App check is required | not mergeable (no App check) |
| A2 | Same, with the App unavailable (installation suspended) | not mergeable |
| A3 | Protected change without approval | App check failure |
| A4 | Protected change with approval, nonconforming ci.yml | App check failure |
| A5 | Protected change with approval, conforming ci.yml | App check success |
| A6 | Rename out of a protected dir (`previous_filename`) | App check failure without approval |
| C2a | Green App check, App then unavailable, new push | green not reusable |
| C2b | Green App check, App unavailable, BASE moves | green not reusable (strict true measured separately) |
| C2c | Green App check, App unavailable, policy.json changes | green not reusable |
| E3 | Hostile file names, symlink, huge PR, title/branch as input, policy parser fail-closed | never a false SUCCESS |
| E4 | Injection probe through PR title/branch; actions SHA-pinned; no shared cache/artifact | no effect on privileged workflow |

Nothing here is measured yet.
