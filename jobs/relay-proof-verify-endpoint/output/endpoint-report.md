## VerifyProofArtifact szignatúra

A `VerifyProofArtifact` függvény a `cmd/relay/proof_verify.go`-ban él (nem `core/cabinet/`-ban — a job spec szándéka szerint a HTTP réteg saját verifikátora, `ComputeChainHashV1` felhasználásával):

```go
func VerifyProofArtifact(a *ProofArtifact) VerifyResult
```

Ellenőrzések:
1. Kötelező mezők: `workflow_id`, `chain_hash`, `timestamp`
2. `chain_hash` újraszámítás: `ComputeChainHashV1(WorkflowID, SourceDigest, steps)`
3. Per-step validáció: `name`, `module`, `input_hash`, `output_hash` mind kötelező
4. `pose_result` enum: `VERIFIED | DRIFT | SKIPPED`
5. `commit_record.id == chain_hash` konzisztencia

## Implementált handler

**Fájl:** `cmd/relay/proof_verify_handler.go`
**Függvény:** `(s *relayServer) proofVerifyHandler`
**Router regisztráció:** `cmd/relay/main.go:190` — `mux.HandleFunc("/v1/proof/verify", s.proofVerifyHandler)`

## Teszt

**Tesztfájl:** `cmd/relay/proof_verify_handler_test.go`

**Tesztesetek (handler):**
- `TestProofVerifyHandler_MethodNotAllowed` — GET → 405
- `TestProofVerifyHandler_BodyTooLarge` — 20 byte > 10 byte limit → 413
- `TestProofVerifyHandler_InvalidJSON` — malformed JSON → 400
- `TestProofVerifyHandler_MissingProofArtifact` — hiányzó mező → 400
- `TestProofVerifyHandler_ReadBodyError` — olvasási hiba → 500
- `TestProofVerifyHandler_ValidArtifact` — helyes artifact → 200, valid=true
- `TestProofVerifyHandler_InvalidChainHash` — rossz chain hash → 200, valid=false, errors tartalmaz "chain_hash mismatch"

**Exit code:** 0

```
ok  centralrelay/cmd/relay  1.222s
```

## Git

**Branch:** `feat/proof-verify-endpoint`
**Commit hash:** `af77c2a`
**Commit message:** `feat(api): POST /v1/proof/verify — chain hash verification endpoint`
