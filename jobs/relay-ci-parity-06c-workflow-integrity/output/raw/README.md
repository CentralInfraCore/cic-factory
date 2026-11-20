# raw/ — #212 job evidence
- scratch/pr-results.tsv: scratch PR -> head sha -> check conclusions (PRs 1..18)
- scratch/runs.tsv: Actions run ids with event, head sha, branch, conclusion
- scratch/integrity-log-lines.txt: the verdict lines of every integrity run
- scratch/*.txt (integrity.py.txt, integrity.yml.txt, policy.json.txt, ci.yml.txt, self-approve.yml.txt, caller.yml.txt, fake.yml.txt; the .txt suffix keeps linters off them): the scratch mechanism and the manipulations
- scratch/sc-helpers.sh: API helpers used to build the scratch repo (no git push)
- scratch/rulesets-probe.txt: the workflows-rule probes
- reachability.txt: call paths with file:line
Scratch repos: CentralInfraCore/cic-scratch-212-{public,private,workflows} (disposable). Approval comments on PR12 (head 8805499c…) and PR13 (head 9bf8ff7f…) were posted by the owner.
