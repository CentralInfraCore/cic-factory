# PoC implementációs terv — forrásanyag

Ez a terv egy korábbi AI elemzésből származik. Az agent feladata nem ennek elfogadása,
hanem KB-val való ütköztetése a háromszintű státusz és bridge detector módszertan szerint.

---

## A terv által említett komponensek

### Sémák

- Actor.schema.json
- Intent.schema.json
- RelayHeader.schema.json
- DesiredState.schema.json
- TerraformState.schema.json
- ActualState.schema.json
- Drift.schema.json
- ProofTraceEvent.schema.json
- PoSE.schema.json
- StateCommit.schema.json
- RollbackRequest.schema.json
- PolicyDecision.schema.json

### Modulok

- schema-registry
- intent-ingestor
- terraform-desired-extractor
- terraform-state-reader
- actual-state-collector (Proxmox, VyOS, OpenSwitch)
- pbs-root-calculator
- canonical-json-normalizer
- prooftrace-builder
- prooftrace-chain-validator
- pose-verifier
- drift-classifier
- state-commit-writer
- trust-anchor-registry
- rollback-intent-reader
- ois-policy-evaluator

### Workflowk

- post_apply_observation.workflow.yaml
- manual_drift_observation.workflow.yaml
- hard_drift_detection.workflow.yaml
- rollback_intent.workflow.yaml
- rollback_post_apply_verify.workflow.yaml

### Relay funkciók

- relay.validate(input, schemaRef)
- relay.canonicalize(object)
- relay.hash(canonicalObject)
- relay.sign(hash, actorRef)
- relay.observe(providerRef)
- relay.compare(logical, physical)
- relay.classifyDrift(diff)
- relay.buildProofTrace(event)
- relay.commitState(bundle)
- relay.verifyCommit(commitRef)
- relay.readIntentBranch()
- relay.emitOperatorInstruction()

### A terv által leírt PoC flow

```
User futtatja: terraform apply
        ↓
CIC: desired IaC beolvasása
CIC: terraform state/show beolvasása
CIC: actual physical state beolvasása (Proxmox/VyOS/OpenSwitch)
CIC: canonicalizálás
CIC: ProofTrace generálás
CIC: PoSE/PBS összevetés
CIC: drift osztályozás
CIC: state/ branch commit + aláírás
```
